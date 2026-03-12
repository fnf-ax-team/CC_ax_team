"""
Person-Based Validation Framework

인물 중심 워크플로우를 위한 검증 프레임워크:
- 얼굴 보존 (Face Preservation) - 95%
- 포즈 유사도 (Pose Similarity) - 90%
- 착장 정확도 (Outfit Accuracy) - 85%
- 인물 보존 (Person Preservation) - 100% (배경 교체용)

Usage:
    from core.person_validator import (
        FacePreservationValidator,
        PoseValidator,
        OutfitValidator,
        PersonPreservationValidator,
        run_validation
    )

    # 단일 검증
    validator = FacePreservationValidator(client)
    result = validator.validate(generated_path, reference_path)

    # 복합 검증
    results = run_validation(
        generated_path=output_img,
        reference_paths={
            "face": face_ref_path,
            "pose": pose_ref_path,
            "outfit": [outfit1, outfit2]
        },
        validators=["face", "pose", "outfit"]
    )
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional, Union
from pathlib import Path
import json
from io import BytesIO

from PIL import Image
from google import genai
from google.genai import types

from core.config import VISION_MODEL


class ValidationStatus(Enum):
    """검증 결과 상태"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"


@dataclass
class ValidationResult:
    """검증 결과 데이터클래스"""
    status: ValidationStatus
    score: float
    threshold: float
    details: Dict[str, any]
    issues: List[str]

    @property
    def passed(self) -> bool:
        """통과 여부"""
        return self.status == ValidationStatus.PASS


# 검증 기준 임계값
VALIDATION_THRESHOLDS = {
    "face_identity": 95,
    "pose_similarity": 90,
    "outfit_accuracy": 85,
    "person_preservation": 100,
}


class FacePreservationValidator:
    """얼굴 보존 검증기

    GENERATED 이미지의 얼굴이 REFERENCE 얼굴과 동일인인지 검증.
    임계값: 95
    """

    DEFAULT_THRESHOLD = 95

    VALIDATION_PROMPT = """
Compare the face in the GENERATED image with the REFERENCE face.
Rate face identity preservation on 0-100 scale.

Check:
1. Same person (facial features, structure)
2. Similar skin tone
3. Eye shape/color match
4. Nose/mouth structure match
5. Face proportions preserved

**Strict Criteria:**
- 95-100: 100% identical person. All features perfectly match.
- 85-94: Same person but slight differences due to lighting/angle.
- 70-84: Similar but uncertain. Some features don't match.
- 50-69: Different person. 2+ major features differ (eyes/nose/mouth).
- 0-49: Completely different person. Not recognizable.

**Important:**
- "Similar vibe" ≠ same person
- Ignore hairstyle, makeup, clothes - compare **bone structure only**
- If any doubt → score 70 or below
- If clearly different person → score 50 or below

Return JSON:
{
    "face_identity_score": 0-100,
    "same_person": true/false,
    "skin_tone_match": true/false,
    "eye_match": true/false,
    "nose_match": true/false,
    "mouth_match": true/false,
    "jawline_match": true/false,
    "issues": []
}
"""

    def __init__(self, client: genai.Client, threshold: Optional[int] = None):
        """
        초기화

        Args:
            client: Gemini API 클라이언트
            threshold: 커스텀 임계값 (기본값: 95)
        """
        self.client = client
        self.threshold = threshold or self.DEFAULT_THRESHOLD

    def validate(
        self,
        generated_path: Union[str, Path, Image.Image],
        reference_path: Union[str, Path, Image.Image],
        threshold: Optional[int] = None
    ) -> ValidationResult:
        """
        얼굴 보존 검증 실행

        Args:
            generated_path: 생성된 이미지 경로 또는 PIL Image
            reference_path: 참조 얼굴 이미지 경로 또는 PIL Image
            threshold: 커스텀 임계값 (옵션)

        Returns:
            ValidationResult
        """
        threshold = threshold or self.threshold

        # 이미지 로드
        gen_img = self._load_image(generated_path)
        ref_img = self._load_image(reference_path)

        # VLM 호출
        content_parts = [
            types.Part(text=self.VALIDATION_PROMPT),
            types.Part(text="\n\n[GENERATED IMAGE]"),
            self._pil_to_part(gen_img),
            types.Part(text="\n\n[REFERENCE FACE]"),
            self._pil_to_part(ref_img),
        ]

        try:
            response = self.client.models.generate_content(
                model=VISION_MODEL,
                contents=[types.Content(role="user", parts=content_parts)],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_modalities=["TEXT"]
                )
            )

            # JSON 파싱
            raw_text = response.candidates[0].content.parts[0].text.strip()
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()

            result_dict = json.loads(raw_text)
            score = result_dict.get("face_identity_score", 0)

            # 결과 생성
            status = ValidationStatus.PASS if score >= threshold else ValidationStatus.FAIL
            issues = result_dict.get("issues", [])

            if score < threshold:
                issues.append(f"Face identity score {score} below threshold {threshold}")

            return ValidationResult(
                status=status,
                score=score,
                threshold=threshold,
                details=result_dict,
                issues=issues
            )

        except Exception as e:
            return ValidationResult(
                status=ValidationStatus.FAIL,
                score=0,
                threshold=threshold,
                details={"error": str(e)},
                issues=[f"Validation error: {e}"]
            )

    def _load_image(self, img: Union[str, Path, Image.Image]) -> Image.Image:
        """이미지 로드"""
        if isinstance(img, (str, Path)):
            return Image.open(img).convert("RGB")
        return img.convert("RGB") if img.mode != "RGB" else img

    def _pil_to_part(self, pil_img: Image.Image, max_size: int = 1024) -> types.Part:
        """PIL Image를 Gemini Part로 변환"""
        if max(pil_img.size) > max_size:
            pil_img = pil_img.copy()
            pil_img.thumbnail((max_size, max_size), Image.LANCZOS)
        buffer = BytesIO()
        pil_img.save(buffer, format="PNG")
        return types.Part(inline_data=types.Blob(
            mime_type="image/png",
            data=buffer.getvalue()
        ))


class PoseValidator:
    """포즈 유사도 검증기

    GENERATED 이미지의 포즈가 REFERENCE 포즈와 일치하는지 검증.
    임계값: 90
    """

    DEFAULT_THRESHOLD = 90

    VALIDATION_PROMPT = """
Compare the pose in GENERATED image with REFERENCE pose.
Rate pose similarity on 0-100 scale.

Check each element:
- Body position (standing/sitting/leaning/crouching)
- Arm positions (left/right)
- Leg positions (left/right)
- Head angle
- Weight distribution

**Scoring:**
- 95-100: Identical pose. All elements perfectly match.
- 85-94: Very similar pose. Minor differences in one element.
- 70-84: Similar pose. Some elements differ.
- 50-69: Different pose. Multiple elements don't match.
- 0-49: Completely different pose.

Return JSON:
{
    "pose_similarity_score": 0-100,
    "body_position_match": true/false,
    "left_arm_match": true/false,
    "right_arm_match": true/false,
    "left_leg_match": true/false,
    "right_leg_match": true/false,
    "head_angle_match": true/false,
    "matching_elements": [],
    "differing_elements": [],
    "issues": []
}
"""

    def __init__(self, client: genai.Client, threshold: Optional[int] = None):
        """
        초기화

        Args:
            client: Gemini API 클라이언트
            threshold: 커스텀 임계값 (기본값: 90)
        """
        self.client = client
        self.threshold = threshold or self.DEFAULT_THRESHOLD

    def validate(
        self,
        generated_path: Union[str, Path, Image.Image],
        reference_path: Union[str, Path, Image.Image],
        threshold: Optional[int] = None
    ) -> ValidationResult:
        """
        포즈 유사도 검증 실행

        Args:
            generated_path: 생성된 이미지 경로 또는 PIL Image
            reference_path: 참조 포즈 이미지 경로 또는 PIL Image
            threshold: 커스텀 임계값 (옵션)

        Returns:
            ValidationResult
        """
        threshold = threshold or self.threshold

        # 이미지 로드
        gen_img = self._load_image(generated_path)
        ref_img = self._load_image(reference_path)

        # VLM 호출
        content_parts = [
            types.Part(text=self.VALIDATION_PROMPT),
            types.Part(text="\n\n[GENERATED IMAGE]"),
            self._pil_to_part(gen_img),
            types.Part(text="\n\n[REFERENCE POSE]"),
            self._pil_to_part(ref_img),
        ]

        try:
            response = self.client.models.generate_content(
                model=VISION_MODEL,
                contents=[types.Content(role="user", parts=content_parts)],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_modalities=["TEXT"]
                )
            )

            # JSON 파싱
            raw_text = response.candidates[0].content.parts[0].text.strip()
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()

            result_dict = json.loads(raw_text)
            score = result_dict.get("pose_similarity_score", 0)

            # 결과 생성
            status = ValidationStatus.PASS if score >= threshold else ValidationStatus.FAIL
            issues = result_dict.get("issues", [])

            if score < threshold:
                issues.append(f"Pose similarity score {score} below threshold {threshold}")
                differing = result_dict.get("differing_elements", [])
                if differing:
                    issues.append(f"Differing elements: {', '.join(differing)}")

            return ValidationResult(
                status=status,
                score=score,
                threshold=threshold,
                details=result_dict,
                issues=issues
            )

        except Exception as e:
            return ValidationResult(
                status=ValidationStatus.FAIL,
                score=0,
                threshold=threshold,
                details={"error": str(e)},
                issues=[f"Validation error: {e}"]
            )

    def _load_image(self, img: Union[str, Path, Image.Image]) -> Image.Image:
        """이미지 로드"""
        if isinstance(img, (str, Path)):
            return Image.open(img).convert("RGB")
        return img.convert("RGB") if img.mode != "RGB" else img

    def _pil_to_part(self, pil_img: Image.Image, max_size: int = 1024) -> types.Part:
        """PIL Image를 Gemini Part로 변환"""
        if max(pil_img.size) > max_size:
            pil_img = pil_img.copy()
            pil_img.thumbnail((max_size, max_size), Image.LANCZOS)
        buffer = BytesIO()
        pil_img.save(buffer, format="PNG")
        return types.Part(inline_data=types.Blob(
            mime_type="image/png",
            data=buffer.getvalue()
        ))


class OutfitValidator:
    """착장 정확도 검증기

    GENERATED 이미지의 착장이 REFERENCE 착장과 일치하는지 검증.
    임계값: 85
    """

    DEFAULT_THRESHOLD = 85

    VALIDATION_PROMPT = """
Compare the outfit in GENERATED image with REFERENCE outfit images.
Rate outfit accuracy on 0-100 scale.

Check:
1. All items present (no missing pieces)
2. Colors match exactly
3. Logos/graphics correct position and design
4. Materials/textures look correct
5. Fit/silhouette preserved

**Scoring:**
- 95-100: Perfect match. All items, colors, logos identical.
- 85-94: Excellent. Minor color shade difference or small detail off.
- 70-84: Good. 1 item slightly different or color not exact.
- 50-69: Fair. 2+ items differ or major color mismatch.
- 0-49: Poor. Missing items or completely wrong outfit.

Return JSON:
{
    "outfit_accuracy_score": 0-100,
    "items_present": true/false,
    "color_accuracy": 0-100,
    "logo_accuracy": 0-100,
    "material_accuracy": 0-100,
    "fit_accuracy": 0-100,
    "missing_items": [],
    "color_mismatches": [],
    "issues": []
}
"""

    def __init__(self, client: genai.Client, threshold: Optional[int] = None):
        """
        초기화

        Args:
            client: Gemini API 클라이언트
            threshold: 커스텀 임계값 (기본값: 85)
        """
        self.client = client
        self.threshold = threshold or self.DEFAULT_THRESHOLD

    def validate(
        self,
        generated_path: Union[str, Path, Image.Image],
        outfit_paths: List[Union[str, Path, Image.Image]],
        threshold: Optional[int] = None
    ) -> ValidationResult:
        """
        착장 정확도 검증 실행

        Args:
            generated_path: 생성된 이미지 경로 또는 PIL Image
            outfit_paths: 참조 착장 이미지 리스트 (경로 또는 PIL Image)
            threshold: 커스텀 임계값 (옵션)

        Returns:
            ValidationResult
        """
        threshold = threshold or self.threshold

        # 이미지 로드
        gen_img = self._load_image(generated_path)
        outfit_imgs = [self._load_image(o) for o in outfit_paths]

        # VLM 호출
        content_parts = [
            types.Part(text=self.VALIDATION_PROMPT),
            types.Part(text="\n\n[GENERATED IMAGE]"),
            self._pil_to_part(gen_img),
            types.Part(text="\n\n[REFERENCE OUTFIT IMAGES]"),
        ]

        for outfit in outfit_imgs[:5]:  # 최대 5개
            content_parts.append(self._pil_to_part(outfit))

        try:
            response = self.client.models.generate_content(
                model=VISION_MODEL,
                contents=[types.Content(role="user", parts=content_parts)],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_modalities=["TEXT"]
                )
            )

            # JSON 파싱
            raw_text = response.candidates[0].content.parts[0].text.strip()
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()

            result_dict = json.loads(raw_text)
            score = result_dict.get("outfit_accuracy_score", 0)

            # 결과 생성
            status = ValidationStatus.PASS if score >= threshold else ValidationStatus.FAIL
            issues = result_dict.get("issues", [])

            if score < threshold:
                issues.append(f"Outfit accuracy score {score} below threshold {threshold}")
                missing = result_dict.get("missing_items", [])
                if missing:
                    issues.append(f"Missing items: {', '.join(missing)}")
                mismatches = result_dict.get("color_mismatches", [])
                if mismatches:
                    issues.append(f"Color mismatches: {', '.join(mismatches)}")

            return ValidationResult(
                status=status,
                score=score,
                threshold=threshold,
                details=result_dict,
                issues=issues
            )

        except Exception as e:
            return ValidationResult(
                status=ValidationStatus.FAIL,
                score=0,
                threshold=threshold,
                details={"error": str(e)},
                issues=[f"Validation error: {e}"]
            )

    def _load_image(self, img: Union[str, Path, Image.Image]) -> Image.Image:
        """이미지 로드"""
        if isinstance(img, (str, Path)):
            return Image.open(img).convert("RGB")
        return img.convert("RGB") if img.mode != "RGB" else img

    def _pil_to_part(self, pil_img: Image.Image, max_size: int = 1024) -> types.Part:
        """PIL Image를 Gemini Part로 변환"""
        if max(pil_img.size) > max_size:
            pil_img = pil_img.copy()
            pil_img.thumbnail((max_size, max_size), Image.LANCZOS)
        buffer = BytesIO()
        pil_img.save(buffer, format="PNG")
        return types.Part(inline_data=types.Blob(
            mime_type="image/png",
            data=buffer.getvalue()
        ))


class PersonPreservationValidator:
    """인물 보존 검증기

    배경 교체 시나리오 - GENERATED 이미지의 인물이 REFERENCE와 100% 동일한지 검증.
    임계값: 100 (완벽 일치 요구)
    """

    DEFAULT_THRESHOLD = 100

    VALIDATION_PROMPT = """
Verify the person in GENERATED matches REFERENCE exactly.
For background swap scenarios - person must be IDENTICAL.

Check:
- Face identical (same person, same expression)
- Pose identical (body position, arms, legs, head angle)
- Outfit identical (all items, colors, logos)
- Body proportions identical

**This is a STRICT check for background swap workflows.**
Any difference in the person = FAIL.

**Scoring:**
- 100: Person is 100% identical. Face, pose, outfit, proportions all match perfectly.
- 90-99: Person is same but has small differences (slight pose variation, expression change).
- 80-89: Person is similar but noticeable differences.
- 0-79: Person is different. FAIL for background swap.

Return JSON:
{
    "preservation_score": 0-100,
    "face_preserved": true/false,
    "expression_preserved": true/false,
    "pose_preserved": true/false,
    "outfit_preserved": true/false,
    "proportions_preserved": true/false,
    "issues": []
}
"""

    def __init__(self, client: genai.Client, threshold: Optional[int] = None):
        """
        초기화

        Args:
            client: Gemini API 클라이언트
            threshold: 커스텀 임계값 (기본값: 100)
        """
        self.client = client
        self.threshold = threshold or self.DEFAULT_THRESHOLD

    def validate(
        self,
        generated_path: Union[str, Path, Image.Image],
        reference_path: Union[str, Path, Image.Image],
        threshold: Optional[int] = None
    ) -> ValidationResult:
        """
        인물 보존 검증 실행

        Args:
            generated_path: 생성된 이미지 경로 또는 PIL Image
            reference_path: 참조 인물 이미지 경로 또는 PIL Image
            threshold: 커스텀 임계값 (옵션)

        Returns:
            ValidationResult
        """
        threshold = threshold or self.threshold

        # 이미지 로드
        gen_img = self._load_image(generated_path)
        ref_img = self._load_image(reference_path)

        # VLM 호출
        content_parts = [
            types.Part(text=self.VALIDATION_PROMPT),
            types.Part(text="\n\n[GENERATED IMAGE]"),
            self._pil_to_part(gen_img),
            types.Part(text="\n\n[REFERENCE PERSON]"),
            self._pil_to_part(ref_img),
        ]

        try:
            response = self.client.models.generate_content(
                model=VISION_MODEL,
                contents=[types.Content(role="user", parts=content_parts)],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_modalities=["TEXT"]
                )
            )

            # JSON 파싱
            raw_text = response.candidates[0].content.parts[0].text.strip()
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()

            result_dict = json.loads(raw_text)
            score = result_dict.get("preservation_score", 0)

            # 결과 생성
            status = ValidationStatus.PASS if score >= threshold else ValidationStatus.FAIL
            issues = result_dict.get("issues", [])

            if score < threshold:
                issues.append(f"Person preservation score {score} below threshold {threshold}")
                if not result_dict.get("face_preserved"):
                    issues.append("Face not preserved")
                if not result_dict.get("pose_preserved"):
                    issues.append("Pose not preserved")
                if not result_dict.get("outfit_preserved"):
                    issues.append("Outfit not preserved")

            return ValidationResult(
                status=status,
                score=score,
                threshold=threshold,
                details=result_dict,
                issues=issues
            )

        except Exception as e:
            return ValidationResult(
                status=ValidationStatus.FAIL,
                score=0,
                threshold=threshold,
                details={"error": str(e)},
                issues=[f"Validation error: {e}"]
            )

    def _load_image(self, img: Union[str, Path, Image.Image]) -> Image.Image:
        """이미지 로드"""
        if isinstance(img, (str, Path)):
            return Image.open(img).convert("RGB")
        return img.convert("RGB") if img.mode != "RGB" else img

    def _pil_to_part(self, pil_img: Image.Image, max_size: int = 1024) -> types.Part:
        """PIL Image를 Gemini Part로 변환"""
        if max(pil_img.size) > max_size:
            pil_img = pil_img.copy()
            pil_img.thumbnail((max_size, max_size), Image.LANCZOS)
        buffer = BytesIO()
        pil_img.save(buffer, format="PNG")
        return types.Part(inline_data=types.Blob(
            mime_type="image/png",
            data=buffer.getvalue()
        ))


def run_validation(
    generated_path: Union[str, Path, Image.Image],
    reference_paths: Dict[str, Union[str, Path, Image.Image, List]],
    validators: List[str],
    client: genai.Client,
    thresholds: Optional[Dict[str, int]] = None
) -> Dict[str, ValidationResult]:
    """
    복합 검증 실행

    Args:
        generated_path: 생성된 이미지 경로 또는 PIL Image
        reference_paths: 참조 이미지 딕셔너리
            {
                "face": str/Path/Image,
                "pose": str/Path/Image,
                "outfit": [str/Path/Image, ...],
                "person": str/Path/Image
            }
        validators: 실행할 검증기 리스트 ["face", "pose", "outfit", "person"]
        client: Gemini API 클라이언트
        thresholds: 커스텀 임계값 딕셔너리 (옵션)

    Returns:
        Dict[str, ValidationResult]: 각 검증기의 결과

    Example:
        results = run_validation(
            generated_path="output.png",
            reference_paths={
                "face": "face_ref.png",
                "pose": "pose_ref.png",
                "outfit": ["outfit1.png", "outfit2.png"]
            },
            validators=["face", "pose", "outfit"],
            client=client
        )

        if results["face"].passed and results["pose"].passed:
            print("Face and pose validation passed!")
    """
    thresholds = thresholds or {}
    results = {}

    if "face" in validators:
        validator = FacePreservationValidator(client, thresholds.get("face_identity"))
        results["face"] = validator.validate(
            generated_path,
            reference_paths.get("face")
        )

    if "pose" in validators:
        validator = PoseValidator(client, thresholds.get("pose_similarity"))
        results["pose"] = validator.validate(
            generated_path,
            reference_paths.get("pose")
        )

    if "outfit" in validators:
        validator = OutfitValidator(client, thresholds.get("outfit_accuracy"))
        outfit_paths = reference_paths.get("outfit", [])
        if not isinstance(outfit_paths, list):
            outfit_paths = [outfit_paths]
        results["outfit"] = validator.validate(
            generated_path,
            outfit_paths
        )

    if "person" in validators:
        validator = PersonPreservationValidator(client, thresholds.get("person_preservation"))
        results["person"] = validator.validate(
            generated_path,
            reference_paths.get("person")
        )

    return results
