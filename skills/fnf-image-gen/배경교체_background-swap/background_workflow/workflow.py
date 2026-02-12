"""
배경 생성 워크플로우 - 대화형 컨셉 조율 + 테스트 + 배치 실행
"""

import os
import random
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .concept_generator import ConceptGenerator, ConceptVariation

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from auto_retry_pipeline import AutoRetryPipeline, PipelineConfig
from core.config import OUTPUT_BASE_DIR


@dataclass
class TestResult:
    """테스트 결과"""
    variation: ConceptVariation
    images: List[Dict[str, str]]  # [{original, generated, path}]


@dataclass
class WorkflowState:
    """워크플로우 상태"""
    phase: str = "init"  # init, concept, test, refine, batch, review, complete
    input_dir: Optional[str] = None
    output_dir: Optional[str] = None
    user_concept: Optional[str] = None
    reference_image: Optional[str] = None
    variations: List[ConceptVariation] = field(default_factory=list)
    test_results: List[TestResult] = field(default_factory=list)
    selected_variation: Optional[ConceptVariation] = None
    batch_result: Optional[Any] = None


class BackgroundWorkflow:
    """대화형 배경 생성 워크플로우"""

    def __init__(self, api_keys: Optional[List[str]] = None):
        self.api_keys = api_keys or self._load_api_keys()
        self.state = WorkflowState()
        self._key_index = 0

    def _load_api_keys(self) -> List[str]:
        """API 키 로드"""
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        api_keys = []
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if 'GEMINI_API_KEY' in line and '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        if ',' in value:
                            api_keys.extend([k.strip() for k in value.split(',')])
                        else:
                            api_keys.append(value.strip())
        return api_keys

    def _get_api_key(self) -> str:
        key = self.api_keys[self._key_index % len(self.api_keys)]
        self._key_index += 1
        return key

    # ═══════════════════════════════════════════════════════════════
    # Phase 1: 컨셉 수집
    # ═══════════════════════════════════════════════════════════════

    def start(
        self,
        input_dir: str,
        user_concept: str,
        reference_image: Optional[str] = None,
        output_dir: Optional[str] = None
    ) -> str:
        """워크플로우 시작 - 컨셉 수집"""

        self.state = WorkflowState(
            phase="concept",
            input_dir=input_dir,
            output_dir=output_dir or OUTPUT_BASE_DIR,
            user_concept=user_concept,
            reference_image=reference_image
        )

        # 이미지 개수 확인
        image_count = len(self._get_image_files(input_dir))

        response = f"""'{user_concept}' 배경으로 이해했어요!
{'참조 이미지도 확인했습니다.' if reference_image else ''}

입력 폴더: {image_count}장의 이미지

몇 가지 컨셉 시안으로 테스트해볼까요?
베리에이션 몇 개를 원하세요? (추천: 2~3개)"""

        return response

    # ═══════════════════════════════════════════════════════════════
    # Phase 2: 베리에이션 생성
    # ═══════════════════════════════════════════════════════════════

    def generate_variations(self, count: int = 3) -> Tuple[str, List[ConceptVariation]]:
        """베리에이션 생성"""

        generator = ConceptGenerator(self._get_api_key())
        variations = generator.generate_variations(
            user_concept=self.state.user_concept,
            count=count,
            reference_image_path=self.state.reference_image
        )

        self.state.variations = variations
        self.state.phase = "test"

        # 응답 구성
        response = f"{self.state.user_concept}을(를) {count}가지로 해석해봤어요:\n\n"

        for v in variations:
            response += f"**{v.id}: {v.name}**\n"
            response += f"- {', '.join(v.keywords)}\n"
            response += f"- {v.description}\n\n"

        # 대표 이미지 개수 결정
        rep_count = min(2, len(self._get_image_files(self.state.input_dir)))
        total_test = rep_count * count

        response += f"대표 이미지 {rep_count}장으로 각 컨셉 테스트할게요!\n"
        response += f"({rep_count}장 × {count}컨셉 = {total_test}장 생성)\n\n"
        response += "테스트 시작할까요?"

        return response, variations

    # ═══════════════════════════════════════════════════════════════
    # Phase 3: 테스트 생성
    # ═══════════════════════════════════════════════════════════════

    def run_test(self, representative_count: int = 2) -> Tuple[str, List[TestResult]]:
        """테스트 생성 실행"""

        from auto_retry_pipeline.generator import ImageGenerator
        from auto_retry_pipeline.config import PipelineConfig, BASE_PRESERVATION_PROMPT

        # 대표 이미지 선택
        rep_images = self._select_representative_images(representative_count)

        # 출력 폴더
        test_dir = os.path.join(self.state.output_dir, "_test")
        os.makedirs(test_dir, exist_ok=True)

        config = PipelineConfig()
        generator = ImageGenerator(config)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        test_results = []

        for variation in self.state.variations:
            var_result = TestResult(variation=variation, images=[])

            prompt = BASE_PRESERVATION_PROMPT + "\n\n" + variation.prompt

            for img_name in rep_images:
                input_path = os.path.join(self.state.input_dir, img_name)
                output_name = f"test_{variation.id}_{img_name.split('.')[0]}_{timestamp}.png"
                output_path = os.path.join(test_dir, output_name)

                result = generator.generate(
                    input_path, prompt, output_path, self._get_api_key()
                )

                var_result.images.append({
                    "original": img_name,
                    "generated": output_name,
                    "path": output_path,
                    "status": result["status"]
                })

            test_results.append(var_result)

        self.state.test_results = test_results
        self.state.phase = "refine"

        # 응답 구성
        response = "테스트 결과예요:\n\n"
        for tr in test_results:
            response += f"**{tr.variation.id}: {tr.variation.name}**\n"
            success = sum(1 for img in tr.images if img["status"] == "success")
            response += f"({success}/{len(tr.images)} 생성 성공)\n"
            for img in tr.images:
                if img["status"] == "success":
                    response += f"- {img['path']}\n"
            response += "\n"

        response += "어떤 버전이 마음에 드세요?\n"
        response += "수정이 필요하면 말씀해주세요. (예: 'V2가 좋은데 좀 더 어둡게')"

        return response, test_results

    # ═══════════════════════════════════════════════════════════════
    # Phase 4: 피드백 반영
    # ═══════════════════════════════════════════════════════════════

    def refine(self, selected_id: str, feedback: Optional[str] = None) -> Tuple[str, Optional[TestResult]]:
        """선택된 버전 수정 (피드백이 있으면)"""

        # 선택된 버전 찾기
        selected = None
        for v in self.state.variations:
            if v.id.upper() == selected_id.upper():
                selected = v
                break

        if not selected:
            return f"'{selected_id}' 버전을 찾을 수 없어요. 다시 선택해주세요.", None

        # 피드백이 있으면 수정
        if feedback:
            generator = ConceptGenerator(self._get_api_key())
            refined = generator.refine_concept(selected, feedback)

            # 수정된 버전으로 재테스트
            response = f"{selected_id} 베이스로 '{feedback}' 반영해서 다시 테스트할게요!\n\n"

            # 재테스트 실행
            from auto_retry_pipeline.generator import ImageGenerator
            from auto_retry_pipeline.config import PipelineConfig, BASE_PRESERVATION_PROMPT

            rep_images = self._select_representative_images(2)
            test_dir = os.path.join(self.state.output_dir, "_test")
            os.makedirs(test_dir, exist_ok=True)

            config = PipelineConfig()
            gen = ImageGenerator(config)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            prompt = BASE_PRESERVATION_PROMPT + "\n\n" + refined.prompt

            refined_result = TestResult(variation=refined, images=[])

            for img_name in rep_images:
                input_path = os.path.join(self.state.input_dir, img_name)
                output_name = f"test_{refined.id}_{img_name.split('.')[0]}_{timestamp}.png"
                output_path = os.path.join(test_dir, output_name)

                result = gen.generate(input_path, prompt, output_path, self._get_api_key())

                refined_result.images.append({
                    "original": img_name,
                    "generated": output_name,
                    "path": output_path,
                    "status": result["status"]
                })

            self.state.selected_variation = refined
            self.state.test_results.append(refined_result)

            response += f"**{refined.id}: {refined.name}**\n"
            for img in refined_result.images:
                if img["status"] == "success":
                    response += f"- {img['path']}\n"
            response += "\n이 느낌 어때요?"

            return response, refined_result

        else:
            # 피드백 없이 선택만
            self.state.selected_variation = selected
            self.state.phase = "batch"

            response = f"**{selected.id}: {selected.name}** 선택!\n\n"
            response += f"이 컨셉으로 전체 폴더 실행할까요?\n"
            response += f"총 {len(self._get_image_files(self.state.input_dir))}장 예상"

            return response, None

    # ═══════════════════════════════════════════════════════════════
    # Phase 5: 전체 배치 실행
    # ═══════════════════════════════════════════════════════════════

    def confirm_and_run_batch(self) -> str:
        """확정된 컨셉으로 전체 배치 실행"""

        if not self.state.selected_variation:
            return "먼저 컨셉을 선택해주세요."

        self.state.phase = "batch"

        image_count = len(self._get_image_files(self.state.input_dir))

        return f"""확정! **{self.state.selected_variation.name}**으로 전체 폴더 실행할게요.

총 {image_count}장, 예상 소요시간: ~{image_count * 5}초

진행할까요?"""

    def run_batch(self, callback=None) -> Tuple[str, Any]:
        """배치 실행"""

        pipeline = AutoRetryPipeline()

        result = pipeline.run(
            input_dir=self.state.input_dir,
            output_dir=self.state.output_dir,
            background_prompt=self.state.selected_variation.prompt,
            callback=callback
        )

        self.state.batch_result = result
        self.state.phase = "review" if result.manual_review_count > 0 else "complete"

        # 응답 구성
        response = f"""완료!

**결과 요약:**
- 성공: {result.success_count}/{result.total_count} ({result.success_count/result.total_count*100:.0f}%)
- 1차 통과: {result.success_count - result.retry_success_count}장
- 재시도 성공: {result.retry_success_count}장
- 수동 검토: {result.manual_review_count}장
- 소요 시간: {result.elapsed_seconds:.0f}초

**출력 폴더:**
- release/: 완성본
- manual_review/: 수동 검토 필요"""

        if result.manual_review_count > 0:
            response += f"\n\n수동 검토 항목 {result.manual_review_count}개가 있어요. 확인할까요?"

        return response, result

    # ═══════════════════════════════════════════════════════════════
    # Phase 6: 수동 검토
    # ═══════════════════════════════════════════════════════════════

    def get_manual_review_items(self) -> Tuple[str, List[Dict]]:
        """수동 검토 항목 조회"""

        if not self.state.batch_result:
            return "배치 실행 결과가 없어요.", []

        manual_items = [
            d for d in self.state.batch_result.details
            if d.get("final_status") == "manual_review"
        ]

        response = f"수동 검토 항목 {len(manual_items)}개:\n\n"

        for i, item in enumerate(manual_items, 1):
            diagnosis = item.get("diagnosis", {})
            issues = diagnosis.get("issues", ["unknown"])

            response += f"**{i}. {item['image_name']}**\n"
            response += f"   진단: {', '.join(issues)}\n"
            response += f"   경로: {item.get('generated_path', 'N/A')}\n\n"

        response += "각 항목에 대해:\n"
        response += "- '1번 다시 시도' - 추가 지시와 함께 재생성\n"
        response += "- '1번 스킵' - 제외\n"
        response += "- '전체 스킵' - 수동 검토 종료"

        return response, manual_items

    # ═══════════════════════════════════════════════════════════════
    # 유틸리티
    # ═══════════════════════════════════════════════════════════════

    def _get_image_files(self, directory: str) -> List[str]:
        """이미지 파일 목록"""
        extensions = {'.jpg', '.jpeg', '.png', '.webp'}
        return sorted([
            f for f in os.listdir(directory)
            if os.path.splitext(f)[1].lower() in extensions
        ])

    def _select_representative_images(self, count: int) -> List[str]:
        """대표 이미지 선택 (다양성 고려)"""
        all_images = self._get_image_files(self.state.input_dir)

        if len(all_images) <= count:
            return all_images

        # 간단히 균등 분포로 선택
        step = len(all_images) // count
        selected = [all_images[i * step] for i in range(count)]

        return selected

    def get_state(self) -> Dict[str, Any]:
        """현재 상태 반환"""
        return {
            "phase": self.state.phase,
            "input_dir": self.state.input_dir,
            "user_concept": self.state.user_concept,
            "variations_count": len(self.state.variations),
            "selected": self.state.selected_variation.name if self.state.selected_variation else None
        }
