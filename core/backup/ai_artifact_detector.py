"""
AI Artifact Detector - AI 생성 이미지의 아티팩트 감지 모듈

점수 방향 주의:
- 높을수록 AI스러움 (0=실제사진급, 100=명백한AI)
- MLBValidator와 반대 방향 (MLBValidator: 높을수록 좋음)
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Union
from pathlib import Path
from PIL import Image
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed

from google import genai
from google.genai import types
from core.config import VISION_MODEL


class Severity(Enum):
    """아티팩트 심각도"""
    CRITICAL = "CRITICAL"  # 즉시 재생성 필요
    HIGH = "HIGH"          # 눈에 띄는 문제
    MEDIUM = "MEDIUM"      # 약간 신경쓰임
    LOW = "LOW"            # 사소한 이슈


@dataclass
class ArtifactIssue:
    """감지된 아티팩트 문제"""
    category: str           # skin, hands, face, background, clothing, lighting
    issue_type: str         # 구체적 문제 유형
    description: str        # 문제 설명
    location: str           # 위치 (예: "left hand", "forehead")
    severity: Severity
    suggestion: str         # 해결 제안


@dataclass
class AIArtifactResult:
    """AI 아티팩트 감지 결과"""
    # 카테고리별 점수 (높을수록 AI 티 많음, 0-100)
    skin_score: int
    hands_score: int
    face_score: int
    background_score: int
    clothing_score: int
    lighting_score: int

    # 종합
    total_ai_score: int     # 가중 평균
    naturalness_grade: str  # S/A/B/C/F
    issues: List[ArtifactIssue]
    critical_issues: List[str]
    suggestions: List[str]
    prompt_improvements: List[str]

    # 메타데이터
    image_path: Optional[str] = None


@dataclass
class GateCheckItem:
    """게이트 체크 개별 항목"""
    criterion_id: str  # eyes_unnatural, skin_synthetic, etc.
    criterion_name: str
    passed: bool
    failed_details: List[str] = field(default_factory=list)


@dataclass
class AIArtifactResultV2:
    """AI 아티팩트 감지 결과 v2 (게이트+루브릭)"""
    # Gate 결과
    gate_passed: bool
    gate_checks: List[GateCheckItem]
    gate_failed_reasons: List[str]

    # Rubric 결과 (gate 통과 시에만 유효)
    rubric_score: int  # 0, 70, 80, 90, 100
    rubric_level: str  # "게이트 실패", "재작업 권장", "서브컷 가능", "상업용 OK", "캠페인급"

    # 카테고리별 세부 점수 (루브릭 채점용)
    category_scores: Dict[str, int]  # skin, lighting, outfit, composition, overall

    # Pass 여부
    is_passed: bool  # 모든 카테고리 >= 88
    min_score: int
    min_category: str

    # 개선 제안
    improvement_suggestions: List[str]
    prompt_improvements: List[str]

    # 메타데이터
    image_path: Optional[str] = None


class AIArtifactDetector:
    """AI 생성 이미지의 아티팩트를 감지하는 클래스

    점수 방향 주의:
    - 높을수록 AI스러움 (0=실제사진급, 100=명백한AI)
    - MLBValidator와 반대 방향 (MLBValidator: 높을수록 좋음)
    """

    # 가중치 상수
    WEIGHTS = {
        "skin": 0.15,       # 피부: 15%
        "hands": 0.25,      # 손: 25% (가장 중요 - AI 실수 빈번)
        "face": 0.20,       # 얼굴: 20%
        "background": 0.15, # 배경: 15%
        "clothing": 0.15,   # 착장: 15%
        "lighting": 0.10    # 조명: 10%
    }

    # VLM 분석 프롬프트
    AI_ARTIFACT_DETECTION_PROMPT = """
## AI-Generated Image Artifact Detection

이 이미지가 AI로 생성되었는지 분석하고, 어떤 부분에서 "AI 티"가 나는지 구체적으로 지목하세요.

### 분석 기준 (각 0-100점, 높을수록 AI스러움)

#### 1. SKIN (피부) - 15%
- 플라스틱/밀랍 같은 피부 (모공 없음)
- 과도한 스무딩/에어브러시 효과
- 피부색 불균일, 부자연스러운 경계
- 이상한 광택/반사

#### 2. HANDS (손/손가락) - 25%
- 손가락 개수 (5개 아님)
- 손가락 관절/길이/두께 이상
- 손톱 유무/형태 이상
- 손 전체 구조 붕괴

#### 3. FACE (눈/얼굴) - 20%
- 좌우 눈 비대칭 (크기, 위치, 홍채)
- 동공/반사광 불일치
- 치아 개수/정렬 이상
- 귀 형태/위치 이상
- 헤어라인 부자연스러움

#### 4. BACKGROUND (배경) - 15%
- 읽을 수 없는 텍스트/로고
- 반복 패턴/타일링
- 원근법 오류
- 인물-배경 경계 부자연스러움

#### 5. CLOTHING (착장) - 15%
- 로고/텍스트 왜곡
- 주름 물리법칙 무시
- 소재 질감 오류
- 색상 번짐/경계 불명확

#### 6. LIGHTING (조명) - 10%
- 그림자 방향 불일치
- 다중 광원 하이라이트
- 색온도 이상 (과도한 따뜻/차가움)
- 환경광 반영 없음

### 응답 형식 (JSON)

```json
{
  "scores": {
    "skin": <0-100>,
    "hands": <0-100>,
    "face": <0-100>,
    "background": <0-100>,
    "clothing": <0-100>,
    "lighting": <0-100>
  },
  "issues": [
    {
      "category": "<카테고리>",
      "type": "<문제 유형>",
      "description": "<구체적 설명>",
      "location": "<위치>",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "suggestion": "<해결 제안>"
    }
  ],
  "critical_issues": ["<심각한 문제 요약>"],
  "naturalness_summary": "<한국어 1-2문장 요약>",
  "overall_ai_score": <0-100 가중평균>,
  "grade": "S|A|B|C|F",
  "suggestions": ["<전체 제안 사항>"],
  "prompt_improvements": ["<프롬프트 개선 문구>"]
}
```

### 등급 기준
- S (0-15): 실제 사진 수준, AI 티 거의 없음
- A (16-30): 자연스러움, 사소한 이슈만
- B (31-50): 약간 인공적, 눈에 띄는 문제 있음
- C (51-70): AI 생성 티 명확
- F (71-100): 심각한 아티팩트, 사용 불가
"""

    # Gate Check 프롬프트 (Step 0)
    GATE_CHECK_PROMPT = """
## AI 합성티 게이트 검사

이 이미지에서 AI 합성 아티팩트를 검사합니다.
아래 항목 중 하나라도 해당되면 FAIL입니다.

### 체크 항목

1. eyes_unnatural (눈/시선 인공감)
   - ring catchlight: 도넛 모양 반사광
   - white sclera: 공막이 너무 하얗고 균일
   - gaze mismatch: 양 눈 시선 방향 불일치

2. skin_synthetic (피부 플라스틱/과샤픈)
   - no pores: 모공 완전 부재
   - over-sharpened: 경계가 과도하게 날카로움
   - waxy surface: 밀랍/도자기 표면

3. anatomy_artifacts (손/입/귀/헤어라인)
   - finger count: 손가락 5개 아님
   - deformed fingers: 기형적 손가락/관절
   - mouth/teeth: 입술/치아 왜곡
   - ear abnormal: 귀 형태 이상
   - hairline: 헤어라인 부자연스러움

4. lighting_physics (조명 물리 위반)
   - shadow mismatch: 그림자 방향 불일치
   - no contact shadows: 발/손 아래 그림자 없음
   - multiple highlights: 다중 광원 불일치

5. logo_text_errors (로고/텍스트 오류)
   - logo distortion: 로고 번짐/왜곡
   - unreadable text: 읽을 수 없는 텍스트

### 응답 형식 (JSON)

```json
{
  "gate_passed": true,
  "checks": {
    "eyes_unnatural": {
      "passed": true,
      "failed_items": []
    },
    "skin_synthetic": {
      "passed": false,
      "failed_items": ["no pores", "over-sharpened"]
    },
    "anatomy_artifacts": {
      "passed": true,
      "failed_items": []
    },
    "lighting_physics": {
      "passed": true,
      "failed_items": []
    },
    "logo_text_errors": {
      "passed": true,
      "failed_items": []
    }
  },
  "failed_summary": ["피부 모공 부재", "피부 경계 과샤픈"]
}
```
"""

    # Rubric Score 프롬프트 (Step 1)
    RUBRIC_SCORE_PROMPT = """
## 상업 품질 등급 채점

게이트를 통과한 이미지의 상업적 품질을 평가합니다.

### 등급 기준
- 100: 캠페인 키비주얼급 (매거진/광고 메인)
- 90: 상업용 OK (이커머스/SNS 메인)
- 80: 서브컷 가능 (보조 이미지)
- 70: 재작업 권장 (품질 미달)

### 평가 카테고리
1. skin: 피부 텍스처 자연스러움
2. lighting: 조명/그림자 자연스러움
3. outfit: 착장 디테일 (로고, 주름, 소재)
4. composition: 구도/프레이밍
5. overall: 전체 분위기/완성도

### 응답 형식 (JSON)

```json
{
  "category_scores": {
    "skin": 90,
    "lighting": 85,
    "outfit": 80,
    "composition": 90,
    "overall": 85
  },
  "rubric_score": 80,
  "rubric_level": "서브컷 가능",
  "reasoning": "피부와 구도는 좋으나 착장 디테일이 약간 아쉬움",
  "improvement_suggestions": [
    "착장 로고 디테일 개선 필요",
    "주름 표현 더 자연스럽게"
  ],
  "prompt_improvements": [
    "프롬프트에 'fabric texture details' 추가",
    "'natural clothing wrinkles' 명시"
  ]
}
```
"""

    def __init__(
        self,
        client: genai.Client,  # 외부에서 주입 (MLBValidator 패턴)
        thresholds: Optional[Dict[str, int]] = None
    ):
        """
        Args:
            client: Google GenAI 클라이언트 (외부 주입)
            thresholds: 카테고리별 임계값 (기본값 사용 시 None)
        """
        self.client = client
        self.thresholds = thresholds or {
            "skin": 50,
            "hands": 30,  # 손은 더 엄격
            "face": 40,
            "background": 60,
            "clothing": 50,
            "lighting": 60
        }

    def detect(
        self,
        image: Union[str, Path, Image.Image]
    ) -> AIArtifactResult:
        """단일 이미지 AI 티 감지

        Args:
            image: 이미지 경로 또는 PIL Image

        Returns:
            AIArtifactResult: 감지 결과
        """
        try:
            # 이미지 로드
            pil_img = self._load_image(image)

            # 이미지 경로 추출 (메타데이터용)
            image_path = str(image) if isinstance(image, (str, Path)) else None

            # Gemini Part로 변환
            img_part = self._pil_to_part(pil_img)

            # VLM 호출
            content_parts = [
                types.Part(text=self.AI_ARTIFACT_DETECTION_PROMPT),
                img_part
            ]

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

            # 결과 변환
            return self._parse_result(result_dict, image_path)

        except json.JSONDecodeError as e:
            print(f"[AIArtifactDetector] JSON parse error: {e}")
            return self._create_error_result(str(image), f"JSON parse error: {e}")
        except Exception as e:
            print(f"[AIArtifactDetector] Detection error: {e}")
            return self._create_error_result(str(image), f"Detection error: {e}")

    def detect_with_context(
        self,
        image: Union[str, Path, Image.Image],
        original_prompt: Optional[str] = None
    ) -> AIArtifactResult:
        """원본 프롬프트 컨텍스트와 함께 감지

        Args:
            image: 이미지 경로 또는 PIL Image
            original_prompt: 이미지 생성에 사용된 원본 프롬프트 (선택)
                           - 제공 시: 프롬프트 기반 개선안 생성
                           - 미제공 시: "권장 추가 문구" 형태로 출력

        Returns:
            AIArtifactResult: 감지 결과 (프롬프트 개선안 포함)
        """
        try:
            # 이미지 로드
            pil_img = self._load_image(image)
            image_path = str(image) if isinstance(image, (str, Path)) else None

            # Gemini Part로 변환
            img_part = self._pil_to_part(pil_img)

            # 프롬프트에 컨텍스트 추가
            context_prompt = self.AI_ARTIFACT_DETECTION_PROMPT
            if original_prompt:
                context_prompt += f"\n\n### Original Prompt (참조용)\n{original_prompt}\n\n" \
                                 "프롬프트 개선 시 위 원본 프롬프트를 기반으로 수정안을 제시하세요."

            # VLM 호출
            content_parts = [
                types.Part(text=context_prompt),
                img_part
            ]

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

            # 결과 변환
            return self._parse_result(result_dict, image_path)

        except json.JSONDecodeError as e:
            print(f"[AIArtifactDetector] JSON parse error: {e}")
            return self._create_error_result(str(image), f"JSON parse error: {e}")
        except Exception as e:
            print(f"[AIArtifactDetector] Detection error: {e}")
            return self._create_error_result(str(image), f"Detection error: {e}")

    def batch_detect(
        self,
        image_paths: List[str],
        max_workers: int = 3
    ) -> List[AIArtifactResult]:
        """배치 이미지 병렬 분석

        ThreadPoolExecutor를 사용한 병렬 처리.
        API Rate Limit 고려하여 기본 max_workers=3.

        Args:
            image_paths: 분석할 이미지 경로 리스트
            max_workers: 최대 병렬 워커 수 (기본 3, API 제한 고려)

        Returns:
            List[AIArtifactResult]: 입력 순서와 동일한 순서의 결과 리스트

        Example:
            >>> detector = AIArtifactDetector(client)
            >>> results = detector.batch_detect([
            ...     "output/image1.png",
            ...     "output/image2.png",
            ...     "output/image3.png"
            ... ])
            >>> for i, result in enumerate(results):
            ...     print(f"Image {i+1}: AI Score = {result.total_ai_score}")
        """
        results = [None] * len(image_paths)  # 순서 보장용

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # (index, path) 튜플로 제출하여 순서 추적
            future_to_idx = {
                executor.submit(self.detect, path): idx
                for idx, path in enumerate(image_paths)
            }

            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    # 실패 시 에러 결과 생성
                    results[idx] = self._create_error_result(
                        image_paths[idx],
                        str(e)
                    )

        return results

    def detect_v2(
        self,
        image: Union[str, Path, Image.Image]
    ) -> AIArtifactResultV2:
        """게이트+루브릭 방식 감지 (v2)

        Args:
            image: 이미지 경로 또는 PIL Image

        Returns:
            AIArtifactResultV2: 게이트+루브릭 감지 결과
        """
        try:
            # 이미지 로드
            pil_img = self._load_image(image)
            image_path = str(image) if isinstance(image, (str, Path)) else None

            # Step 0: Gate 체크
            gate_result = self._check_gate(pil_img)

            if not gate_result["gate_passed"]:
                return AIArtifactResultV2(
                    gate_passed=False,
                    gate_checks=gate_result["gate_checks"],
                    gate_failed_reasons=gate_result["failed_summary"],
                    rubric_score=0,
                    rubric_level="게이트 실패",
                    category_scores={},
                    is_passed=False,
                    min_score=0,
                    min_category="gate",
                    improvement_suggestions=self._get_gate_improvements(gate_result),
                    prompt_improvements=self._get_gate_prompt_improvements(gate_result),
                    image_path=image_path
                )

            # Step 1: Rubric 채점
            rubric_result = self._score_rubric(pil_img)

            min_score = min(rubric_result["category_scores"].values())
            min_category = min(
                rubric_result["category_scores"],
                key=rubric_result["category_scores"].get
            )
            is_passed = min_score >= 88

            return AIArtifactResultV2(
                gate_passed=True,
                gate_checks=gate_result["gate_checks"],
                gate_failed_reasons=[],
                rubric_score=rubric_result["rubric_score"],
                rubric_level=rubric_result["rubric_level"],
                category_scores=rubric_result["category_scores"],
                is_passed=is_passed,
                min_score=min_score,
                min_category=min_category,
                improvement_suggestions=rubric_result.get("improvement_suggestions", []),
                prompt_improvements=rubric_result.get("prompt_improvements", []),
                image_path=image_path
            )

        except Exception as e:
            print(f"[AIArtifactDetector] detect_v2 error: {e}")
            # 에러 시 게이트 실패로 처리
            return AIArtifactResultV2(
                gate_passed=False,
                gate_checks=[],
                gate_failed_reasons=[f"분석 실패: {str(e)}"],
                rubric_score=0,
                rubric_level="게이트 실패",
                category_scores={},
                is_passed=False,
                min_score=0,
                min_category="error",
                improvement_suggestions=[],
                prompt_improvements=[],
                image_path=str(image) if isinstance(image, (str, Path)) else None
            )

    def batch_detect_v2(
        self,
        image_paths: List[str],
        max_workers: int = 3
    ) -> List[AIArtifactResultV2]:
        """배치 이미지 병렬 분석 (v2 게이트+루브릭)

        Args:
            image_paths: 분석할 이미지 경로 리스트
            max_workers: 최대 병렬 워커 수 (기본 3)

        Returns:
            List[AIArtifactResultV2]: 입력 순서와 동일한 순서의 결과 리스트
        """
        results = [None] * len(image_paths)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(self.detect_v2, path): idx
                for idx, path in enumerate(image_paths)
            }

            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    # 실패 시 게이트 실패 결과 생성
                    results[idx] = AIArtifactResultV2(
                        gate_passed=False,
                        gate_checks=[],
                        gate_failed_reasons=[f"분석 실패: {str(e)}"],
                        rubric_score=0,
                        rubric_level="게이트 실패",
                        category_scores={},
                        is_passed=False,
                        min_score=0,
                        min_category="error",
                        improvement_suggestions=[],
                        prompt_improvements=[],
                        image_path=image_paths[idx]
                    )

        return results

    def _check_gate(self, pil_img: Image.Image) -> Dict:
        """Step 0: 합성티 게이트 체크

        Returns:
            Dict with keys: gate_passed, checks, failed_summary
        """
        img_part = self._pil_to_part(pil_img)

        content_parts = [
            types.Part(text=self.GATE_CHECK_PROMPT),
            img_part
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

            raw_text = response.candidates[0].content.parts[0].text.strip()
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()

            result = json.loads(raw_text)

            # GateCheckItem 리스트로 변환
            gate_checks = []
            checks_dict = result.get("checks", {})

            criterion_names = {
                "eyes_unnatural": "눈/시선 인공감",
                "skin_synthetic": "피부 플라스틱/과샤픈",
                "anatomy_artifacts": "손/입/귀/헤어라인",
                "lighting_physics": "조명 물리 위반",
                "logo_text_errors": "로고/텍스트 오류"
            }

            for criterion_id, criterion_name in criterion_names.items():
                check_data = checks_dict.get(criterion_id, {"passed": True, "failed_items": []})
                gate_checks.append(GateCheckItem(
                    criterion_id=criterion_id,
                    criterion_name=criterion_name,
                    passed=check_data.get("passed", True),
                    failed_details=check_data.get("failed_items", [])
                ))

            return {
                "gate_passed": result.get("gate_passed", True),
                "gate_checks": gate_checks,
                "failed_summary": result.get("failed_summary", [])
            }

        except Exception as e:
            print(f"[AIArtifactDetector] Gate check error: {e}")
            # 파싱 실패 시 게이트 실패
            return {
                "gate_passed": False,
                "gate_checks": [],
                "failed_summary": [f"게이트 체크 실패: {str(e)}"]
            }

    def _score_rubric(self, pil_img: Image.Image) -> Dict:
        """Step 1: 루브릭 채점 (게이트 통과 후)

        Returns:
            Dict with keys: category_scores, rubric_score, rubric_level, reasoning, etc.
        """
        img_part = self._pil_to_part(pil_img)

        content_parts = [
            types.Part(text=self.RUBRIC_SCORE_PROMPT),
            img_part
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

            raw_text = response.candidates[0].content.parts[0].text.strip()
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()

            result = json.loads(raw_text)

            return {
                "category_scores": result.get("category_scores", {}),
                "rubric_score": result.get("rubric_score", 70),
                "rubric_level": result.get("rubric_level", "재작업 권장"),
                "reasoning": result.get("reasoning", ""),
                "improvement_suggestions": result.get("improvement_suggestions", []),
                "prompt_improvements": result.get("prompt_improvements", [])
            }

        except Exception as e:
            print(f"[AIArtifactDetector] Rubric scoring error: {e}")
            # 파싱 실패 시 기본 점수
            return {
                "category_scores": {"skin": 70, "lighting": 70, "outfit": 70, "composition": 70, "overall": 70},
                "rubric_score": 70,
                "rubric_level": "재작업 권장",
                "reasoning": f"루브릭 채점 실패: {str(e)}",
                "improvement_suggestions": [],
                "prompt_improvements": []
            }

    def _get_gate_improvements(self, gate_result: Dict) -> List[str]:
        """게이트 실패 시 개선 제안 생성"""
        suggestions = []
        for check in gate_result["gate_checks"]:
            if not check.passed and check.failed_details:
                for detail in check.failed_details:
                    suggestions.append(f"{check.criterion_name}: {detail} 개선 필요")
        return suggestions

    def _get_gate_prompt_improvements(self, gate_result: Dict) -> List[str]:
        """게이트 실패 시 프롬프트 개선안 생성"""
        improvements = []

        # 각 게이트 항목별 프롬프트 개선 문구 매핑
        prompt_map = {
            "eyes_unnatural": "프롬프트에 'natural eye reflections, realistic gaze direction' 추가",
            "skin_synthetic": "프롬프트에 'visible skin pores, natural skin texture' 추가",
            "anatomy_artifacts": "프롬프트에 'anatomically correct hands, 5 fingers, natural hairline' 추가",
            "lighting_physics": "프롬프트에 'physically accurate shadows, consistent lighting direction' 추가",
            "logo_text_errors": "프롬프트에 'sharp logo details, readable text' 추가"
        }

        for check in gate_result["gate_checks"]:
            if not check.passed:
                improvement = prompt_map.get(check.criterion_id)
                if improvement:
                    improvements.append(improvement)

        return improvements

    def _calculate_total_score(self, scores: Dict[str, int]) -> int:
        """가중 평균으로 총점 계산

        공식: total = sum(scores[cat] * WEIGHTS[cat] for cat in WEIGHTS)

        가중치:
        - skin: 15% (피부)
        - hands: 25% (손 - 가장 중요)
        - face: 20% (얼굴)
        - background: 15% (배경)
        - clothing: 15% (착장)
        - lighting: 10% (조명)

        Returns:
            int: 0-100 범위의 총 AI 점수 (높을수록 AI스러움)
        """
        total = sum(
            scores.get(cat, 0) * weight
            for cat, weight in self.WEIGHTS.items()
        )
        return round(total)

    def _load_image(self, img: Union[str, Path, Image.Image]) -> Image.Image:
        """이미지 로드 (core/mlb_validator.py:569-573 패턴)"""
        if isinstance(img, (str, Path)):
            return Image.open(img).convert("RGB")
        return img.convert("RGB") if img.mode != "RGB" else img

    def _pil_to_part(self, pil_img: Image.Image, max_size: int = 1024) -> types.Part:
        """PIL Image를 Gemini Part로 변환 (core/mlb_validator.py:575-585 패턴)"""
        if max(pil_img.size) > max_size:
            pil_img = pil_img.copy()
            pil_img.thumbnail((max_size, max_size), Image.LANCZOS)
        buffer = BytesIO()
        pil_img.save(buffer, format="PNG")
        return types.Part(inline_data=types.Blob(
            mime_type="image/png",
            data=buffer.getvalue()
        ))

    def _parse_result(self, result_dict: Dict, image_path: Optional[str]) -> AIArtifactResult:
        """VLM 응답을 AIArtifactResult로 변환"""
        scores = result_dict.get("scores", {})

        # 이슈 파싱
        issues = []
        for issue_data in result_dict.get("issues", []):
            try:
                severity_str = issue_data.get("severity", "MEDIUM")
                severity = Severity[severity_str]
            except KeyError:
                severity = Severity.MEDIUM

            issues.append(ArtifactIssue(
                category=issue_data.get("category", "unknown"),
                issue_type=issue_data.get("type", ""),
                description=issue_data.get("description", ""),
                location=issue_data.get("location", ""),
                severity=severity,
                suggestion=issue_data.get("suggestion", "")
            ))

        return AIArtifactResult(
            skin_score=scores.get("skin", 0),
            hands_score=scores.get("hands", 0),
            face_score=scores.get("face", 0),
            background_score=scores.get("background", 0),
            clothing_score=scores.get("clothing", 0),
            lighting_score=scores.get("lighting", 0),
            total_ai_score=result_dict.get("overall_ai_score",
                                          self._calculate_total_score(scores)),
            naturalness_grade=result_dict.get("grade", "C"),
            issues=issues,
            critical_issues=result_dict.get("critical_issues", []),
            suggestions=result_dict.get("suggestions", []),
            prompt_improvements=result_dict.get("prompt_improvements", []),
            image_path=image_path
        )

    def _create_error_result(self, image_path: str, error_msg: str) -> AIArtifactResult:
        """에러 발생 시 기본 결과 생성"""
        return AIArtifactResult(
            skin_score=0,
            hands_score=0,
            face_score=0,
            background_score=0,
            clothing_score=0,
            lighting_score=0,
            total_ai_score=0,
            naturalness_grade="ERROR",
            issues=[],
            critical_issues=[f"분석 실패: {error_msg}"],
            suggestions=[],
            prompt_improvements=[],
            image_path=image_path
        )
