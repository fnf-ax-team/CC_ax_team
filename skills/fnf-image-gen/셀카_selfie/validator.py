"""
Selfie/UGC Validator (v1.0 - 5 Criteria)

셀카/UGC 품질 검증 모듈:
- 5개 기준 (realism, person_preservation, scenario_fit, skin_condition, anti_polish_factor)
- "너무 잘 나오면 실패" 원칙 (anti-polish logic)
- Auto-fail 조건
- Grade 시스템 (S/A/B/C/F)
- 한국어 요약 지원
"""

from dataclasses import dataclass, field
from typing import Optional, List, Union, Tuple
from enum import Enum
from pathlib import Path
import json
from io import BytesIO

from PIL import Image
from google import genai
from google.genai import types

from core.config import VISION_MODEL


class SelfieQualityTier(Enum):
    """셀카/UGC 품질 티어"""

    RELEASE_READY = "RELEASE_READY"  # 90+: 즉시 사용 가능
    NEEDS_MINOR_EDIT = "NEEDS_MINOR_EDIT"  # 75-89: 소폭 보정 후 사용
    REGENERATE = "REGENERATE"  # <75: 재생성 필요


@dataclass
class SelfieValidationResult:
    """셀카/UGC 검증 결과 (5개 기준)"""

    # 5개 검증 기준
    realism: int  # 35% - 실제 사진처럼 보이는가
    person_preservation: int  # 25% - 얼굴이 참조와 같은 사람인가
    scenario_fit: int  # 20% - 장소/상황/옷이 자연스럽게 어울리는가
    skin_condition: int  # 10% - 피부 질감이 자연스러운가
    anti_polish_factor: int  # 10% - 너무 완벽하지 않은가 (결점이 자연스러움)

    # 종합 결과
    total_score: int
    tier: SelfieQualityTier
    grade: str  # S/A/B/C/F
    passed: bool
    auto_fail: bool
    auto_fail_reasons: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    summary_kr: str = ""
    raw_response: Optional[dict] = None

    # "너무 완벽" 페널티 적용 여부
    too_polished_penalty: bool = False

    def to_dict(self) -> dict:
        """JSON 직렬화 가능한 dict로 변환"""
        return {
            # 5개 기준
            "realism": self.realism,
            "person_preservation": self.person_preservation,
            "scenario_fit": self.scenario_fit,
            "skin_condition": self.skin_condition,
            "anti_polish_factor": self.anti_polish_factor,
            # 종합 결과
            "total_score": self.total_score,
            "tier": self.tier.value,
            "grade": self.grade,
            "passed": self.passed,
            "auto_fail": self.auto_fail,
            "auto_fail_reasons": self.auto_fail_reasons,
            "issues": self.issues,
            "summary_kr": self.summary_kr,
            "raw_response": self.raw_response,
            "too_polished_penalty": self.too_polished_penalty,
        }


@dataclass
class SelfieValidationThresholds:
    """셀카/UGC 검증 임계값"""

    # PASS 기준
    pass_total: int = 75
    pass_realism: int = 70
    pass_person_preservation: int = 80

    # 가중치 (총 100%)
    weights: dict = field(
        default_factory=lambda: {
            "realism": 0.35,
            "person_preservation": 0.25,
            "scenario_fit": 0.20,
            "skin_condition": 0.10,
            "anti_polish_factor": 0.10,
        }
    )

    # Auto-fail 임계값
    auto_fail_thresholds: dict = field(
        default_factory=lambda: {
            "realism": 40,  # 너무 AI스러움
            "person_preservation": 50,  # 다른 사람
            "skin_condition": 40,  # 플라스틱 피부
        }
    )

    # "너무 완벽" 페널티 기준
    too_polished_threshold: int = 95  # 모든 점수가 이 이상이면 페널티


# Auto-fail 조건 설명 (한국어)
SELFIE_AUTO_FAIL_DESCRIPTIONS = {
    "finger_anomaly": "손가락 6개 이상 / 기형적 손가락",
    "different_person": "얼굴 다른 사람 (참조와 불일치)",
    "warm_cast": "누런 톤 (golden/amber/warm cast)",
    "plastic_skin": "AI 특유 플라스틱 피부",
    "unwanted_text": "의도하지 않은 텍스트/워터마크",
    "too_polished": "너무 완벽함 (UGC답지 않음)",
}


class SelfieValidator:
    """셀카/UGC 품질 검증기 (5개 기준)"""

    VALIDATION_PROMPT = """## 셀카/UGC 품질 검증 (v1.0 - 5개 기준)

당신은 인플루언서/UGC 스타일 이미지의 품질을 평가하는 전문가입니다.
핵심 원칙: **"너무 잘 나오면 실패"** - 자연스러운 스마트폰 셀카처럼 보여야 합니다.

---

## 1. realism (35%) - 실제 사진인가?

스마트폰으로 찍은 실제 셀카/스냅샷처럼 보이는가?

- 90-100: 진짜 폰카 사진. 인스타 피드에서 봐도 의심 안 함
- 70-89: 대체로 실사. 약간 보정한 것처럼 보임
- 50-69: AI 느낌이 슬쩍 남. 어딘가 이상함
- 0-49: 명백한 AI/CG 렌더링 → AUTO-FAIL

**체크 포인트:**
- 폰카 특유의 약간 뭉개진 디테일
- 완벽하지 않은 조명 (오버/언더 노출 허용)
- 자연스러운 피부 질감
- 스튜디오 조명 느낌 = 감점

---

## 2. person_preservation (25%) - 같은 사람인가?

[FACE REFERENCE]와 [GENERATED IMAGE]가 정확히 같은 사람인가?

- 95-100: 100% 동일인. 모든 특징 완벽 일치
- 85-94: 동일인. 조명/각도로 약간 달라 보일 수 있음
- 70-84: 비슷하지만 확신 불가
- 50-69: 다른 사람. 골격 불일치
- 0-49: 완전히 다른 사람 → AUTO-FAIL

**비교 포인트:**
- 눈 (쌍꺼풀, 눈꼬리 각도, 크기)
- 코 (콧대, 코끝, 콧볼)
- 입 (입술 두께, 인중)
- 턱선/광대

---

## 3. scenario_fit (20%) - 상황이 자연스러운가?

장소/상황/의상이 서로 어울리고 자연스러운가?

- 90-100: 완벽한 조화. 그 장소에서 그 옷 입고 있을 법함
- 70-89: 대체로 어울림. 약간 어색한 부분 있음
- 50-69: 상황 불일치. 헬스장에 정장? 카페에 수영복?
- 0-49: 물리적으로 말이 안 됨

**체크 포인트:**
- 장소와 의상의 조화
- 시간대와 조명의 일치
- 소품/배경의 적합성
- 포즈와 상황의 자연스러움

---

## 4. skin_condition (10%) - 피부가 자연스러운가?

피부 질감이 실제 사람처럼 보이는가?

- 90-100: 완전 자연스러운 피부. 모공, 잔주름, 약간의 결점까지 보임
- 70-89: 대체로 자연스러움. 약간 매끈함
- 50-69: 에어브러시 느낌. 너무 깨끗함
- 0-49: 플라스틱/왁스 인형 피부 → AUTO-FAIL

**경고 신호:**
- 모공 완전 부재
- 균일한 피부 톤
- 밀랍 인형 광택
- 과도한 smoothing

---

## 5. anti_polish_factor (10%) - 너무 완벽하지 않은가?

UGC/셀카는 약간의 "결점"이 오히려 자연스럽습니다.

- 90-100: 자연스러운 불완전함. 머리카락 흐트러짐, 약간의 흔들림, 자연광
- 70-89: 대체로 자연스러움. 너무 계산된 느낌은 없음
- 50-69: 너무 완벽. 스튜디오 촬영 같음
- 0-49: 에디토리얼/매거진 수준 → UGC로 부적합

**"너무 완벽"의 징후:**
- 완벽한 조명
- 완벽한 구도
- 완벽한 피부
- 완벽한 포즈
→ 이러면 UGC가 아니라 화보

---

## AUTO-FAIL 조건 (하나라도 해당 시 즉시 FAIL)

1. 손가락 6개 이상 / 기형적 손가락
2. 얼굴 다른 사람 (참조와 불일치)
3. 누런 톤 (golden/amber/warm cast)
4. AI 특유 플라스틱 피부
5. 의도하지 않은 텍스트/워터마크

---

## RESPONSE FORMAT (JSON only)

```json
{{
  "realism": <0-100>,
  "person_preservation": <0-100>,
  "scenario_fit": <0-100>,
  "skin_condition": <0-100>,
  "anti_polish_factor": <0-100>,
  "auto_fail_detected": [<해당하는 auto-fail 항목들>],
  "issues": ["<문제점1>", "<문제점2>"],
  "summary_kr": "<한국어 1-2문장 요약>"
}}
```"""

    def __init__(
        self,
        client: genai.Client,
        thresholds: Optional[SelfieValidationThresholds] = None,
    ):
        """
        검증기 초기화

        Args:
            client: Gemini API 클라이언트
            thresholds: 선택적 커스텀 임계값 (미지정 시 기본값 사용)
        """
        self.client = client
        self.thresholds = thresholds or SelfieValidationThresholds()

    def validate(
        self,
        generated_img: Union[str, Path, Image.Image],
        face_images: List[Union[str, Path, Image.Image]] = None,
        outfit_images: List[Union[str, Path, Image.Image]] = None,
        scenario_options: Optional[dict] = None,
    ) -> SelfieValidationResult:
        """
        셀카/UGC 이미지 품질 검증

        Args:
            generated_img: 검증할 생성된 이미지 (경로 또는 PIL Image)
            face_images: 참조용 얼굴 이미지들 (경로 또는 PIL Images)
            outfit_images: 참조용 착장 이미지들 (선택적)
            scenario_options: 시나리오 옵션 (장소, 분위기 등)

        Returns:
            SelfieValidationResult: 5개 기준 검증 결과
        """
        # 얼굴 참조 이미지 필수
        if not face_images or len(face_images) == 0:
            raise ValueError(
                "face_images는 필수입니다. person_preservation 평가에 필요합니다."
            )

        # 이미지 로드
        gen_img = self._load_image(generated_img)
        faces = [self._load_image(f) for f in (face_images or [])]
        outfits = [self._load_image(o) for o in (outfit_images or [])]

        # VLM 콘텐츠 구성
        content_parts = [types.Part(text=self.VALIDATION_PROMPT)]

        content_parts.append(types.Part(text="\n\n[GENERATED IMAGE TO EVALUATE]"))
        content_parts.append(self._pil_to_part(gen_img))

        if faces:
            content_parts.append(types.Part(text="\n\n[FACE REFERENCE - 얼굴 비교용]"))
            for face in faces[:3]:  # 최대 3장
                content_parts.append(self._pil_to_part(face))

        if outfits:
            content_parts.append(
                types.Part(text="\n\n[OUTFIT REFERENCE - 착장 참고용 (선택)]")
            )
            for outfit in outfits[:3]:
                content_parts.append(self._pil_to_part(outfit))

        if scenario_options:
            scenario_text = f"\n\n[SCENARIO CONTEXT]\n{json.dumps(scenario_options, ensure_ascii=False)}"
            content_parts.append(types.Part(text=scenario_text))

        # VLM 호출
        try:
            response = self.client.models.generate_content(
                model=VISION_MODEL,
                contents=[types.Content(role="user", parts=content_parts)],
                config=types.GenerateContentConfig(
                    temperature=0.1, response_modalities=["TEXT"]
                ),
            )

            # JSON 파싱
            raw_text = response.candidates[0].content.parts[0].text.strip()
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()

            result_dict = json.loads(raw_text)

        except json.JSONDecodeError as e:
            print(f"[SelfieValidator] JSON 파싱 오류: {e}")
            return self._create_error_result(f"JSON 파싱 오류: {e}")
        except Exception as e:
            print(f"[SelfieValidator] VLM 오류: {e}")
            return self._create_error_result(f"VLM 오류: {e}")

        # 결과 처리
        return self._process_result(result_dict)

    def _process_result(self, result_dict: dict) -> SelfieValidationResult:
        """VLM 응답을 SelfieValidationResult로 변환"""
        # 점수 추출
        realism = result_dict.get("realism", 0)
        person_preservation = result_dict.get("person_preservation", 0)
        scenario_fit = result_dict.get("scenario_fit", 0)
        skin_condition = result_dict.get("skin_condition", 0)
        anti_polish_factor = result_dict.get("anti_polish_factor", 0)

        # "너무 완벽" 페널티 체크
        too_polished_penalty = self._check_too_polished(
            realism,
            person_preservation,
            scenario_fit,
            skin_condition,
            anti_polish_factor,
        )

        # 페널티 적용: anti_polish_factor 감점
        if too_polished_penalty:
            anti_polish_factor = max(0, anti_polish_factor - 30)
            result_dict["anti_polish_factor"] = anti_polish_factor

        # 총점 계산
        total_score = self._calculate_total_score(result_dict)

        # Auto-fail 체크
        auto_fail, auto_fail_reasons = self._check_auto_fail(result_dict)

        # Grade 결정
        grade = self._determine_grade(total_score, auto_fail)

        # Tier 결정
        tier = self._determine_tier(total_score, auto_fail, grade)

        # Pass 여부
        passed = self._check_passed(result_dict, total_score, auto_fail)

        # Issues 추출
        issues = result_dict.get("issues", [])
        if too_polished_penalty:
            issues.append("너무 완벽함 - UGC답지 않음")

        # 요약
        summary_kr = result_dict.get("summary_kr", "")

        return SelfieValidationResult(
            realism=realism,
            person_preservation=person_preservation,
            scenario_fit=scenario_fit,
            skin_condition=skin_condition,
            anti_polish_factor=anti_polish_factor,
            total_score=total_score,
            tier=tier,
            grade=grade,
            passed=passed,
            auto_fail=auto_fail,
            auto_fail_reasons=auto_fail_reasons,
            issues=issues,
            summary_kr=summary_kr,
            raw_response=result_dict,
            too_polished_penalty=too_polished_penalty,
        )

    def _check_too_polished(
        self,
        realism: int,
        person_preservation: int,
        scenario_fit: int,
        skin_condition: int,
        anti_polish_factor: int,
    ) -> bool:
        """
        "너무 완벽" 여부 체크

        모든 점수가 95점 이상이면 → 너무 완벽 = UGC답지 않음 = 페널티
        """
        threshold = self.thresholds.too_polished_threshold
        scores = [
            realism,
            person_preservation,
            scenario_fit,
            skin_condition,
            anti_polish_factor,
        ]

        # 모든 점수가 threshold 이상이면 "너무 완벽"
        if all(s >= threshold for s in scores):
            print(f"[SelfieValidator] 너무 완벽 페널티 발동: 모든 점수 >= {threshold}")
            return True
        return False

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
        return types.Part(
            inline_data=types.Blob(mime_type="image/png", data=buffer.getvalue())
        )

    def _calculate_total_score(self, result: dict) -> int:
        """가중 총점 계산"""
        weights = self.thresholds.weights
        total = 0.0

        for metric, weight in weights.items():
            score = result.get(metric, 0)
            total += score * weight

        return round(total)

    def _check_auto_fail(self, result: dict) -> Tuple[bool, List[str]]:
        """Auto-fail 조건 체크"""
        auto_fail = False
        reasons = []

        # VLM이 감지한 auto-fail 항목
        detected = result.get("auto_fail_detected", [])
        if detected:
            auto_fail = True
            for item in detected:
                desc = SELFIE_AUTO_FAIL_DESCRIPTIONS.get(item, item)
                reasons.append(desc)

        # 점수 기반 auto-fail
        for criterion, threshold in self.thresholds.auto_fail_thresholds.items():
            score = result.get(criterion, 100)
            if score < threshold:
                auto_fail = True
                desc = f"{criterion} 점수 미달 ({score} < {threshold})"
                if desc not in reasons:
                    reasons.append(desc)

        return auto_fail, reasons

    def _determine_grade(self, total_score: int, auto_fail: bool) -> str:
        """Grade 결정 (S/A/B/C/F)"""
        if auto_fail:
            return "F"
        elif total_score >= 95:
            return "S"
        elif total_score >= 90:
            return "A"
        elif total_score >= 85:
            return "B"
        elif total_score >= 75:
            return "C"
        else:
            return "F"

    def _determine_tier(
        self, total_score: int, auto_fail: bool, grade: str
    ) -> SelfieQualityTier:
        """Quality tier 결정"""
        if auto_fail or grade == "F":
            return SelfieQualityTier.REGENERATE
        elif grade in ("S", "A"):
            return SelfieQualityTier.RELEASE_READY
        elif grade == "B":
            return SelfieQualityTier.NEEDS_MINOR_EDIT
        else:  # C
            return SelfieQualityTier.REGENERATE

    def _check_passed(self, result: dict, total_score: int, auto_fail: bool) -> bool:
        """Pass 여부 체크"""
        if auto_fail:
            return False

        t = self.thresholds
        return (
            total_score >= t.pass_total
            and result.get("realism", 0) >= t.pass_realism
            and result.get("person_preservation", 0) >= t.pass_person_preservation
        )

    def _create_error_result(self, error_msg: str) -> SelfieValidationResult:
        """오류 발생 시 REGENERATE 결과 생성"""
        return SelfieValidationResult(
            realism=0,
            person_preservation=0,
            scenario_fit=0,
            skin_condition=0,
            anti_polish_factor=0,
            total_score=0,
            tier=SelfieQualityTier.REGENERATE,
            grade="F",
            passed=False,
            auto_fail=True,
            auto_fail_reasons=[f"검증 오류: {error_msg}"],
            issues=[f"검증 오류: {error_msg}"],
            summary_kr=f"검증 오류: {error_msg}",
        )

    def print_result(self, result: SelfieValidationResult, filename: str = "") -> None:
        """검증 결과 출력"""
        print(f"\n{'='*60}")
        if filename:
            print(f"File: {filename}")
        print(f"{'='*60}")

        # 5개 기준 출력
        criteria = [
            ("realism (35%)", result.realism, 70),
            ("person_preservation (25%)", result.person_preservation, 80),
            ("scenario_fit (20%)", result.scenario_fit, 70),
            ("skin_condition (10%)", result.skin_condition, 70),
            ("anti_polish_factor (10%)", result.anti_polish_factor, 70),
        ]

        print("\n[5개 검증 기준]")
        for name, score, threshold in criteria:
            status = "[O]" if score >= threshold else "[X]"
            print(f"  {name:<28} {score:>3}  {status}")

        # "너무 완벽" 페널티
        if result.too_polished_penalty:
            print(f"\n  [!] 너무 완벽 페널티 적용됨")

        # 총점
        print(f"\n{'='*60}")
        print(
            f"TOTAL: {result.total_score}  |  GRADE: {result.grade}  |  TIER: {result.tier.value}  |  {'PASS' if result.passed else 'FAIL'}"
        )
        print(f"{'='*60}")

        # Auto-fail
        if result.auto_fail:
            print(f"\n[AUTO-FAIL] {', '.join(result.auto_fail_reasons)}")

        # Issues
        if result.issues:
            print(f"\nIssues ({len(result.issues)}):")
            for issue in result.issues[:5]:
                print(f"  - {issue}")

        # 요약
        if result.summary_kr:
            print(f"\n요약: {result.summary_kr}")

    def generate_report(self, results: List[SelfieValidationResult]) -> dict:
        """배치 검증 리포트 생성"""
        if not results:
            return {"error": "결과 없음"}

        total = len(results)

        # Grade 카운트
        grade_counts = {"S": 0, "A": 0, "B": 0, "C": 0, "F": 0}
        tier_counts = {"RELEASE_READY": 0, "NEEDS_MINOR_EDIT": 0, "REGENERATE": 0}

        avg_scores = {
            "total_score": 0,
            "realism": 0,
            "person_preservation": 0,
            "scenario_fit": 0,
            "skin_condition": 0,
            "anti_polish_factor": 0,
        }

        auto_fail_count = 0
        too_polished_count = 0

        for result in results:
            grade_counts[result.grade] += 1
            tier_counts[result.tier.value] += 1

            avg_scores["total_score"] += result.total_score
            avg_scores["realism"] += result.realism
            avg_scores["person_preservation"] += result.person_preservation
            avg_scores["scenario_fit"] += result.scenario_fit
            avg_scores["skin_condition"] += result.skin_condition
            avg_scores["anti_polish_factor"] += result.anti_polish_factor

            if result.auto_fail:
                auto_fail_count += 1
            if result.too_polished_penalty:
                too_polished_count += 1

        # 평균 계산
        for key in avg_scores:
            avg_scores[key] = round(avg_scores[key] / total, 1)

        # Pass rate
        passed_count = sum(1 for r in results if r.passed)
        pass_rate = round(passed_count / total * 100, 1)

        # Usable rate
        usable_count = tier_counts["RELEASE_READY"] + tier_counts["NEEDS_MINOR_EDIT"]
        usable_rate = round(usable_count / total * 100, 1)

        return {
            "summary": {
                "total_images": total,
                "passed": passed_count,
                "pass_rate": pass_rate,
                "usable_rate": usable_rate,
                "auto_fail_count": auto_fail_count,
                "too_polished_count": too_polished_count,
            },
            "grades": grade_counts,
            "tiers": tier_counts,
            "average_scores": avg_scores,
        }

    def print_report(self, report: dict) -> None:
        """배치 검증 리포트 출력"""
        print("\n" + "=" * 60)
        print("SELFIE/UGC VALIDATION REPORT (5 Criteria)")
        print("=" * 60)

        summary = report["summary"]
        print(f"\n[SUMMARY]")
        print(f"  Total Images: {summary['total_images']}")
        print(f"  Passed: {summary['passed']} ({summary['pass_rate']}%)")
        print(f"  Usable Rate: {summary['usable_rate']}%")
        print(f"  Auto-Fail: {summary['auto_fail_count']}")
        print(f"  Too Polished: {summary['too_polished_count']}")

        grades = report["grades"]
        print(f"\n[GRADE DISTRIBUTION]")
        print(
            f"  S: {grades['S']} | A: {grades['A']} | B: {grades['B']} | C: {grades['C']} | F: {grades['F']}"
        )

        tiers = report["tiers"]
        print(f"\n[TIER BREAKDOWN]")
        print(f"  RELEASE_READY: {tiers['RELEASE_READY']}")
        print(f"  NEEDS_MINOR_EDIT: {tiers['NEEDS_MINOR_EDIT']}")
        print(f"  REGENERATE: {tiers['REGENERATE']}")

        avg = report["average_scores"]
        print(f"\n[AVERAGE SCORES]")
        print(f"  Total: {avg['total_score']}")
        print(f"  Realism (35%): {avg['realism']}")
        print(f"  Person Preservation (25%): {avg['person_preservation']}")
        print(f"  Scenario Fit (20%): {avg['scenario_fit']}")
        print(f"  Skin Condition (10%): {avg['skin_condition']}")
        print(f"  Anti-Polish (10%): {avg['anti_polish_factor']}")

        print("\n" + "=" * 60)
