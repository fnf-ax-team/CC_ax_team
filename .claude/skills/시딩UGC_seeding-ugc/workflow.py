"""
시딩 UGC 6단계 워크플로 오케스트레이터

Pipeline:
  Step 1: 브랜드 라우팅 + 템플릿 로드
  Step 2: AI 시나리오 판정 (로깅)
  Step 3: 프롬프트 조립
  Step 4: 이미지 생성 (병렬)
  Step 5: UGC 리얼리즘 검증
  Step 6: 실패 재시도 + 시딩 가이드 생성

Usage:
    python -m seeding_ugc.workflow "Banillaco 아침 루틴 3장" -r ref.png -o ./output
"""

import io
import os
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any

from google import genai
from google.genai import types
from PIL import Image

from seeding_ugc.scenario_router import ScenarioRouter, RoutingResult
from seeding_ugc.prompt_builder import PromptBuilder
from seeding_ugc.validator import UGCValidator


# ── 생성 태스크 ─────────────────────────────────────────────────
@dataclass
class _GenTask:
    prompt: str
    negative: str
    route: RoutingResult
    index: int


# ── 메인 워크플로 ───────────────────────────────────────────────
class SeedingUGCWorkflow:
    """시딩 UGC 6단계 파이프라인"""

    IMAGE_MODEL = "gemini-3-pro-image-preview"
    DEFAULT_TEMP = 0.35
    RETRY_TEMP_BUMP = 0.10  # 재시도 시 temp 증가폭

    def __init__(
        self,
        api_keys: Optional[List[str]] = None,
        max_retries: int = 2,
        max_workers: int = 4,
    ):
        self.api_keys = api_keys or self._load_api_keys()
        self._key_idx = 0
        self._key_lock = threading.Lock()
        self.max_retries = max_retries
        self.max_workers = max_workers

        # 내부 모듈
        self.router = ScenarioRouter()
        self.builder = PromptBuilder()
        self.validator = UGCValidator()

    # ================================================================
    # Public API
    # ================================================================

    def generate(
        self,
        user_input: str,
        model_images: Optional[List[Image.Image]] = None,
        brand_dna: Optional[Dict] = None,
        extra_vars: Optional[Dict] = None,
        output_dir: str = "./seeding_output",
        callback: Optional[Callable] = None,
    ) -> Dict:
        """
        6단계 파이프라인 실행

        Args:
            user_input: 사용자 자연어 요청
            model_images: 참조 이미지 리스트 (PIL Image)
            brand_dna: 브랜드 DNA JSON
            extra_vars: 추가 변수
            output_dir: 출력 디렉토리
            callback: (stage_name, progress_0_to_1, message)

        Returns:
            결과 dict (images, seeding_guide, quality_scores 등)
        """
        t0 = time.time()
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        # ── Step 1 ──
        self._log("Step 1", "브랜드 라우팅 & 템플릿 로드")
        routes = self.router.route(user_input)
        for r in routes:
            self._log("Route", f"{r.category}/{r.scenario} | cam={r.camera_style} | skin={r.skin_state} | n={r.count}")
        if callback:
            callback("route", 0.05, f"{len(routes)}개 시나리오")

        # ── Step 2 ──
        self._log("Step 2", f"AI 시나리오 확인 → {len(routes)}개")
        if callback:
            callback("scenario", 0.10, "시나리오 확인 완료")

        # ── Step 3 ──
        self._log("Step 3", "프롬프트 조립")
        tasks = self._build_tasks(routes, brand_dna, extra_vars)
        self._log("Prompts", f"{len(tasks)}개 프롬프트 준비")
        if callback:
            callback("prompt", 0.15, f"{len(tasks)}개 프롬프트")

        # ── Step 4 ──
        self._log("Step 4", f"이미지 생성 (workers={self.max_workers})")
        generated = self._generate_batch(tasks, model_images, out, callback)
        ok_gen = [g for g in generated if g.get("path")]
        self._log("Generated", f"{len(ok_gen)}/{len(tasks)} 성공")

        # ── Step 5 ──
        self._log("Step 5", "UGC 리얼리즘 검증")
        ref_path = self._save_reference(model_images, out) if model_images else None
        passed, failed = self._validate_batch(ok_gen, ref_path, callback)
        self._log("Validation", f"Pass={len(passed)} Fail={len(failed)}")

        # ── Step 6 ──
        self._log("Step 6", f"재시도 ({len(failed)}개) & 시딩가이드")
        retry_passed = self._retry_failed(failed, model_images, brand_dna, extra_vars, out, callback)
        guide = self._build_seeding_guide(routes, brand_dna)

        # ── 결과 취합 ──
        all_passed = passed + retry_passed
        elapsed = round(time.time() - t0, 2)

        result = {
            "images": [p["path"] for p in all_passed],
            "seeding_guide": guide,
            "quality_scores": [p["validation"] for p in all_passed],
            "routing": [r.__dict__ for r in routes],
            "total_generated": len(tasks),
            "passed": len(all_passed),
            "failed": len(failed) - len(retry_passed),
            "elapsed_seconds": elapsed,
        }

        # 결과 JSON 저장
        result_path = out / "workflow_result.json"
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        self._log("Done", f"Pass={len(all_passed)} | {elapsed}s | {result_path}")

        if callback:
            callback("done", 1.0, "완료")
        return result

    # ================================================================
    # Step helpers
    # ================================================================

    def _build_tasks(
        self,
        routes: List[RoutingResult],
        brand_dna: Optional[Dict],
        extra_vars: Optional[Dict],
    ) -> List[_GenTask]:
        """Step 3: 라우팅 결과 → 생성 태스크 리스트 (count만큼 복제)"""
        tasks = []
        idx = 0
        for route in routes:
            prompt = self.builder.build(route.__dict__, brand_dna, extra_vars)
            negative = self.builder.build_negative()
            for _ in range(route.count):
                tasks.append(_GenTask(prompt=prompt, negative=negative, route=route, index=idx))
                idx += 1
        return tasks

    def _generate_batch(
        self,
        tasks: List[_GenTask],
        model_images: Optional[List[Image.Image]],
        out: Path,
        callback: Optional[Callable],
    ) -> List[Dict]:
        """Step 4: 병렬 이미지 생성"""
        results: List[Dict] = []
        total = len(tasks)

        # Before/After 페어는 순차 생성 (일관성)
        ba_tasks = [t for t in tasks if t.route.before_after]
        normal_tasks = [t for t in tasks if not t.route.before_after]

        # BA 페어 순차
        for t in ba_tasks:
            r = self._generate_one(t, model_images, out)
            results.append(r)
            self._log("Gen", f"[BA] {t.index}: {'OK' if r.get('path') else 'FAIL'}")

        # 나머지 병렬
        if normal_tasks:
            with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
                fmap = {pool.submit(self._generate_one, t, model_images, out): t for t in normal_tasks}
                done_count = len(ba_tasks)
                for fut in as_completed(fmap):
                    done_count += 1
                    t = fmap[fut]
                    try:
                        r = fut.result()
                        results.append(r)
                        self._log("Gen", f"[{done_count}/{total}] {t.route.scenario}_{t.index}: {'OK' if r.get('path') else 'FAIL'}")
                    except Exception as e:
                        results.append({"path": None, "task": t, "error": str(e)})
                        self._log("Gen", f"[{done_count}/{total}] FAIL: {e}")
                    if callback:
                        callback("generate", 0.15 + 0.45 * done_count / total, f"{done_count}/{total}")

        return results

    def _generate_one(
        self,
        task: _GenTask,
        model_images: Optional[List[Image.Image]],
        out: Path,
        temperature: float = None,
    ) -> Dict:
        """단일 이미지 생성 (재시도 포함)"""
        temp = temperature or self.DEFAULT_TEMP
        api_key = self._next_key()
        client = genai.Client(api_key=api_key)

        # 콘텐츠 파트 구성
        parts = [types.Part.from_text(text=task.prompt)]
        if model_images:
            for img in model_images:
                parts.append(self._pil_to_part(img))

        for attempt in range(3):
            try:
                resp = client.models.generate_content(
                    model=self.IMAGE_MODEL,
                    contents=parts,
                    config=types.GenerateContentConfig(
                        temperature=temp,
                        response_modalities=["IMAGE", "TEXT"],
                        image_config=types.ImageConfig(
                            aspect_ratio="9:16",
                            image_size="2K",
                        ),
                    ),
                )
                fname = f"seeding_{task.route.scenario}_{task.index:03d}.png"
                path = self._save_gen_image(resp, out, fname)
                return {"path": str(path), "task": task, "error": None}

            except Exception as e:
                err = str(e).lower()
                if any(code in err for code in ("429", "503", "overloaded")):
                    wait = (attempt + 1) * 3
                    self._log("Retry", f"API rate limit, wait {wait}s...")
                    time.sleep(wait)
                    client = genai.Client(api_key=self._next_key())
                    continue
                return {"path": None, "task": task, "error": str(e)}

        return {"path": None, "task": task, "error": "max_api_retries_exceeded"}

    def _validate_batch(
        self,
        generated: List[Dict],
        ref_path: Optional[str],
        callback: Optional[Callable],
    ) -> tuple:
        """Step 5: 검증"""
        passed, failed = [], []

        for i, item in enumerate(generated, 1):
            path = item.get("path")
            if not path:
                failed.append(item)
                continue

            task = item["task"]
            try:
                vr = self.validator.validate(
                    path,
                    ref_path or path,  # ref 없으면 self-compare (person_preservation 스킵)
                    self._next_key(),
                    task.route.__dict__,
                )
                item["validation"] = vr

                if vr.get("pass", False):
                    self._log("Val", f"[{i}] PASS total={vr.get('total', 0):.1f}")
                    passed.append(item)
                else:
                    self._log("Val", f"[{i}] FAIL total={vr.get('total', 0):.1f} hints={vr.get('retry_hints', [])}")
                    failed.append(item)

            except Exception as e:
                self._log("Val", f"[{i}] ERROR: {e}")
                item["validation"] = {"pass": False, "retry_hints": ["validation_error"]}
                failed.append(item)

            if callback:
                callback("validate", 0.60 + 0.20 * i / len(generated), f"검증 {i}/{len(generated)}")

        return passed, failed

    def _retry_failed(
        self,
        failed: List[Dict],
        model_images: Optional[List[Image.Image]],
        brand_dna: Optional[Dict],
        extra_vars: Optional[Dict],
        out: Path,
        callback: Optional[Callable],
    ) -> List[Dict]:
        """Step 6: 실패 항목 재시도"""
        retry_passed = []

        for i, item in enumerate(failed, 1):
            if i > self.max_retries * len(failed):
                break

            task: _GenTask = item["task"]
            vr = item.get("validation", {})
            hints = vr.get("retry_hints", [])

            self._log("Retry", f"[{i}/{len(failed)}] {task.route.scenario} hints={len(hints)}")

            # 프롬프트 강화
            enhanced = self._enhance_prompt(task.prompt, hints)
            temp = self.DEFAULT_TEMP + self.RETRY_TEMP_BUMP

            # 새 태스크 생성
            retry_task = _GenTask(
                prompt=enhanced,
                negative=task.negative,
                route=task.route,
                index=task.index + 1000,
            )

            result = self._generate_one(retry_task, model_images, out, temperature=temp)
            if not result.get("path"):
                continue

            # 재검증
            ref_path_str = str(out / "_reference.png") if model_images else result["path"]
            try:
                vr2 = self.validator.validate(
                    result["path"],
                    ref_path_str,
                    self._next_key(),
                    task.route.__dict__,
                )
                result["validation"] = vr2

                if vr2.get("pass", False):
                    self._log("Retry", f"[{i}] PASS after retry total={vr2.get('total', 0):.1f}")
                    retry_passed.append(result)
                else:
                    self._log("Retry", f"[{i}] Still FAIL total={vr2.get('total', 0):.1f}")
            except Exception as e:
                self._log("Retry", f"[{i}] Validate error: {e}")

            if callback:
                callback("retry", 0.80 + 0.15 * i / max(len(failed), 1), f"재시도 {i}/{len(failed)}")

        return retry_passed

    # ================================================================
    # 프롬프트 강화
    # ================================================================

    def _enhance_prompt(self, original: str, hints: List[str]) -> str:
        """검증 힌트 기반 프롬프트 강화"""
        prefix_parts = []
        suffix_parts = []

        for hint in hints:
            h = hint.lower()
            if "raw" in h or "ugc_realism" in h or "phone" in h:
                prefix_parts.append(
                    "ULTRA RAW phone selfie, completely unpolished, authentic smartphone photo, "
                    "imperfect exposure, slight motion blur, casual framing"
                )
            if "anti_polish" in h or "professional" in h or "studio" in h:
                suffix_parts.append(
                    "\nAVOID AT ALL COSTS: professional lighting, perfect composition, "
                    "studio quality, ring light, beauty filter, color grading"
                )
            if "skin_state" in h or "skin" in h:
                prefix_parts.append("VERY VISIBLE skin condition, clearly noticeable texture and imperfections")
            if "person" in h or "face" in h:
                prefix_parts.append(
                    "CRITICAL: preserve EXACT facial features from reference image, "
                    "identical face structure, same person"
                )

        result = original
        if prefix_parts:
            result = ", ".join(prefix_parts) + ",\n" + result
        if suffix_parts:
            result = result + "\n".join(suffix_parts)
        return result

    # ================================================================
    # 시딩 가이드
    # ================================================================

    def _build_seeding_guide(self, routes: List[RoutingResult], brand_dna: Optional[Dict]) -> Dict:
        """시딩 가이드 메모 생성"""
        brand = brand_dna.get("_metadata", {}).get("brand", "") if brand_dna else ""

        # 시나리오별 캡션/해시태그 매핑
        CAPTIONS = {
            "headache_sun": f"진짜 어제 햇빛 너무 세서 두통 왔는데... {brand} 발라야했음",
            "oily_frustration": f"번들거림 미침ㅋㅋ 진짜 {brand}로 유분 잡아야 할 듯",
            "acne_concern": f"트러블 또 났어.. {brand} 진정 효과 있나 써봄",
            "dryness_flaking": f"겨울이라 건조함 미쳤다 {brand} 보습 진짜 좋음",
            "dark_circles": f"수면부족으로 다크서클 심해짐.. {brand} 아이크림 시작",
            "wind_mess": f"바람에 완전 엉망됨ㅋㅋ {brand} 덕분에 피부는 괜찮",
            "before_skincare": f"세안 직후 맨얼굴.. {brand} 루틴 시작!",
            "after_skincare": f"{brand} 루틴 끝! 확실히 촉촉해짐",
            "morning_routine": f"아침 루틴 브이로그 {brand} 빠질 수 없지",
            "workout_post": f"운동 후 땀범벅.. {brand}로 진정 케어",
        }

        HASHTAGS = {
            "pain_point": [f"#{brand}", "#선케어", "#피부고민", "#뷰티꿀팁", "#솔직후기"],
            "before_after": [f"#{brand}", "#전후비교", "#스킨케어루틴", "#피부변화", "#솔직후기"],
            "daily_routine": [f"#{brand}", "#데일리루틴", "#스킨케어", "#브이로그", "#솔직후기"],
        }

        scenarios_guide = []
        for r in routes:
            scenarios_guide.append({
                "scenario": r.scenario,
                "target_platform": "TikTok/Reels/Shorts",
                "suggested_caption": CAPTIONS.get(r.scenario, f"{brand} 솔직 후기"),
                "suggested_hashtags": HASHTAGS.get(r.category, [f"#{brand}", "#뷰티"]),
                "product_placement": "자연스럽게 손에 들거나 옆에 놓인 상태 (의도적으로 보여주지 않기)",
                "content_direction": (
                    "사용 전/후 비교로 효과 강조" if r.before_after
                    else f"{r.scenario} 불편한 상황 → 제품 사용 → 해결 서사"
                ),
            })

        return {"brand": brand, "scenarios": scenarios_guide}

    # ================================================================
    # Utilities
    # ================================================================

    def _next_key(self) -> str:
        with self._key_lock:
            k = self.api_keys[self._key_idx % len(self.api_keys)]
            self._key_idx += 1
            return k

    def _load_api_keys(self) -> List[str]:
        raw = os.getenv("GEMINI_API_KEY", "")
        if not raw:
            env_path = Path(__file__).parent.parent / ".env"
            if env_path.exists():
                with open(env_path, "r") as f:
                    for line in f:
                        if "GEMINI_API_KEY" in line and "=" in line and not line.strip().startswith("#"):
                            raw = line.strip().split("=", 1)[1]
                            break
        if not raw:
            raise ValueError("GEMINI_API_KEY not found in env or .env file")
        return [k.strip() for k in raw.split(",") if k.strip()]

    def _pil_to_part(self, img: Image.Image, max_size: int = 1024) -> types.Part:
        if max(img.size) > max_size:
            img = img.copy()
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return types.Part.from_bytes(data=buf.getvalue(), mime_type="image/png")

    def _save_gen_image(self, response, out: Path, filename: str) -> Path:
        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                path = out / filename
                with open(path, "wb") as f:
                    f.write(part.inline_data.data)
                return path
        raise ValueError("No image data in response")

    def _save_reference(self, model_images: List[Image.Image], out: Path) -> str:
        ref_path = out / "_reference.png"
        model_images[0].save(ref_path)
        return str(ref_path)

    @staticmethod
    def _log(tag: str, msg: str):
        print(f"[{tag}] {msg}")


# ── CLI ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="시딩 UGC 이미지 생성 워크플로")
    parser.add_argument("input", help="요청 텍스트 (예: 'Banillaco 아침 루틴 3장')")
    parser.add_argument("-r", "--reference", help="참조 이미지 경로")
    parser.add_argument("-o", "--output", default="./seeding_output")
    parser.add_argument("--brand-dna", help="Brand DNA JSON 경로")
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--max-workers", type=int, default=4)
    args = parser.parse_args()

    imgs = None
    if args.reference:
        imgs = [Image.open(args.reference).convert("RGB")]
        print(f"[Ref] {args.reference}")

    dna = None
    if args.brand_dna:
        with open(args.brand_dna, "r", encoding="utf-8") as f:
            dna = json.load(f)
        print(f"[DNA] {args.brand_dna}")

    wf = SeedingUGCWorkflow(max_retries=args.max_retries, max_workers=args.max_workers)
    res = wf.generate(args.input, model_images=imgs, brand_dna=dna, output_dir=args.output)
    print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
