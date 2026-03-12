"""
자동 재생성 파이프라인 - 메인 오케스트레이터
"""

import os
import json
import shutil
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field

from .config import PipelineConfig, BASE_PRESERVATION_PROMPT, DEFAULT_BACKGROUND_PROMPT
from .generator import ImageGenerator
from .validator import QualityValidator
from .studio_relight_validator import StudioRelightValidator
from .diagnoser import IssueDiagnoser
from .enhancer import PromptEnhancer


@dataclass
class PipelineResult:
    """파이프라인 실행 결과"""
    total_count: int = 0
    success_count: int = 0
    retry_success_count: int = 0
    manual_review_count: int = 0
    elapsed_seconds: float = 0
    details: List[Dict[str, Any]] = field(default_factory=list)


class AutoRetryPipeline:
    """자동 재생성 파이프라인"""

    def __init__(self, config: Optional[PipelineConfig] = None, api_keys: Optional[List[str]] = None, source_type: str = "standard"):
        self.config = config or PipelineConfig()
        self.api_keys = api_keys or self._load_api_keys()
        self.source_type = source_type

        self.generator = ImageGenerator(self.config)
        if source_type == "studio":
            self.validator = StudioRelightValidator(self.config)
        else:
            self.validator = QualityValidator(self.config)
        self.diagnoser = IssueDiagnoser(self.config)
        self.enhancer = PromptEnhancer()

        # API 키 로테이션
        self._key_lock = threading.Lock()
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

    def _get_next_api_key(self) -> str:
        """다음 API 키 반환 (로테이션)"""
        with self._key_lock:
            key = self.api_keys[self._key_index % len(self.api_keys)]
            self._key_index += 1
            return key

    def run(
        self,
        input_dir: str,
        output_dir: str,
        background_prompt: str = DEFAULT_BACKGROUND_PROMPT,
        callback: Optional[callable] = None
    ) -> PipelineResult:
        """
        메인 파이프라인 실행

        Args:
            input_dir: 입력 이미지 폴더
            output_dir: 출력 폴더
            background_prompt: 배경 프롬프트
            callback: 진행 콜백 함수 (status, current, total, message)

        Returns:
            PipelineResult
        """
        import time
        start_time = time.time()

        # 출력 폴더 구조 생성
        dirs = self._setup_output_dirs(output_dir)

        # 이미지 파일 목록
        image_files = self._get_image_files(input_dir)
        total_count = len(image_files)

        if callback:
            callback("start", 0, total_count, f"Starting pipeline with {total_count} images")

        result = PipelineResult(total_count=total_count)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 조명 프로필 (Stage 0에서 분석, 재시도에서 사용)
        self._lighting_profile = None

        # ========================================
        # STAGE 0: 포즈-배경 호환성 사전 체크
        # ========================================
        corrected_bg_prompt = self._stage0_pose_analysis(
            input_dir, image_files, background_prompt, callback
        )

        # ========================================
        # STAGE 1: 1차 생성
        # ========================================
        if callback:
            callback("stage1", 0, total_count, "Stage 1: Initial generation")

        base_prompt = BASE_PRESERVATION_PROMPT + "\n\n" + corrected_bg_prompt
        stage1_results = self._stage1_generate(
            input_dir, image_files, dirs["temp"], base_prompt, timestamp, callback
        )

        # ========================================
        # STAGE 2: 품질 검수
        # ========================================
        if callback:
            callback("stage2", 0, len(stage1_results), "Stage 2: Quality validation")

        passed, failed = self._stage2_validate(
            input_dir, stage1_results, callback
        )

        # 통과 항목 release로 이동
        for item in passed:
            src = item["generated_path"]
            dst = os.path.join(dirs["release"], os.path.basename(src))
            shutil.copy2(src, dst)
            result.success_count += 1
            result.details.append({**item, "final_status": "release", "retry_count": 0})

        # ========================================
        # STAGE 3-5: 실패 항목 재처리
        # ========================================
        for retry_num in range(self.config.max_retries):
            if not failed:
                break

            if callback:
                callback("retry", retry_num + 1, self.config.max_retries,
                         f"Retry {retry_num + 1}: Processing {len(failed)} failed items")

            # Stage 3: 진단
            diagnoses = self._stage3_diagnose(input_dir, failed, callback)

            # Stage 4: 프롬프트 보강
            enhanced_prompts = self._stage4_enhance(diagnoses, background_prompt)

            # Stage 5: 재생성
            temperature = self.config.temperature_schedule[min(retry_num, len(self.config.temperature_schedule) - 1)]
            retry_results = self._stage5_retry(
                input_dir, failed, enhanced_prompts, dirs["temp"], timestamp, temperature, retry_num + 1, callback
            )

            # 재검수
            newly_passed, still_failed = self._stage2_validate(input_dir, retry_results, callback)

            # 통과 항목 release로 이동
            for item in newly_passed:
                src = item["generated_path"]
                dst = os.path.join(dirs["release"], os.path.basename(src))
                shutil.copy2(src, dst)
                result.success_count += 1
                result.retry_success_count += 1
                result.details.append({**item, "final_status": "release", "retry_count": retry_num + 1})

            failed = still_failed

        # ========================================
        # STAGE 6: 최종 분류 - 실패 항목 manual_review로
        # ========================================
        for item in failed:
            src = item["generated_path"]
            dst = os.path.join(dirs["manual_review"], os.path.basename(src))
            shutil.copy2(src, dst)

            # 진단 정보 저장
            diag_path = os.path.join(dirs["diagnosis"], f"{item['image_name']}_diagnosis.json")
            with open(diag_path, 'w', encoding='utf-8') as f:
                json.dump(item.get("diagnosis", {}), f, ensure_ascii=False, indent=2)

            result.manual_review_count += 1
            result.details.append({**item, "final_status": "manual_review"})

        # 임시 폴더 정리
        shutil.rmtree(dirs["temp"], ignore_errors=True)

        result.elapsed_seconds = time.time() - start_time

        # 최종 리포트 저장
        self._save_report(dirs["logs"], result, timestamp)

        if callback:
            callback("complete", result.success_count, total_count,
                     f"Complete: {result.success_count}/{total_count} success, {result.manual_review_count} manual review")

        return result

    def _setup_output_dirs(self, output_dir: str) -> Dict[str, str]:
        """출력 폴더 구조 생성"""
        dirs = {
            "release": os.path.join(output_dir, "release"),
            "manual_review": os.path.join(output_dir, "manual_review"),
            "diagnosis": os.path.join(output_dir, "manual_review", "diagnosis"),
            "logs": os.path.join(output_dir, "logs"),
            "temp": os.path.join(output_dir, "_temp"),
        }

        for d in dirs.values():
            os.makedirs(d, exist_ok=True)

        return dirs

    def _get_image_files(self, input_dir: str) -> List[str]:
        """이미지 파일 목록 반환"""
        extensions = {'.jpg', '.jpeg', '.png', '.webp'}
        files = []

        for f in os.listdir(input_dir):
            if os.path.splitext(f)[1].lower() in extensions:
                files.append(f)

        return sorted(files)

    def _stage0_pose_analysis(
        self,
        input_dir: str,
        image_files: List[str],
        background_prompt: str,
        callback: Optional[callable]
    ) -> str:
        """Stage 0: 포즈-배경 호환성 사전 체크 및 소품 스타일 매칭"""
        if not image_files:
            return background_prompt

        # 첫 번째 이미지로 대표 분석 (배치 내 포즈가 유사하다고 가정)
        sample_path = os.path.join(input_dir, image_files[0])

        if callback:
            callback("stage0", 0, 1, "Stage 0: Pose-background compatibility check")

        corrected_prompt = background_prompt

        try:
            # === 기존: 포즈 분석 ===
            analysis = self.diagnoser.analyze_original_only(
                sample_path, self._get_next_api_key()
            )

            if not analysis.get("error"):
                physics_req = analysis.get("physics_requirement", "")
                pose_desc = analysis.get("pose_description", "")

                # 포즈 타입 감지
                pose_lower = (pose_desc + " " + physics_req).lower()
                support_required = any(kw in pose_lower for kw in [
                    "sitting", "seated", "sit on", "leaning", "lean on",
                    "resting on", "crouching", "kneeling"
                ])

                if support_required:
                    # 배경 프롬프트에 지지 구조물이 있는지 확인
                    bg_lower = background_prompt.lower()
                    has_support = any(kw in bg_lower for kw in [
                        "stairs", "staircase", "steps", "bench", "ledge", "curb",
                        "wall", "pillar", "seat", "chair", "railing", "platform",
                        "계단", "벤치", "턱", "난간", "의자"
                    ])

                    if not has_support:
                        # 비호환! 프롬프트 자동 보정
                        if callback:
                            callback("stage0_progress", 0, 1,
                                     f"WARNING: Pose requires support ({physics_req[:60]}...) - auto-correcting")
                        support_injection = self._get_support_injection(pose_lower, physics_req)
                        corrected_prompt = corrected_prompt.rstrip() + "\n\n" + support_injection
                    else:
                        if callback:
                            callback("stage0_progress", 0, 1, "Pose compatible (support structure in background)")
                else:
                    if callback:
                        callback("stage0_progress", 0, 1, "Pose compatible (standing/free pose)")

            # === 신규: 소품 스타일 분석 ===
            if callback:
                callback("stage0_props", 0, 1, "Stage 0: Prop style analysis")

            prop_analysis = self.diagnoser.analyze_props(
                sample_path, self._get_next_api_key(), background_prompt
            )

            if not prop_analysis.get("error") and prop_analysis.get("props_detected"):
                prop_style_prompt = self.enhancer.build_prop_style_prompt(
                    prop_analysis, background_prompt
                )

                if prop_style_prompt:
                    corrected_prompt = corrected_prompt.rstrip() + "\n\n" + prop_style_prompt
                    if callback:
                        props_info = ", ".join(
                            p.get("prop_type", "unknown") for p in prop_analysis.get("props", [])
                        )
                        verdict = prop_analysis.get("style_match_verdict", "unknown")
                        callback("stage0_props_progress", 1, 1,
                                 f"Props detected: [{props_info}] - style verdict: {verdict}")
                else:
                    if callback:
                        callback("stage0_props_progress", 1, 1, "Props style matches background")
            else:
                if callback:
                    callback("stage0_props_progress", 1, 1, "No interactive props detected")

            # === 신규: 조명 사전 분석 ===
            if callback:
                callback("stage0_lighting", 0, 1, "Stage 0: Model lighting analysis")

            lighting_profile = self.diagnoser.analyze_lighting(
                sample_path, self._get_next_api_key()
            )

            if not lighting_profile.get("error"):
                self._lighting_profile = lighting_profile

                # 조명 프로필을 배경 프롬프트에 주입
                lighting_constraint = f"""
=== MODEL LIGHTING PROFILE (ANALYZED FROM ORIGINAL) ===
The model in the original photo has the following lighting:
- Light Direction: {lighting_profile.get('light_direction', 'unknown')}
- Light Type: {lighting_profile.get('light_type', 'unknown')}
- Color Temperature: {lighting_profile.get('color_temperature', 'unknown')}
- Shadows: {lighting_profile.get('shadow_characteristics', 'unknown')}
- Intensity: {lighting_profile.get('intensity', 'unknown')}
- Skin Appearance: {lighting_profile.get('skin_tone_appearance', 'unknown')}

CRITICAL LIGHTING CONSTRAINT:
{lighting_profile.get('background_lighting_recommendation', 'Generate background lighting that matches the model.')}

The background MUST have lighting that matches these characteristics.
DO NOT generate a background with harsh sunlight if the model has soft diffused light.
DO NOT generate a background with cool shadows if the model has warm lighting.
The background lighting must be CONSISTENT with what is already on the model."""

                corrected_prompt = corrected_prompt.rstrip() + "\n\n" + lighting_constraint

                if callback:
                    light_dir = lighting_profile.get('light_direction', 'unknown')
                    light_type = lighting_profile.get('light_type', 'unknown')
                    callback("stage0_lighting_progress", 1, 1,
                             f"Lighting: {light_type} from {light_dir}")
            else:
                if callback:
                    callback("stage0_lighting_progress", 1, 1,
                             f"Lighting analysis skipped: {lighting_profile.get('error', 'unknown')[:50]}")

            return corrected_prompt

        except Exception as e:
            if callback:
                callback("stage0_progress", 1, 1, f"Stage 0 skipped: {str(e)[:50]}")
            return corrected_prompt

    def _get_support_injection(self, pose_lower: str, physics_req: str) -> str:
        """포즈에 맞는 지지 구조물 프롬프트 생성"""
        if "sitting" in pose_lower or "seated" in pose_lower or "sit on" in pose_lower:
            return """CRITICAL PHYSICS CONSTRAINT:
The model is in a SITTING pose. The background MUST include a visible surface to sit on.
Add one of: concrete ledge, low wall, stone bench, steps, curb, platform.
The sitting surface must be at the correct height and position matching the model's seated pose.
The model must NOT appear floating - they must be clearly sitting ON something."""

        elif "leaning" in pose_lower or "lean on" in pose_lower:
            return """CRITICAL PHYSICS CONSTRAINT:
The model is LEANING. The background MUST include a surface to lean against.
Add one of: wall, pillar, column, railing, post.
The leaning surface must be at the correct position matching the model's lean direction.
The model must NOT appear floating - they must be clearly leaning ON something."""

        elif "crouching" in pose_lower or "kneeling" in pose_lower:
            return """CRITICAL PHYSICS CONSTRAINT:
The model is in a LOW pose (crouching/kneeling). The background MUST have a ground surface
that supports this pose. The ground must be clearly visible and the model must appear grounded."""

        else:
            return f"""CRITICAL PHYSICS CONSTRAINT:
{physics_req}
The background MUST physically support the model's pose. The model must NOT appear floating."""

    def _stage1_generate(
        self,
        input_dir: str,
        image_files: List[str],
        temp_dir: str,
        prompt: str,
        timestamp: str,
        callback: Optional[callable]
    ) -> List[Dict[str, Any]]:
        """Stage 1: 1차 생성"""
        results = []
        completed = 0

        def generate_task(image_name: str) -> Dict[str, Any]:
            input_path = os.path.join(input_dir, image_name)
            output_name = f"{os.path.splitext(image_name)[0]}_gen_{timestamp}.png"
            output_path = os.path.join(temp_dir, output_name)

            result = self.generator.generate(
                input_path, prompt, output_path, self._get_next_api_key()
            )

            return {
                "image_name": image_name,
                "original_path": input_path,
                "generated_path": output_path,
                "status": result["status"],
                "error": result.get("error")
            }

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {executor.submit(generate_task, img): img for img in image_files}

            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                completed += 1

                if callback:
                    status = "✓" if result["status"] == "success" else "✗"
                    callback("stage1_progress", completed, len(image_files),
                             f"{status} {result['image_name']}")

        return results

    def _stage2_validate(
        self,
        input_dir: str,
        results: List[Dict[str, Any]],
        callback: Optional[callable]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Stage 2: 품질 검수"""
        passed = []
        failed = []

        for i, item in enumerate(results):
            if item["status"] != "success":
                failed.append(item)
                continue

            validation = self.validator.validate(
                item["original_path"],
                item["generated_path"],
                self._get_next_api_key()
            )

            item["validation"] = validation

            if validation.get("pass", False):
                passed.append(item)
            else:
                failed.append(item)

            if callback:
                status = "PASS" if validation.get("pass") else "FAIL"
                score = validation.get("total", 0)
                callback("stage2_progress", i + 1, len(results),
                         f"{status} ({score:.0f}) {item['image_name']}")

        return passed, failed

    def _stage3_diagnose(
        self,
        input_dir: str,
        failed_items: List[Dict[str, Any]],
        callback: Optional[callable]
    ) -> Dict[str, Dict[str, Any]]:
        """Stage 3: 실패 원인 진단"""
        diagnoses = {}

        for i, item in enumerate(failed_items):
            # 생성 실패 항목은 진단 건너뛰기 (생성된 이미지가 없음)
            if item.get("status") != "success":
                diagnoses[item["image_name"]] = {
                    "scores": {},
                    "issues": [],
                    "error": f"Generation failed: {item.get('error', 'unknown')}"
                }
                if callback:
                    callback("stage3_progress", i + 1, len(failed_items),
                             f"Skipped {item['image_name']} (generation failed)")
                continue

            diagnosis = self.diagnoser.diagnose(
                item["original_path"],
                item["generated_path"],
                self._get_next_api_key()
            )

            diagnoses[item["image_name"]] = diagnosis
            item["diagnosis"] = diagnosis

            if callback:
                issues = ", ".join(diagnosis.get("issues", ["unknown"]))
                callback("stage3_progress", i + 1, len(failed_items),
                         f"Diagnosed {item['image_name']}: {issues}")

        return diagnoses

    def _stage4_enhance(
        self,
        diagnoses: Dict[str, Dict[str, Any]],
        background_prompt: str
    ) -> Dict[str, str]:
        """Stage 4: 프롬프트 보강"""
        enhanced_prompts = {}

        for image_name, diagnosis in diagnoses.items():
            # 소품 스타일 이슈가 있으면 진단에 보강 정보 추가
            if "PROP_STYLE_MISMATCH" in diagnosis.get("issues", []):
                prop_score = diagnosis.get("scores", {}).get("prop_style_consistency", 100)
                diagnosis["prop_description"] = diagnosis.get(
                    "prop_description",
                    "prop/furniture that the model is interacting with"
                )
                diagnosis["background_style"] = background_prompt[:200]
                diagnosis["prop_replacement_instruction"] = (
                    "Replace the prop with one that matches the background style. "
                    "The replacement must serve the SAME physical function (same height, same support). "
                    f"Current prop style score: {prop_score}/100."
                )

            # 조명 프로필 주입 (Stage 0에서 분석한 원본 모델 조명 특성)
            if self._lighting_profile and not self._lighting_profile.get("error"):
                diagnosis["_lighting_profile"] = self._lighting_profile

            enhanced = self.enhancer.build_full_prompt(diagnosis, background_prompt)
            enhanced_prompts[image_name] = enhanced

        return enhanced_prompts

    def _stage5_retry(
        self,
        input_dir: str,
        failed_items: List[Dict[str, Any]],
        enhanced_prompts: Dict[str, str],
        temp_dir: str,
        timestamp: str,
        temperature: float,
        retry_num: int,
        callback: Optional[callable]
    ) -> List[Dict[str, Any]]:
        """Stage 5: 재생성"""
        results = []

        for i, item in enumerate(failed_items):
            image_name = item["image_name"]
            prompt = enhanced_prompts.get(image_name, "")

            output_name = f"{os.path.splitext(image_name)[0]}_retry{retry_num}_{timestamp}.png"
            output_path = os.path.join(temp_dir, output_name)

            result = self.generator.generate(
                item["original_path"],
                prompt,
                output_path,
                self._get_next_api_key(),
                temperature=temperature
            )

            retry_result = {
                "image_name": image_name,
                "original_path": item["original_path"],
                "generated_path": output_path,
                "status": result["status"],
                "error": result.get("error"),
                "diagnosis": item.get("diagnosis"),
                "retry_num": retry_num
            }

            results.append(retry_result)

            if callback:
                status = "✓" if result["status"] == "success" else "✗"
                callback("stage5_progress", i + 1, len(failed_items),
                         f"Retry {retry_num}: {status} {image_name}")

        return results

    def _save_report(self, logs_dir: str, result: PipelineResult, timestamp: str):
        """최종 리포트 저장"""
        report = {
            "timestamp": timestamp,
            "summary": {
                "total": result.total_count,
                "success": result.success_count,
                "first_pass_success": result.success_count - result.retry_success_count,
                "retry_success": result.retry_success_count,
                "manual_review": result.manual_review_count,
                "success_rate": f"{result.success_count / result.total_count * 100:.1f}%" if result.total_count > 0 else "0%",
                "elapsed_seconds": round(result.elapsed_seconds, 1)
            },
            "details": result.details
        }

        report_path = os.path.join(logs_dir, f"pipeline_report_{timestamp}.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
