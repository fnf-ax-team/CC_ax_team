"""
Person-based workflow utilities - 얼굴/포즈 분석, VLM 유틸
"""

import os
import re
import json
import threading
from io import BytesIO
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any

from PIL import Image
from google import genai
from google.genai import types

from core.config import IMAGE_MODEL, VISION_MODEL


# ============================================================
# Type Definitions (dataclasses)
# ============================================================


@dataclass
class BoundingBox:
    """정규화된 바운딩 박스 (0-1 범위)"""

    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def center(self) -> Tuple[float, float]:
        """박스 중심점"""
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def area(self) -> float:
        """박스 면적 (정규화)"""
        return (self.x2 - self.x1) * (self.y2 - self.y1)

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1


@dataclass
class FaceInfo:
    """얼굴 감지 정보"""

    bbox: BoundingBox
    position_label: str  # left, center-left, center, center-right, right
    face_angle: str  # frontal, 3/4 left, 3/4 right, profile left, profile right
    confidence: float

    def to_dict(self) -> dict:
        return {
            "bbox": {
                "x1": self.bbox.x1,
                "y1": self.bbox.y1,
                "x2": self.bbox.x2,
                "y2": self.bbox.y2,
            },
            "position_label": self.position_label,
            "face_angle": self.face_angle,
            "confidence": self.confidence,
        }


@dataclass
class PoseInfo:
    """포즈 정보 (레퍼런스 이미지 분석 결과)"""

    body_position: str  # standing, sitting, walking, running, etc.
    torso_angle: str  # frontal, 3/4 left, 3/4 right, side
    head_position: str  # neutral, turned left, turned right, looking up/down
    arm_left: str  # relaxed, bent, raised, etc.
    arm_right: str
    leg_left: str  # standing, bent, forward, backward
    leg_right: str

    def to_dict(self) -> dict:
        return {
            "body_position": self.body_position,
            "torso_angle": self.torso_angle,
            "head_position": self.head_position,
            "arm_left": self.arm_left,
            "arm_right": self.arm_right,
            "leg_left": self.leg_left,
            "leg_right": self.leg_right,
        }


@dataclass
class PoseComparison:
    """포즈 비교 결과"""

    similarity_score: float  # 0-100
    matching_elements: List[str]
    differing_elements: List[str]
    overall_match: bool

    def to_dict(self) -> dict:
        return {
            "similarity_score": self.similarity_score,
            "matching_elements": self.matching_elements,
            "differing_elements": self.differing_elements,
            "overall_match": self.overall_match,
        }


# ============================================================
# VLM Prompts
# ============================================================

FACE_DETECTION_PROMPT = """
Analyze this image and detect all human faces.

For each face, provide:
1. Bounding box in normalized coordinates (0-1 range): {"x1": float, "y1": float, "x2": float, "y2": float}
2. Position label: "left", "center-left", "center", "center-right", "right" (based on horizontal center)
3. Face angle: "frontal", "3/4 left", "3/4 right", "profile left", "profile right"
4. Confidence: 0.0-1.0 (how clear/visible the face is)

Return JSON format:
{
    "faces": [
        {
            "bbox": {"x1": 0.2, "y1": 0.1, "x2": 0.4, "y2": 0.5},
            "position_label": "center-left",
            "face_angle": "3/4 right",
            "confidence": 0.95
        }
    ]
}

If no faces detected, return {"faces": []}
"""

POSE_ANALYSIS_PROMPT = """
Analyze the pose of the person in this image.

Provide detailed information:
1. body_position: "standing", "sitting", "walking", "running", "leaning", "crouching", etc.
2. torso_angle: "frontal", "3/4 left", "3/4 right", "side left", "side right", "back"
3. head_position: "neutral", "turned left", "turned right", "looking up", "looking down", "tilted"
4. arm_left: "relaxed down", "bent at elbow", "raised up", "extended forward", "crossed", "on hip"
5. arm_right: (same options as arm_left)
6. leg_left: "standing straight", "bent at knee", "forward step", "backward step", "crossed"
7. leg_right: (same options as leg_left)

Return JSON format:
{
    "body_position": "standing",
    "torso_angle": "3/4 right",
    "head_position": "turned left",
    "arm_left": "relaxed down",
    "arm_right": "on hip",
    "leg_left": "standing straight",
    "leg_right": "forward step"
}
"""

POSE_COMPARISON_PROMPT = """
Compare the poses between two images.

Image 1: Source pose (what we want to match)
Image 2: Reference pose (what was requested)

Analyze:
1. similarity_score: 0-100 (how similar are the poses overall)
2. matching_elements: list of pose elements that match well
3. differing_elements: list of pose elements that differ significantly
4. overall_match: true/false (similarity_score >= 90)

Return JSON format:
{
    "similarity_score": 92,
    "matching_elements": ["torso angle", "head position", "arm positions"],
    "differing_elements": ["leg stance"],
    "overall_match": true
}
"""

FACE_SELECTION_PROMPT = """
You are selecting the best face reference images from a folder.

Criteria for good face references:
1. Face is clearly visible (not blurry, occluded, or too small)
2. Frontal or near-frontal angle (3/4 view acceptable)
3. Good lighting (face features visible)
4. Neutral or positive expression preferred
5. High resolution/quality

Return JSON with selected image paths ranked by quality:
{
    "selected": ["image1.png", "image3.jpg"],
    "reasons": ["Clear frontal view, high quality", "Good 3/4 angle, well-lit"]
}

Max {max_count} selections.
"""


# ============================================================
# API Key Management
# ============================================================


class _ApiKeyRotator:
    """스레드 안전 API 키 로테이터 (싱글톤)"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._keys = cls._load_api_keys()
                    cls._instance._index = 0
        return cls._instance

    @staticmethod
    def _load_api_keys() -> List[str]:
        """환경변수 또는 .env 파일에서 API 키 로드"""
        env_key = os.environ.get("GEMINI_API_KEY", "")
        if env_key:
            keys = [k.strip() for k in env_key.split(",") if k.strip()]
            if keys:
                return keys

        # .env 파일 탐색 (현재 디렉토리부터 상위로)
        for path in [".env", "../.env", "../../.env", "../../../.env"]:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        for line in f:
                            if (
                                "GEMINI_API_KEY" in line
                                and "=" in line
                                and not line.startswith("#")
                            ):
                                _, v = line.strip().split("=", 1)
                                keys = [k.strip() for k in v.split(",") if k.strip()]
                                if keys:
                                    return keys
                except Exception:
                    continue

        return []

    def get_key(self) -> str:
        """다음 API 키 반환 (라운드 로빈)"""
        if not self._keys:
            raise ValueError("GEMINI_API_KEY 없음. .env 파일을 확인하세요.")

        with self._lock:
            key = self._keys[self._index % len(self._keys)]
            self._index += 1
            return key


def load_api_keys() -> List[str]:
    """모든 API 키 반환"""
    rotator = _ApiKeyRotator()
    return rotator._keys


def get_next_api_key() -> str:
    """다음 API 키 가져오기 (스레드 안전)"""
    rotator = _ApiKeyRotator()
    return rotator.get_key()


# ============================================================
# 이미지 변환
# ============================================================


def pil_to_part(img: Image.Image, max_size: int = 1024) -> types.Part:
    """PIL 이미지를 Gemini API Part로 변환"""
    # 리사이즈
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    # PNG 바이트로 변환
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return types.Part(
        inline_data=types.Blob(mime_type="image/png", data=buffer.getvalue())
    )


def image_path_to_part(image_path: str, max_size: int = 1024) -> types.Part:
    """이미지 파일 경로를 Gemini API Part로 변환"""
    img = Image.open(image_path).convert("RGB")
    return pil_to_part(img, max_size)


# ============================================================
# JSON 추출
# ============================================================


def extract_json(response_text: str) -> dict:
    """LLM 응답에서 JSON 추출 (마크다운 코드블록 처리)"""
    text = response_text.strip()

    # 마크다운 코드블록 제거
    if text.startswith("```"):
        lines = text.split("\n")
        # 첫 줄(```json 등) 제거, 마지막 줄(```) 제거
        if lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1])
        else:
            text = "\n".join(lines[1:])

    # JSON 파싱
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as e:
        # 에러 시 원본 텍스트 반환
        return {"error": f"JSON parse error: {str(e)}", "raw_text": text}


# ============================================================
# VLM 분석 (단일/멀티 이미지)
# ============================================================


def analyze_with_vlm(
    image_path: str, prompt: str, model_name: str = None, max_size: int = 1024
) -> dict:
    """
    단일 이미지 VLM 분석

    Args:
        image_path: 이미지 파일 경로
        prompt: 분석 프롬프트
        model_name: 사용할 모델 (기본값: VISION_MODEL)
        max_size: 최대 이미지 크기

    Returns:
        JSON 파싱 결과 (dict)
    """
    if model_name is None:
        model_name = VISION_MODEL

    # API 키 설정
    api_key = get_next_api_key()
    genai.configure(api_key=api_key)

    # 이미지 로드
    img_part = image_path_to_part(image_path, max_size)

    # 모델 생성 및 호출
    model = genai.GenerativeModel(model_name)
    response = model.generate_content([prompt, img_part])

    # JSON 추출
    return extract_json(response.text)


def analyze_with_vlm_multi(
    image_paths: List[str], prompt: str, model_name: str = None, max_size: int = 1024
) -> dict:
    """
    멀티 이미지 VLM 분석

    Args:
        image_paths: 이미지 파일 경로 리스트
        prompt: 분석 프롬프트
        model_name: 사용할 모델 (기본값: VISION_MODEL)
        max_size: 최대 이미지 크기

    Returns:
        JSON 파싱 결과 (dict)
    """
    if model_name is None:
        model_name = VISION_MODEL

    # API 키 설정
    api_key = get_next_api_key()
    genai.configure(api_key=api_key)

    # 이미지들을 Part로 변환
    parts = [prompt]
    for img_path in image_paths:
        parts.append(image_path_to_part(img_path, max_size))

    # 모델 생성 및 호출
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(parts)

    # JSON 추출
    return extract_json(response.text)


# ============================================================
# 얼굴 처리
# ============================================================


def detect_faces(image_path: str, model_name: str = None) -> List[FaceInfo]:
    """
    이미지에서 얼굴 감지

    Args:
        image_path: 이미지 경로
        model_name: VLM 모델명 (기본값: VISION_MODEL)

    Returns:
        FaceInfo 리스트
    """
    result = analyze_with_vlm(image_path, FACE_DETECTION_PROMPT, model_name)

    if "error" in result:
        print(f"[WARN] Face detection error: {result['error']}")
        return []

    faces = []
    for face_data in result.get("faces", []):
        bbox_data = face_data.get("bbox", {})
        bbox = BoundingBox(
            x1=bbox_data.get("x1", 0.0),
            y1=bbox_data.get("y1", 0.0),
            x2=bbox_data.get("x2", 1.0),
            y2=bbox_data.get("y2", 1.0),
        )
        face = FaceInfo(
            bbox=bbox,
            position_label=face_data.get("position_label", "center"),
            face_angle=face_data.get("face_angle", "frontal"),
            confidence=face_data.get("confidence", 0.5),
        )
        faces.append(face)

    return faces


def select_best_faces(
    face_folder: str, max_count: int = 2, model_name: str = None
) -> List[str]:
    """
    폴더에서 최적 얼굴 이미지 선택

    Args:
        face_folder: 얼굴 이미지 폴더 경로
        max_count: 선택할 최대 개수
        model_name: VLM 모델명 (기본값: VISION_MODEL)

    Returns:
        선택된 이미지 경로 리스트 (절대 경로)
    """
    # 폴더 내 이미지 찾기
    image_paths = load_images_from_folder(face_folder)

    if not image_paths:
        return []

    if len(image_paths) <= max_count:
        return image_paths

    # VLM으로 선택
    prompt = FACE_SELECTION_PROMPT.format(max_count=max_count)

    # 멀티 이미지 분석 (전체 이미지 전달)
    result = analyze_with_vlm_multi(image_paths, prompt, model_name)

    if "error" in result:
        print(f"[WARN] Face selection error: {result['error']}")
        # 에러 시 앞에서 max_count개 반환
        return image_paths[:max_count]

    # 선택된 파일명 → 절대 경로 매핑
    selected_names = result.get("selected", [])
    folder_path = Path(face_folder).resolve()

    selected_paths = []
    for name in selected_names:
        full_path = folder_path / name
        if full_path.exists():
            selected_paths.append(str(full_path))

    return selected_paths[:max_count]


# ============================================================
# 포즈 처리
# ============================================================


def analyze_pose(image_path: str, model_name: str = None) -> Optional[PoseInfo]:
    """
    이미지에서 포즈 분석

    Args:
        image_path: 이미지 경로
        model_name: VLM 모델명 (기본값: VISION_MODEL)

    Returns:
        PoseInfo 객체 또는 None (에러 시)
    """
    result = analyze_with_vlm(image_path, POSE_ANALYSIS_PROMPT, model_name)

    if "error" in result:
        print(f"[WARN] Pose analysis error: {result['error']}")
        return None

    return PoseInfo(
        body_position=result.get("body_position", "unknown"),
        torso_angle=result.get("torso_angle", "frontal"),
        head_position=result.get("head_position", "neutral"),
        arm_left=result.get("arm_left", "relaxed down"),
        arm_right=result.get("arm_right", "relaxed down"),
        leg_left=result.get("leg_left", "standing straight"),
        leg_right=result.get("leg_right", "standing straight"),
    )


def compare_poses(
    source_path: str,
    reference_path: str,
    threshold: float = 90.0,
    model_name: str = None,
) -> PoseComparison:
    """
    두 이미지의 포즈 비교

    Args:
        source_path: 소스 이미지 (생성된 이미지)
        reference_path: 레퍼런스 이미지 (원본 요청)
        threshold: 매칭 판정 임계값 (기본 90.0)
        model_name: VLM 모델명 (기본값: VISION_MODEL)

    Returns:
        PoseComparison 객체
    """
    result = analyze_with_vlm_multi(
        [source_path, reference_path], POSE_COMPARISON_PROMPT, model_name
    )

    if "error" in result:
        print(f"[WARN] Pose comparison error: {result['error']}")
        # 에러 시 기본값 반환
        return PoseComparison(
            similarity_score=0.0,
            matching_elements=[],
            differing_elements=["analysis_failed"],
            overall_match=False,
        )

    score = result.get("similarity_score", 0.0)

    return PoseComparison(
        similarity_score=score,
        matching_elements=result.get("matching_elements", []),
        differing_elements=result.get("differing_elements", []),
        overall_match=score >= threshold,
    )


# ============================================================
# 이미지 로드
# ============================================================


def load_images_from_folder(folder: str, extensions: List[str] = None) -> List[str]:
    """
    폴더에서 이미지 파일 로드

    Args:
        folder: 폴더 경로
        extensions: 허용 확장자 (기본값: ['.png', '.jpg', '.jpeg', '.webp'])

    Returns:
        이미지 파일 경로 리스트 (절대 경로)
    """
    if extensions is None:
        extensions = [".png", ".jpg", ".jpeg", ".webp"]

    folder_path = Path(folder)
    if not folder_path.exists() or not folder_path.is_dir():
        return []

    image_files = []
    for ext in extensions:
        image_files.extend(folder_path.glob(f"*{ext}"))
        image_files.extend(folder_path.glob(f"*{ext.upper()}"))

    return [str(p.resolve()) for p in sorted(image_files)]
