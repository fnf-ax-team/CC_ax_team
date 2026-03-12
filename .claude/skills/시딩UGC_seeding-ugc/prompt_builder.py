"""
시딩 UGC 프롬프트 빌더

seeding_ugc.json 템플릿을 로드하고 라우팅 결과를 바탕으로 최종 Gemini 프롬프트를 조립합니다.

주요 기능:
- {input.var|default} 형식 변수 해석
- 시나리오별 prompt_fragment 삽입
- 카메라 스타일별 angle/framing/stability 삽입
- 피부 상태 texture 삽입
- 브랜드 제품 자연 배치
- 네거티브 프롬프트 생성
"""

import json
import re
import os
from pathlib import Path
from typing import Optional, Dict, Any


class PromptBuilder:
    """seeding_ugc.json 기반 프롬프트 조립기"""

    def __init__(self, template_path: Optional[str] = None):
        """
        Args:
            template_path: seeding_ugc.json 경로 (None → 기본 경로)
        """
        if template_path is None:
            project_root = Path(__file__).parent.parent
            template_path = str(
                project_root / ".claude" / "skills" / "prompt-templates" / "seeding_ugc.json"
            )
        self.template_path = Path(template_path)
        self._data = self._load()

    def _load(self) -> dict:
        """JSON 템플릿 로드"""
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template not found: {self.template_path}")
        with open(self.template_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ------------------------------------------------------------------
    # 변수 해석
    # ------------------------------------------------------------------

    def _resolve(self, text: str, ctx: dict) -> str:
        """
        {path.to.key|default} 형식 변수를 ctx에서 조회하여 치환

        Rules:
            - {input.gender|여성} → ctx["input"]["gender"] 또는 "여성"
            - {brand_dna._metadata.brand} → ctx["brand_dna"]["_metadata"]["brand"]
        """
        def _repl(m):
            path, default = m.group(1), m.group(2) or ""
            val = ctx
            for k in path.split("."):
                if isinstance(val, dict) and k in val:
                    val = val[k]
                else:
                    return default
            return str(val) if val is not None else default

        return re.sub(r"\{([^}|]+)(?:\|([^}]*))?\}", _repl, text)

    def _get(self, d: dict, path: str, default: Any = "") -> Any:
        """Nested dict에서 dot path로 값 조회"""
        val = d
        for k in path.split("."):
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    # ------------------------------------------------------------------
    # 프롬프트 빌드
    # ------------------------------------------------------------------

    def build(
        self,
        routing: dict,
        brand_dna: Optional[dict] = None,
        extra_vars: Optional[dict] = None,
    ) -> str:
        """
        최종 프롬프트 조립

        Args:
            routing: RoutingResult.__dict__ 또는 동등한 dict
                     필수 키: category, scenario, camera_style, skin_state
            brand_dna: 브랜드 DNA JSON (선택)
            extra_vars: 추가 템플릿 변수 (선택)

        Returns:
            완성된 프롬프트 문자열
        """
        tpl = self._data.get("template", {})
        scenarios = self._data.get("scenarios", {})
        camera_styles = self._data.get("camera_styles", {})
        skin_states = self._data.get("skin_states", {})

        # 컨텍스트 구성 (변수 해석용)
        ctx = {"input": routing, **(extra_vars or {})}
        if brand_dna:
            ctx["brand_dna"] = brand_dna

        # 시나리오 데이터
        cat = routing.get("category", "daily_routine")
        scn = routing.get("scenario", "morning_routine")
        scn_data = scenarios.get(cat, {}).get(scn, {})

        # 카메라 스타일 데이터
        cam_key = routing.get("camera_style", "selfie_complaint")
        cam_data = camera_styles.get(cam_key, {})

        # 피부 상태 데이터 (리스트의 첫 번째 사용)
        skin_key_list = routing.get("skin_state", ["normal_daily"])
        if isinstance(skin_key_list, str):
            skin_key_list = [skin_key_list]
        skin_textures = []
        for sk in skin_key_list:
            st = skin_states.get(sk, {})
            if st.get("texture"):
                skin_textures.append(st["texture"])
        skin_texture = ", ".join(skin_textures) if skin_textures else "normal daily skin"

        # ── Line-by-line 조립 ──────────────────────────────────────

        lines = []

        # 1) meta: shooting_style, device_profile, still frame
        meta = tpl.get("meta", {})
        lines.append(
            f"{self._resolve(meta.get('shooting_style', ''), ctx)}, "
            f"{self._resolve(meta.get('device_profile', ''), ctx)}, "
            f"still frame from video,"
        )

        # 2) subject: gender, age, expression, skin base, skin_state texture
        subj = tpl.get("subject", {})
        lines.append(
            f"{self._resolve(subj.get('gender', ''), ctx)}, "
            f"{self._resolve(subj.get('age', ''), ctx)}, "
            f"{self._resolve(subj.get('expression', ''), ctx)}, "
            f"{self._resolve(subj.get('skin', ''), ctx)}, "
            f"{skin_texture},"
        )

        # 3) scenario prompt_fragment
        frag = scn_data.get("prompt_fragment", "")
        if frag:
            lines.append(f"{self._resolve(frag, ctx)},")

        # 4) camera_style: angle, framing, stability
        cam_parts = [cam_data.get("angle", ""), cam_data.get("framing", ""), cam_data.get("stability", "")]
        cam_line = ", ".join(p for p in cam_parts if p)
        if cam_line:
            lines.append(f"{self._resolve(cam_line, ctx)},")

        # 5) lighting
        light = tpl.get("lighting", {})
        lines.append(
            f"{self._resolve(light.get('primary', ''), ctx)}, "
            f"{self._resolve(light.get('quality', ''), ctx)},"
        )

        # 6) environment (시나리오 override 우선)
        env_text = scn_data.get("environment", "")
        if not env_text:
            env = tpl.get("environment", {})
            env_text = env.get("location", "") + ", " + env.get("background", "")
        lines.append(f"{self._resolve(env_text, ctx)},")

        # 7) technical overall_feel
        tech = tpl.get("technical", {})
        lines.append(self._resolve(tech.get("overall_feel", ""), ctx))

        # 8) brand injection
        if brand_dna:
            brand_name = self._get(brand_dna, "_metadata.brand", "brand")
            lines.append(f"subtle {brand_name} product visible in scene")

        # ── PHYSICS 블록 ──────────────────────────────────────────
        phys = tpl.get("physics", {})
        pose = tpl.get("pose", {})
        physics_block = "\n\nCRITICAL PHYSICS:"
        physics_block += f"\n- Lens distortion: {self._resolve(phys.get('lens_distortion', ''), ctx)}"
        physics_block += f"\n- Chromatic aberration: {self._resolve(phys.get('chromatic_aberration', ''), ctx)}"
        physics_block += f"\n- Noise: {self._resolve(phys.get('noise', ''), ctx)}"
        physics_block += f"\n- Compression: {self._resolve(phys.get('compression', ''), ctx)}"
        physics_block += f"\n- Framing: {self._resolve(pose.get('framing', ''), ctx)}"
        physics_block += f"\n- Hand Rule: {self._resolve(pose.get('hand_rule', ''), ctx)}"

        # ── NEGATIVE 블록 ─────────────────────────────────────────
        neg = self.build_negative()
        neg_block = f"\n\nNEGATIVE (DO NOT INCLUDE):\n{neg}"

        return "\n".join(lines) + physics_block + neg_block

    def build_negative(self) -> str:
        """네거티브 프롬프트 반환 (쉼표 구분)"""
        items = self._data.get("negative_prompt", [])
        return ", ".join(items)


# ── 테스트 ────────────────────────────────────────────────────────
if __name__ == "__main__":
    builder = PromptBuilder()

    routing = {
        "category": "pain_point",
        "scenario": "headache_sun",
        "camera_style": "selfie_complaint",
        "skin_state": ["sweaty_flushed", "sun_damaged"],
        "gender": "여성",
        "age": "20대 초반",
    }

    brand_dna = {"_metadata": {"brand": "Banillaco"}}
    prompt = builder.build(routing, brand_dna=brand_dna)
    print("=== PROMPT ===")
    print(prompt)
