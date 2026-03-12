"""
FNF Studio - 인물 이미지 생성 워크플로
brand-dna + prompt-template 기반 경량 파이프라인

사용법:
    workflow = ImageGenerationWorkflow()
    images = workflow.generate(
        brand="MLB",
        style="editorial",
        count=5,
        model_images=[pil1, pil2],
        outfit_images=[pil3, pil4]
    )
"""

import os
import json
import time
from pathlib import Path
from io import BytesIO
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# PIL, torch는 런타임에서 import
try:
    from PIL import Image
    import torch
    import numpy as np
except ImportError:
    Image = None
    torch = None
    np = None

# Google GenAI
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None


class ImageGenerationWorkflow:
    """
    인물 이미지 생성 워크플로

    특징:
    - API 호출 최소화 (이미지 생성만)
    - 정적 JSON 데이터 사용 (brand-dna, prompt-template)
    - 병렬 처리 지원
    - API 키 로테이션 (실패시 다음 키 시도)
    """

    # 경로 설정
    SKILLS_DIR = Path(__file__).parent.parent
    BRAND_DNA_DIR = SKILLS_DIR / "brand-dna"
    TEMPLATE_DIR = SKILLS_DIR / "prompt-templates"

    # 브랜드 인덱스 캐시
    _brand_index: Optional[Dict] = None
    _brand_cache: Dict[str, Dict] = {}
    _template_cache: Dict[str, Dict] = {}

    def __init__(self, api_keys: List[str] = None):
        """
        Args:
            api_keys: Gemini API 키 리스트 (없으면 환경변수에서 로드)
        """
        # API 키 리스트 로드
        if api_keys:
            self.api_keys = api_keys if isinstance(api_keys, list) else [api_keys]
        else:
            env_keys = os.environ.get("GEMINI_API_KEY", "")
            self.api_keys = [k.strip() for k in env_keys.split(",") if k.strip()]

        self.current_key_index = 0
        self.client = None
        print(f"[Workflow] API 키 {len(self.api_keys)}개 로드됨")

    def _get_client(self, force_new: bool = False):
        """Gemini 클라이언트 (키 로테이션 지원)"""
        if not self.api_keys:
            return None

        if self.client is None or force_new:
            api_key = self.api_keys[self.current_key_index]
            if genai:
                self.client = genai.Client(api_key=api_key)
                print(f"[Workflow] API 키 #{self.current_key_index + 1} 사용")
        return self.client

    def _rotate_api_key(self):
        """다음 API 키로 전환"""
        if len(self.api_keys) > 1:
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            self.client = None  # 클라이언트 리셋
            print(f"[Workflow] API 키 로테이션 → #{self.current_key_index + 1}")
            return True
        return False

    # ═══════════════════════════════════════════════════════════════
    # [1] 브랜드/스타일 라우팅 (간소화 - _index.json 불필요)
    # ═══════════════════════════════════════════════════════════════

    def route_brand(self, user_input: str) -> Optional[str]:
        """
        사용자 입력에서 브랜드 매칭 (직접 키워드 매칭)

        _index.json 없이 직접 라우팅
        """
        if not user_input:
            return None

        user_lower = user_input.lower()

        # MLB (marketing vs graphic 구분)
        if "mlb" in user_lower:
            # 그래픽 시그널
            if any(k in user_lower for k in ["스트릿", "그래픽", "바시티", "스케이트", "올드스쿨"]):
                return "mlb-graphic"
            # 마케팅 (기본값)
            return "mlb-marketing"

        # Discovery
        if any(k in user_lower for k in ["discovery", "디스커버리", "아웃도어", "고프코어"]):
            return "discovery"

        # Duvetica
        if any(k in user_lower for k in ["duvetica", "듀베티카", "다운", "이탈리안"]):
            return "duvetica"

        # Sergio Tacchini
        if any(k in user_lower for k in ["sergio", "tacchini", "세르지오", "타키니", "테니스", "레트로"]):
            return "sergio-tacchini"

        # Banillaco
        if any(k in user_lower for k in ["banila", "banillaco", "바닐라코", "뷰티", "색조"]):
            return "banillaco"

        return None

    def route_style(self, user_input: str) -> str:
        """
        사용자 입력에서 스타일 매칭 (직접 키워드 매칭)

        Returns: "editorial" 또는 "selfie"
        """
        if not user_input:
            return "editorial"

        user_lower = user_input.lower()

        # 셀피 시그널
        if any(k in user_lower for k in ["셀피", "셀카", "거울", "폰카", "sns", "일상", "캐주얼"]):
            return "selfie"

        # 기본값: editorial
        return "editorial"

    # ═══════════════════════════════════════════════════════════════
    # [2] 정적 데이터 로드
    # ═══════════════════════════════════════════════════════════════

    def load_brand_dna(self, brand_key: str) -> Dict:
        """브랜드 DNA 로드 (캐싱)"""
        if brand_key in self._brand_cache:
            return self._brand_cache[brand_key]

        dna_path = self.BRAND_DNA_DIR / f"{brand_key}.json"
        if dna_path.exists():
            with open(dna_path, 'r', encoding='utf-8') as f:
                dna = json.load(f)
                self._brand_cache[brand_key] = dna
                return dna

        return {}

    def load_template(self, style: str, brand: str = None) -> Dict:
        """
        프롬프트 템플릿 로드 (캐싱)

        우선순위:
        1. {BRAND}_{style}.json (예: MLB_editorial.json)
        2. {style}.json (예: editorial.json) - fallback
        """
        # 브랜드별 템플릿 키
        brand_key = f"{brand}_{style}" if brand else style

        if brand_key in self._template_cache:
            return self._template_cache[brand_key]

        # 1. 브랜드별 템플릿 먼저 시도 (MLB_editorial.json)
        if brand:
            # 브랜드명 추출 (mlb-marketing → MLB)
            brand_name = brand.split("-")[0].upper()
            brand_template_path = self.TEMPLATE_DIR / f"{brand_name}_{style}.json"
            if brand_template_path.exists():
                with open(brand_template_path, 'r', encoding='utf-8') as f:
                    template = json.load(f)
                    self._template_cache[brand_key] = template
                    print(f"[Workflow] 브랜드별 템플릿 로드: {brand_template_path.name}")
                    return template

        # 2. 기본 템플릿 (editorial.json)
        template_path = self.TEMPLATE_DIR / f"{style}.json"
        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                template = json.load(f)
                self._template_cache[style] = template
                print(f"[Workflow] 기본 템플릿 로드: {template_path.name}")
                return template

        return {}

    def load_brand_director_skill(self, brand_key: str) -> Optional[str]:
        """브랜드 디렉터 SKILL.md 로드"""
        # 브랜드 키 → 스킬 폴더 매핑
        skill_mapping = {
            "mlb-marketing": "(MLB마케팅)_시티미니멀_tyrone-lebon",
            "mlb-graphic": "(MLB그래픽)_뉴욕스트릿_shawn-stussy",
            "discovery": "(디스커버리)_어반아웃도어_yosuke-aizawa",
            "duvetica": "(듀베티카)_이탈리안프리미엄_brunello-cucinelli",
            "sergio-tacchini": "(세르지오타키니)_레트로테니스_hedi-slimane",
            "banillaco": "(바닐라코)_K뷰티내추럴_ahn-joo-young",
        }

        skill_folder = skill_mapping.get(brand_key)
        if not skill_folder:
            return None

        skill_path = self.SKILLS_DIR / skill_folder / "SKILL.md"
        if skill_path.exists():
            with open(skill_path, 'r', encoding='utf-8') as f:
                return f.read()

        return None

    def parse_director_skill(self, skill_content: str) -> Dict:
        """
        브랜드 디렉터 SKILL.md에서 포토 디렉팅 지침 추출

        SKILL.md 구조:
        - 스타일 (라인 42-52): "- old money meets streetwear" 형태
        - 세팅 (라인 54-64): "- minimalist concrete mansion" 형태
        - 분위기 (라인 66-76): "- arrogant and nonchalant" 형태
        - 포즈/행동 (라인 78-88): "- leaning arrogantly against walls" 형태
        - DO (라인 92-100): "Pose: 완벽한 배경에..." 형태
        - DON'T (라인 102-106): "Background: 그래피티..." 형태
        """
        import re

        result = {
            "persona": "",
            "philosophy": [],
            "style_keywords": [],
            "setting_keywords": [],
            "mood_keywords": [],
            "pose_guidelines": [],
            "do_rules": [],
            "dont_rules": []
        }

        if not skill_content:
            return result

        lines = skill_content.split('\n')
        current_section = None

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # DO/DON'T 섹션 감지 먼저 (MLB 브랜드 DNA 다음에 나옴)
            if "DO " in line_stripped and "애티튜드" in line_stripped:
                current_section = "do"
                continue
            elif "DON'T" in line_stripped and "금지" in line_stripped:
                current_section = "dont"
                continue
            # 다른 섹션 감지
            elif line_stripped == "스타일":
                current_section = "style"
                continue
            elif "세팅" in line_stripped:
                current_section = "setting"
                continue
            elif line_stripped == "분위기":
                current_section = "mood"
                continue
            elif "포즈" in line_stripped and "행동" in line_stripped:
                current_section = "pose"
                continue
            elif line_stripped.startswith("트리거"):
                current_section = None  # 트리거 키워드 이후는 리셋

            # - 로 시작하는 키워드 추출
            if line_stripped.startswith("- "):
                keyword = line_stripped[2:].strip()
                if current_section == "style":
                    result["style_keywords"].append(keyword)
                elif current_section == "setting":
                    result["setting_keywords"].append(keyword)
                elif current_section == "mood":
                    result["mood_keywords"].append(keyword)
                elif current_section == "pose":
                    result["pose_guidelines"].append(keyword)

            # DO 룰 추출 (Pose:, Expression:, Interaction:, Styling: 형태)
            if current_section == "do":
                for prefix in ["Pose:", "Expression:", "Interaction:", "Styling:"]:
                    if line_stripped.startswith(prefix):
                        rule = line_stripped[len(prefix):].strip()
                        result["do_rules"].append(f"{prefix} {rule}")

            # DON'T 룰 추출 (Background:, Vibe: 형태)
            if current_section == "dont":
                for prefix in ["Background:", "Vibe:"]:
                    if line_stripped.startswith(prefix):
                        rule = line_stripped[len(prefix):].strip()
                        result["dont_rules"].append(f"{prefix} {rule}")

            # 철학 문장 추출 ("로 시작)
            if line_stripped.startswith('"') and line_stripped.endswith('"'):
                result["philosophy"].append(line_stripped.strip('"'))

        # 페르소나 이름 추출
        persona_match = re.search(r'([A-Za-z\s]+)\s*\(([^)]+)\)', skill_content[:500])
        if persona_match:
            result["persona"] = f"{persona_match.group(1).strip()} ({persona_match.group(2)})"

        return result

    # ═══════════════════════════════════════════════════════════════
    # [3] 착장 분석
    # ═══════════════════════════════════════════════════════════════

    def analyze_outfit(self, outfit_images: List) -> Dict:
        """
        착장 이미지 분석 (착장분석_clothing-analysis 스킬 기반)

        Returns:
            {
                "garments": [...],
                "outfit_description": "...",
                "key_features": [...]
            }
        """
        client = self._get_client()
        if client is None or not outfit_images:
            return {"garments": [], "outfit_description": "", "key_features": []}

        # ═══════════════════════════════════════════════════════════════
        # 간소화된 착장 분석 프롬프트 (응답 길이 제한)
        # ═══════════════════════════════════════════════════════════════
        analysis_prompt = """패션 아이템 분석. 이미지 생성에 필요한 핵심 정보만 간결하게 추출하세요.

## 출력 형식 (JSON):
```json
{
  "garments": [
    {
      "category": "headwear/outer/top/bottom/bag/shoes",
      "type": "beanie/cap/jacket/hoodie/t_shirt/jeans 등",
      "fit": "oversized/regular/slim/balloon/straight",
      "key_details": "핵심 구조 3-5개 (예: no_brim, ribbed, drop_shoulder)",
      "logo": "브랜드명 + 위치 (예: MLB front_right) 또는 null",
      "material": "주요 소재 (예: wool, nylon, denim)"
    }
  ],
  "outfit_summary": "전체 착장 한 문장 요약 (30단어 이내)"
}
```

## 규칙:
1. 각 아이템 1줄로 핵심만 (key_details는 콤마로 구분)
2. 색상 제외, 구조/핏/소재만
3. 로고 위치는 front_left/front_right/front_center 등 정확히
4. 비니도 챙 유무 체크 (no_brim 또는 has_brim)
5. JSON만 출력, 설명 없이"""

        parts = [types.Part(text=analysis_prompt)]
        for img in outfit_images:
            part = self.pil_to_part(img)
            if part:
                parts.append(part)

        # 재시도 로직 추가 (최대 3회)
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"[Workflow] 착장 분석 재시도 {attempt + 1}/{max_retries}...")
                    import time
                    time.sleep(1)  # 재시도 전 1초 대기

                response = client.models.generate_content(
                    model="gemini-2.0-flash-exp",  # 분석용은 Flash
                    contents=[types.Content(role="user", parts=parts)],
                    config=types.GenerateContentConfig(temperature=0.3, max_output_tokens=1500)  # 간소화된 응답
                )

                # JSON 파싱 (repair 로직 포함)
                text = response.text
                import re
                json_match = re.search(r'\{[\s\S]*\}', text)
                if json_match:
                    json_str = json_match.group()

                    # JSON repair 시도
                    try:
                        analysis_result = json.loads(json_str)
                    except json.JSONDecodeError:
                        # 일반적인 JSON 오류 수정 시도
                        # 1. trailing comma 제거
                        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
                        # 2. 따옴표 안의 개행 제거
                        json_str = re.sub(r'(?<!\\)\n', ' ', json_str)
                        # 3. 잘린 문자열 닫기
                        if json_str.count('"') % 2 == 1:
                            json_str += '"'
                        # 4. 닫히지 않은 괄호 닫기
                        open_braces = json_str.count('{') - json_str.count('}')
                        open_brackets = json_str.count('[') - json_str.count(']')
                        json_str += ']' * open_brackets + '}' * open_braces

                        try:
                            analysis_result = json.loads(json_str)
                            print(f"[Workflow] JSON repair 성공")
                        except json.JSONDecodeError as e2:
                            print(f"[Workflow] JSON repair 실패: {e2}")
                            raise

                    # ═══════════════════════════════════════════════════════════════
                    # 간소화된 JSON 구조 파싱 (새로운 형식)
                    # ═══════════════════════════════════════════════════════════════
                    garments = analysis_result.get("garments", [])
                    outfit_parts = []
                    key_features_list = []

                    for garment in garments:
                        # 새로운 간소화된 구조: type, fit, key_details, logo, material
                        item_type = garment.get("type", "")
                        fit = garment.get("fit", "")
                        key_details = garment.get("key_details", "")
                        logo = garment.get("logo", "")
                        material = garment.get("material", "")

                        # 아이템 설명 생성
                        desc_parts = []
                        if fit:
                            desc_parts.append(fit)
                        if item_type:
                            desc_parts.append(item_type)
                        if material:
                            desc_parts.append(f"({material})")
                        if key_details:
                            desc_parts.append(f"[{key_details}]")
                        if logo and logo != "null":
                            desc_parts.append(f"with {logo}")

                        if desc_parts:
                            outfit_parts.append(" ".join(desc_parts))

                        # key_features 추출
                        if logo and logo != "null":
                            key_features_list.append(logo)
                        if key_details:
                            key_features_list.extend([d.strip() for d in key_details.split(",")])

                    # outfit_summary 사용 또는 생성
                    outfit_summary = analysis_result.get("outfit_summary", "")
                    analysis_result["outfit_description"] = outfit_summary or ", ".join(outfit_parts)
                    analysis_result["key_features"] = key_features_list

                    # 성공 - garments가 비어있지 않으면 반환
                    if analysis_result.get("garments"):
                        return analysis_result
                    else:
                        print(f"[Workflow] 착장 분석 결과 비어있음, 재시도 시도...")
                        last_error = "Empty garments result"
                        continue

            except Exception as e:
                last_error = str(e)
                print(f"[Workflow] 착장 분석 시도 {attempt + 1} 실패: {e}")
                continue  # 다음 재시도

        # 모든 재시도 실패
        print(f"[Workflow] 착장 분석 최종 실패 (모든 재시도 소진): {last_error}")
        return {"garments": [], "outfit_description": "", "key_features": []}

    def build_outfit_for_template(self, outfit_analysis: Dict) -> Dict:
        """
        착장 분석 결과를 템플릿 outfit 섹션 형태로 변환
        structural_details에서 image_gen_description 생성

        Returns:
            {
                "items": "black cargo jeans with NY logo on front_right, black tank top with MLB logo, ...",
                "style": "styling notes",
                "brand_aesthetic": "MLB aesthetic"
            }
        """
        # ═══════════════════════════════════════════════════════════════
        # 간소화된 JSON 구조 지원
        # ═══════════════════════════════════════════════════════════════
        descriptions = []
        for garment in outfit_analysis.get("garments", []):
            # 새로운 간소화된 구조: type, fit, key_details, logo, material
            item_type = garment.get("type", "")
            fit = garment.get("fit", "")
            key_details = garment.get("key_details", "")
            logo = garment.get("logo", "")
            material = garment.get("material", "")

            # 아이템 설명 생성
            desc_parts = []
            if fit:
                desc_parts.append(fit)
            if item_type:
                desc_parts.append(item_type)
            if material:
                desc_parts.append(f"({material})")
            if key_details:
                desc_parts.append(f"- {key_details}")
            if logo and logo != "null":
                desc_parts.append(f"with {logo}")

            if desc_parts:
                descriptions.append(" ".join(desc_parts))

        # outfit_summary가 있으면 우선 사용
        outfit_summary = outfit_analysis.get("outfit_summary", "")

        return {
            "items": outfit_summary or ", ".join(descriptions),
            "style": outfit_analysis.get("styling_notes", ""),
            "brand_aesthetic": "MLB aesthetic"
        }

    # ═══════════════════════════════════════════════════════════════
    # [3.5] 브랜드 디렉터 포토 디렉팅 (페르소나 기반)
    # ═══════════════════════════════════════════════════════════════

    def generate_director_vision(
        self,
        outfit_images: List,
        outfit_analysis: Dict,
        director_directives: Dict,
        input_vars: Dict = None,
        user_request: str = "",
        variation_index: int = 0,
        style: str = "editorial"
    ) -> Dict:
        """
        브랜드 디렉터 페르소나가 착장을 보고 직접 포토 디렉팅

        Args:
            outfit_images: 착장 이미지 리스트
            outfit_analysis: 착장 분석 결과
            director_directives: parse_director_skill() 결과
            input_vars: 사용자 입력 (gender, age 등)
            user_request: 사용자의 원본 요청 (배경 등)
            variation_index: 연출 번호 (0~4) - 각각 다른 포즈/앵글 강제

        Returns:
            {
                "director_name": "Tyrone Lebon",
                "concept": "촬영 컨셉",
                "location": "구체적인 로케이션",
                "pose": "구체적인 포즈 디렉션",
                "expression": "표정/시선 디렉션",
                "outfit_highlight": "착장 포인트 강조법",
                "mood": "전체 무드",
                "camera": "카메라 앵글/구도",
                "full_direction": "전체 디렉팅 (자연어)"
            }
        """
        client = self._get_client()
        if client is None:
            return {"full_direction": "", "error": "No API client"}

        input_vars = input_vars or {}
        persona = director_directives.get("persona", "Photo Director")
        philosophy = director_directives.get("philosophy", [])
        style_keywords = director_directives.get("style_keywords", [])
        setting_keywords = director_directives.get("setting_keywords", [])
        mood_keywords = director_directives.get("mood_keywords", [])
        pose_guidelines = director_directives.get("pose_guidelines", [])
        do_rules = director_directives.get("do_rules", [])
        dont_rules = director_directives.get("dont_rules", [])

        outfit_desc = outfit_analysis.get("outfit_description", "")
        key_features = outfit_analysis.get("key_features", [])

        gender = input_vars.get("gender", "여성")
        age = input_vars.get("age", "20대 중반")

        # ═══════════════════════════════════════════════════════════════
        # 스타일별 포즈 라이브러리
        # ═══════════════════════════════════════════════════════════════

        # [EDITORIAL] 화보용 포즈 라이브러리 (10개 - SUV 상호작용, 다양한 구도)
        EDITORIAL_POSE_VARIATIONS = [
            {
                "pose": "The Foot Rest (발 올리기)",
                "pose_detail": "차 옆에 서서 한쪽 발을 SUV 범퍼/휠 위에 거침없이 올리기. 팔꿈치로 무릎 짚고 카메라 내려다보기.",
                "expression": "오만하게 카메라 내려다보기, 턱 살짝 들고",
                "angle": "극단적 로우앵글 - 카메라맨이 바닥에 엎드려서 모델 올려다보기",
                "framing": "전신, 다리 길어보이게, 차 휠/범퍼 일부만"
            },
            {
                "pose": "The Hood Lounger (보닛 점유)",
                "pose_detail": "차 보닛 위에 비스듬히 앉아서, 뒤로 손 짚고 기대기. 다리는 쭉 뻗거나 꼬아서.",
                "expression": "지루한 듯 먼 곳 응시, 카메라 무시",
                "angle": "45도 측면, 약간 로우앵글",
                "framing": "전신, 보닛 일부와 함께"
            },
            {
                "pose": "쭈그려 앉아서 턱 괴기",
                "pose_detail": "바닥에 쭈그려 앉고, 한쪽 무릎 세우고, 팔꿈치를 무릎에 올려서 손으로 턱 받치기.",
                "expression": "살짝 시크한 표정, 눈은 카메라 똑바로",
                "angle": "로우앵글 - 바닥 높이에서 올려다보기",
                "framing": "전신 또는 무릎 위"
            },
            {
                "pose": "걷다가 뒤돌아보기 (역동적)",
                "pose_detail": "걷는 중간에 어깨 너머로 카메라 쪽 돌아보기. 머리카락 날리는 느낌.",
                "expression": "살짝 도발적인 눈빛, 입술 살짝 벌림",
                "angle": "측면에서 아이레벨",
                "framing": "전신, 역동적인 순간 포착"
            },
            {
                "pose": "바닥에 앉아서 손으로 머리 받치기",
                "pose_detail": "바닥에 다리 쭉 뻗고 편하게 앉아서, 한손으로 머리 옆 받치고, 다른 손은 바닥 짚기.",
                "expression": "편안하면서 쿨한 표정, 카메라 무심하게 보기",
                "angle": "하이앵글 - 위에서 45도로 내려다보기",
                "framing": "전신, 다리 라인 강조"
            },
            {
                "pose": "벽에 기대서 (Leaning on Wall)",
                "pose_detail": "콘크리트 벽에 한쪽 어깨 기대서. 한 손은 주머니, 다른 손은 벽에 가볍게.",
                "expression": "시크하고 무심한 눈빛, 카메라 쳐다보기",
                "angle": "아이레벨, 정면 또는 45도",
                "framing": "전신 또는 무릎 위"
            },
            {
                "pose": "차 문에 기대기 (Leaning on Car Door)",
                "pose_detail": "열린 차 문에 등을 기대고 서서. 팔짱 끼거나 한 손으로 머리 만지기.",
                "expression": "지루한 듯 카메라 응시, 입꼬리 살짝",
                "angle": "45도 측면, 아이레벨",
                "framing": "전신, 차 문과 함께"
            },
            {
                "pose": "계단에 앉아서 (Sitting on Stairs)",
                "pose_detail": "계단에 앉아서 다리 벌리고 앞으로 기울이기. 팔꿈치를 무릎에.",
                "expression": "강한 눈빛, 카메라 똑바로 응시",
                "angle": "로우앵글, 정면",
                "framing": "전신, 계단 라인 강조"
            },
            {
                "pose": "뒤돌아서서 (Back Turned)",
                "pose_detail": "카메라에 등을 보이고 서서, 고개만 어깨 너머로 돌려 카메라 봄.",
                "expression": "신비로운 눈빛, 입술 살짝 벌림",
                "angle": "아이레벨, 등 쪽에서",
                "framing": "전신, 뒷모습과 옆얼굴"
            },
            {
                "pose": "차 앞에서 서서 (Standing in Front of Car)",
                "pose_detail": "차 앞에 서서 정면 응시. 양손은 허리에 또는 팔짱. 파워풀한 스탠스.",
                "expression": "자신감 넘치는 표정, 정면 응시",
                "angle": "아이레벨, 정면",
                "framing": "전신, 차가 배경으로"
            }
        ]

        # [SELFIE] 셀피용 포즈 라이브러리 (10개 - 거울셀카, 대기실, 다양한 앵글)
        SELFIE_POSE_VARIATIONS = [
            {
                "pose": "전신 거울 셀피 (Full Body Mirror)",
                "pose_detail": "전신 거울 앞에 서서 한 손으로 스마트폰 들고 셀피. 거울에 비친 전신이 보이도록. 다른 손은 허리에.",
                "expression": "무심한 표정, 살짝 입꼬리 올림, 눈은 폰 화면 응시",
                "angle": "아이레벨 - 거울 속에 비친 모습",
                "framing": "거울에 비친 전신, 폰 들고 있는 손 보임"
            },
            {
                "pose": "화장대 거울 셀피 (Vanity Mirror)",
                "pose_detail": "화장대 거울 앞에서 셀피. 화장대 조명 아래. 한 손으로 머리 만지거나 턱 받침.",
                "expression": "살짝 시크한 표정, 눈은 거울 속 자신 응시",
                "angle": "아이레벨, 약간 클로즈업",
                "framing": "상반신, 화장대 조명 보임"
            },
            {
                "pose": "하이앵글 셀피 (High Angle Direct)",
                "pose_detail": "한 손으로 폰을 위로 들어 하이앵글 셀피. 얼굴이 작아보이는 각도. 다른 손은 머리 뒤로.",
                "expression": "살짝 도도한 표정, 눈은 카메라 렌즈 올려다봄",
                "angle": "하이앵글 - 위에서 내려다보는 셀피 앵글",
                "framing": "얼굴 클로즈업, 상반신 일부"
            },
            {
                "pose": "소파에 앉아 셀피 (Sitting on Sofa)",
                "pose_detail": "소파에 편하게 기대앉아서, 한 손으로 폰 들고 셀피. 다리 꼬고 한쪽 팔은 소파 등받이에.",
                "expression": "릴렉스한 표정, 여유로운 미소",
                "angle": "아이레벨, 약간 측면",
                "framing": "상반신, 소파 일부 보임"
            },
            {
                "pose": "옆모습 거울 셀피 (Side Profile Mirror)",
                "pose_detail": "거울을 보며 45도 각도로 서서 셀피. 옆모습이 보이도록. 한 손은 머리카락 정리.",
                "expression": "시크한 옆모습, 입술 살짝 내밀기",
                "angle": "거울에 비친 45도 측면",
                "framing": "전신 또는 상반신, 옆모습 강조"
            },
            {
                "pose": "로우앵글 셀피 (Low Angle Direct)",
                "pose_detail": "폰을 턱 아래에서 들어 로우앵글 셀피. 강한 인상. 턱선 강조.",
                "expression": "도도하고 강한 눈빛, 턱 살짝 들기",
                "angle": "로우앵글 - 아래에서 올려다보는 각도",
                "framing": "얼굴 클로즈업, 턱선 강조"
            },
            {
                "pose": "기대서 셀피 (Leaning on Wall)",
                "pose_detail": "벽에 한쪽 어깨 기대서 셀피. 자연스럽게 한쪽 다리 꼬고. 폰은 얼굴 앞으로.",
                "expression": "무심한 표정, 살짝 지루한 듯",
                "angle": "아이레벨, 정면 또는 약간 측면",
                "framing": "상반신 또는 무릎 위"
            },
            {
                "pose": "바닥에 앉아 셀피 (Sitting on Floor)",
                "pose_detail": "바닥에 다리 뻗고 앉아서 셀피. 한쪽 무릎 세우고. 폰은 약간 위에서.",
                "expression": "편안하고 캐주얼한 표정",
                "angle": "약간 하이앵글",
                "framing": "전신, 다리 라인 보임"
            },
            {
                "pose": "뒤돌아 거울 셀피 (Back Turned Mirror)",
                "pose_detail": "거울 앞에서 뒤돌아서서 어깨 너머로 셀피. 등이 거울에 비침. 고개만 돌려 카메라 봄.",
                "expression": "어깨 너머 신비로운 눈빛",
                "angle": "거울에 비친 뒷모습",
                "framing": "전신, 뒷모습과 옆얼굴"
            },
            {
                "pose": "걷다가 셀피 (Walking Selfie)",
                "pose_detail": "걸으면서 자연스럽게 셀피. 머리카락 날리는 느낌. 한 발 앞으로 나간 상태.",
                "expression": "자연스러운 미소, 캔디드한 느낌",
                "angle": "약간 하이앵글, 전방을 향해",
                "framing": "상반신 또는 전신, 역동적"
            }
        ]

        # 스타일에 따라 포즈 라이브러리 선택
        if style == "selfie":
            POSE_VARIATIONS = SELFIE_POSE_VARIATIONS
        else:
            POSE_VARIATIONS = EDITORIAL_POSE_VARIATIONS

        # 현재 연출에 해당하는 포즈/앵글/표정
        current_var = POSE_VARIATIONS[variation_index % len(POSE_VARIATIONS)]
        forced_pose = current_var["pose"]
        forced_pose_detail = current_var["pose_detail"]
        forced_expression = current_var["expression"]
        forced_angle = current_var["angle"]
        forced_framing = current_var["framing"]

        # 스타일별 JSON 스키마 예시
        if style == "selfie":
            json_schema_example = """```json
{{
  "concept": "촬영 컨셉 (한국어 한 줄)",
  "subject": {{
    "expression": "nonchalant / slightly bored / casual confidence / subtle smile"
  }},
  "pose": {{
    "style": "standing mirror selfie / sitting with phone / direct selfie arm extended",
    "legs": "standing naturally / sitting with legs crossed / one leg bent",
    "arms": "one hand holding phone, other hand natural / touching hair / peace sign",
    "body": "facing mirror / turned slightly / relaxed posture"
  }},
  "scene": {{
    "location": "music show waiting room / dressing room / backstage mirror",
    "background": "full length mirror / vanity mirror with lights / clean white wall with mirror",
    "props": "smartphone in hand visible in mirror / vanity lights / makeup table edge",
    "atmosphere": "casual behind the scenes / candid SNS vibe / relaxed waiting room"
  }},
  "camera": {{
    "angle": "eye level mirror reflection / slightly high angle selfie / straight on",
    "framing": "full body in mirror / upper body / face close up",
    "lens": "smartphone wide angle",
    "aperture": "f/1.8",
    "depth_of_field": "slight blur on background / sharp foreground"
  }},
  "lighting": {{
    "type": "fluorescent ceiling light / vanity mirror lights / soft indoor light",
    "color_temp": "cool white 4000K-5000K / warm vanity 3000K",
    "mood": "natural indoor / backstage casual"
  }},
  "outfit_notes": "outfit fully visible in mirror, logo details clear, natural smartphone quality"
}}
```"""
        else:
            json_schema_example = """```json
{{
  "concept": "촬영 컨셉 (한국어 한 줄)",
  "subject": {{
    "expression": "arrogant looking down / nonchalant / piercing gaze / bored / confident"
  }},
  "pose": {{
    "style": "squatting with one knee up / sitting on car hood / standing with foot on bumper / walking mid-stride",
    "legs": "right leg raised, left leg extended / legs crossed / legs spread wide",
    "arms": "left elbow on knee chin resting on hand / arms crossed / hands in pockets / one hand touching hair",
    "body": "leaning forward slightly / turned 45 degrees / straight posture"
  }},
  "scene": {{
    "location": "New York Financial District / SoHo street / Manhattan skyline",
    "background": "white G-Wagon parked / concrete wall / glass building reflection",
    "props": "luxury SUV side view / clean concrete bench / none",
    "atmosphere": "cool bored rich kid vibe / arrogant luxury / urban minimal"
  }},
  "camera": {{
    "angle": "low angle looking up at model / eye level / high angle looking down / 45 degree side view",
    "framing": "full body / knee up / waist up / close up face",
    "lens": "85mm",
    "aperture": "f/2.0",
    "depth_of_field": "shallow bokeh background / sharp everything"
  }},
  "lighting": {{
    "type": "overcast daylight / blue hour / shade",
    "color_temp": "cool tone 5500K-6500K",
    "mood": "desaturated cool / cinematic blue"
  }},
  "outfit_notes": "MLB logo visible on cap and pants, NY logo on bag should be in frame"
}}
```"""

        # 스타일 설명
        style_description = "셀피/거울셀카" if style == "selfie" else "화보/에디토리얼"

        # 디렉터 페르소나 프롬프트 - JSON 스키마 출력
        director_prompt = f"""너는 "{persona}"야.

## 너의 철학
{chr(10).join(f'- "{p}"' for p in philosophy[:3]) if philosophy else '- 완벽한 이미지를 만든다'}

## 너의 스타일
- 선호 스타일: {', '.join(style_keywords[:5]) if style_keywords else 'high fashion'}
- 선호 세팅: {', '.join(setting_keywords[:3]) if setting_keywords else 'studio'}
- 선호 무드: {', '.join(mood_keywords[:3]) if mood_keywords else 'confident'}

## 오늘의 촬영 ({style_description})

**클라이언트 요청**: {user_request if user_request else '(없음)'}
**모델**: {gender}, {age}
**착장**: {outfit_desc if outfit_desc else '(이미지 참고)'}

---

🚨 이번 컷의 지정된 연출:
- 포즈: {forced_pose} → {forced_pose_detail}
- 표정: {forced_expression}
- 앵글: {forced_angle}
- 프레이밍: {forced_framing}

---

⚠️ 중요: 이미지 생성 AI가 이해할 수 있도록 **영어 키워드** 형태로 JSON을 출력해.
구어체("힘 빼고", "배경 확 날려") 금지! 영어 키워드만!

다음 JSON 스키마에 맞게 출력해:

{json_schema_example}

JSON만 출력해. 다른 텍스트 없이!"""

        parts = [types.Part(text=director_prompt)]

        # 착장 이미지 추가
        for img in outfit_images:
            part = self.pil_to_part(img)
            if part:
                parts.append(part)

        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash-exp",  # 빠른 응답용
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(temperature=0.8, max_output_tokens=1500)
            )

            text = response.text

            # JSON 파싱
            import re
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                try:
                    parsed = json.loads(json_match.group())

                    # 템플릿 스키마 형식으로 정리
                    result = {
                        "director_name": persona,
                        "concept": parsed.get("concept", ""),
                        "full_direction": text,  # 원본 저장

                        # subject
                        "subject": parsed.get("subject", {}),
                        "expression": parsed.get("subject", {}).get("expression", "confident"),

                        # pose (각 필드 조합)
                        "pose": parsed.get("pose", {}),
                        "pose_style": parsed.get("pose", {}).get("style", ""),
                        "pose_full": ", ".join([
                            parsed.get("pose", {}).get("style", ""),
                            parsed.get("pose", {}).get("legs", ""),
                            parsed.get("pose", {}).get("arms", ""),
                            parsed.get("pose", {}).get("body", "")
                        ]),

                        # scene
                        "scene": parsed.get("scene", {}),
                        "location": parsed.get("scene", {}).get("location", ""),
                        "background": parsed.get("scene", {}).get("background", ""),
                        "props": parsed.get("scene", {}).get("props", ""),
                        "atmosphere": parsed.get("scene", {}).get("atmosphere", ""),

                        # camera
                        "camera": parsed.get("camera", {}),
                        "camera_angle": parsed.get("camera", {}).get("angle", ""),
                        "camera_framing": parsed.get("camera", {}).get("framing", ""),
                        "camera_lens": parsed.get("camera", {}).get("lens", "85mm"),
                        "camera_aperture": parsed.get("camera", {}).get("aperture", "f/2.0"),
                        "depth_of_field": parsed.get("camera", {}).get("depth_of_field", "shallow bokeh"),

                        # lighting
                        "lighting": parsed.get("lighting", {}),
                        "lighting_type": parsed.get("lighting", {}).get("type", "overcast daylight"),
                        "lighting_mood": parsed.get("lighting", {}).get("mood", "cool tone"),

                        # outfit
                        "outfit_highlight": parsed.get("outfit_notes", "")
                    }

                    # ═══════════════════════════════════════════════════════════
                    # 🚨 다양성 강제 적용: VLM 결과 위에 강제 포즈/앵글/표정 덮어쓰기
                    # VLM이 강제 지정을 무시할 수 있으므로 결과에 직접 적용
                    # ═══════════════════════════════════════════════════════════
                    result["forced_pose"] = forced_pose
                    result["forced_pose_detail"] = forced_pose_detail
                    result["forced_expression"] = forced_expression
                    result["forced_angle"] = forced_angle
                    result["forced_framing"] = forced_framing

                    # pose_full에 강제 포즈 정보 병합 (VLM 결과 + 강제 지정)
                    result["pose_full"] = f"{forced_pose_detail}"

                    # camera_angle, camera_framing에 강제 앵글/프레이밍 적용
                    result["camera_angle"] = forced_angle
                    result["camera_framing"] = forced_framing

                    # expression에 강제 표정 적용
                    result["expression"] = forced_expression

                    print(f"[Workflow] 다양성 강제 적용: 포즈={forced_pose[:30]}..., 표정={forced_expression[:20]}..., 앵글={forced_angle[:20]}...")

                    return result

                except json.JSONDecodeError as e:
                    print(f"[Workflow] JSON 파싱 실패: {e}")

            # JSON 파싱 실패시 강제 포즈로 기본값 반환
            print(f"[Workflow] JSON 파싱 실패, 강제 포즈로 fallback")
            return {
                "director_name": persona,
                "concept": "",
                "full_direction": text,
                "subject": {},
                "pose": {},
                "scene": {},
                "camera": {},
                "lighting": {},
                # 강제 포즈 값 적용
                "expression": forced_expression,
                "pose_full": forced_pose_detail,
                "camera_angle": forced_angle,
                "camera_framing": forced_framing,
                "forced_pose": forced_pose,
                "forced_pose_detail": forced_pose_detail,
                "forced_expression": forced_expression,
                "forced_angle": forced_angle,
                "forced_framing": forced_framing,
                "location": "",
                "outfit_highlight": ""
            }

        except Exception as e:
            print(f"[Workflow] 디렉터 비전 생성 실패: {e}, 강제 포즈로 fallback")
            # 예외 발생 시에도 강제 포즈 적용
            return {
                "full_direction": "",
                "error": str(e),
                "expression": forced_expression,
                "pose_full": forced_pose_detail,
                "camera_angle": forced_angle,
                "camera_framing": forced_framing,
                "forced_pose": forced_pose,
                "forced_pose_detail": forced_pose_detail,
                "forced_expression": forced_expression,
                "forced_angle": forced_angle,
                "forced_framing": forced_framing,
                "location": "",
                "outfit_highlight": ""
            }

    # ═══════════════════════════════════════════════════════════════
    # [4] 프롬프트 조립
    # ═══════════════════════════════════════════════════════════════

    def build_prompt(
        self,
        brand_dna: Dict,
        template: Dict,
        input_vars: Dict = None
    ) -> str:
        """
        브랜드 DNA + 템플릿 → 최종 프롬프트

        Args:
            brand_dna: 브랜드 DNA JSON
            template: 프롬프트 템플릿 JSON
            input_vars: 사용자 입력 변수 (gender, age 등)
        """
        input_vars = input_vars or {}

        # 템플릿 포맷 가져오기
        builder = template.get("prompt_builder", {})
        format_str = builder.get("format", "")
        brand_injection = builder.get("brand_injection", "")

        # 변수 치환 준비
        replacements = {
            # 메타
            "{meta.quality}": template.get("template", {}).get("meta", {}).get("quality", "photorealistic"),

            # 피사체
            "{subject.gender}": input_vars.get("gender", "여성"),
            "{subject.age}": input_vars.get("age", "20대 중반"),
            "{subject.expression}": brand_dna.get("director_guidelines", {}).get("expression", {}).get("type", "natural"),
            "{subject.skin}": "ultra realistic skin texture, natural pores",

            # 의상
            "{outfit.style}": ", ".join(brand_dna.get("keywords", {}).get("style", ["stylish"])[:2]),
            "{outfit.mood}": brand_dna.get("identity", {}).get("mood", ["confident"])[0] if brand_dna.get("identity", {}).get("mood") else "confident",

            # 포즈
            "{pose.style}": brand_dna.get("director_guidelines", {}).get("pose", {}).get("style", "natural"),

            # 씬
            "{scene.location}": brand_dna.get("keywords", {}).get("setting", ["studio"])[0] if brand_dna.get("keywords", {}).get("setting") else "studio",
            "{scene.background}": brand_dna.get("must_include_keywords", {}).get("background", ["clean background"])[0] if brand_dna.get("must_include_keywords", {}).get("background") else "clean background",

            # 조명
            "{lighting.type}": brand_dna.get("director_guidelines", {}).get("lighting", {}).get("type", "soft lighting"),
            "{lighting.quality}": brand_dna.get("director_guidelines", {}).get("lighting", {}).get("quality", "diffused"),

            # 기술
            "{technical.resolution}": "8k",
            "{technical.skin_texture}": "hyper-realistic skin",
            "{technical.color_grading}": "editorial color grading",

            # 브랜드 주입
            "{brand_dna._metadata.persona}": brand_dna.get("_metadata", {}).get("persona", ""),
            "{brand_dna._metadata.brand}": brand_dna.get("_metadata", {}).get("brand", ""),
            "{brand_dna.identity.philosophy[0]}": brand_dna.get("identity", {}).get("philosophy", [""])[0] if brand_dna.get("identity", {}).get("philosophy") else "",
            "{brand_dna.identity.mood[0]}": brand_dna.get("identity", {}).get("mood", [""])[0] if brand_dna.get("identity", {}).get("mood") else "",
        }

        # 변수 치환
        prompt = format_str
        for key, value in replacements.items():
            prompt = prompt.replace(key, str(value))

        # 브랜드 주입
        brand_line = brand_injection
        for key, value in replacements.items():
            brand_line = brand_line.replace(key, str(value))

        if brand_line:
            prompt = f"{prompt}\n\n{brand_line}"

        return prompt

    def build_negative_prompt(self, brand_dna: Dict, template: Dict) -> str:
        """네거티브 프롬프트 생성"""
        negatives = []

        # 템플릿 기본 네거티브
        negatives.extend(template.get("negative_prompt", []))

        # 브랜드 금지 키워드
        forbidden = brand_dna.get("forbidden_keywords", {})
        if isinstance(forbidden, dict):
            for category_keywords in forbidden.values():
                if isinstance(category_keywords, list):
                    negatives.extend(category_keywords)
        elif isinstance(forbidden, list):
            negatives.extend(forbidden)

        # 중복 제거
        return ", ".join(list(dict.fromkeys(negatives)))

    def build_prompt_from_template(
        self,
        template: Dict,
        brand_dna: Dict,
        outfit_data: Dict,
        director_vision: Dict,
        input_vars: Dict = None
    ) -> str:
        """
        템플릿 기반 프롬프트 생성 - JSON 형식으로 출력

        Args:
            template: editorial.json 템플릿
            brand_dna: 브랜드 DNA
            outfit_data: build_outfit_for_template() 결과
            director_vision: generate_director_vision() 결과 (JSON 스키마)
            input_vars: 사용자 입력 (gender, age 등)
        """
        input_vars = input_vars or {}
        tmpl = template.get("template", {})

        # 템플릿에서 기본값 가져오기
        meta = tmpl.get("meta", {})
        subject_tmpl = tmpl.get("subject", {})
        technical = tmpl.get("technical", {})

        # JSON 구조로 프롬프트 구성 (템플릿 값 우선 사용)
        prompt_json = {
            "meta": {
                "aspect_ratio": meta.get("aspect_ratio", "4:5"),
                "quality": meta.get("quality", "ultra_photorealistic_editorial, 8k"),
                "camera": meta.get("camera", "Hasselblad H6D-100c"),
                "lens": director_vision.get("camera_lens", meta.get("lens", "85mm f/2.0"))
            },
            "subject": {
                "gender": input_vars.get("gender", "여성"),
                "age": input_vars.get("age", "20대 초반"),
                "ethnicity": "East Asian",
                "expression": director_vision.get("expression", "confident"),
                "skin": subject_tmpl.get("skin", "ultra realistic skin texture, natural pores")
            },
            "outfit": {
                # outfit.items가 비어있으면 director_vision.outfit_highlight 사용 (fallback)
                "items": outfit_data.get("items", "") or director_vision.get("outfit_highlight", ""),
                "style": outfit_data.get("style", "") or director_vision.get("atmosphere", ""),
                "brand_aesthetic": brand_dna.get("_metadata", {}).get("brand", "") + " aesthetic"
            },
            "pose": {
                "style": director_vision.get("pose_full", "confident standing"),
                "selfie_type": tmpl.get("pose", {}).get("selfie_type", ""),
                "arm_position": tmpl.get("pose", {}).get("arm_position", "")
            },
            "scene": {
                "location": director_vision.get("location", ""),
                "background": director_vision.get("background", ""),
                "atmosphere": director_vision.get("props", "")
            },
            "lighting": {
                "type": director_vision.get("lighting_type", "natural light"),
                "quality": director_vision.get("lighting_mood", "soft_diffused"),
                "color_temp": "5500K"
            },
            "camera": {
                "angle": director_vision.get("camera_angle", ""),
                "framing": director_vision.get("camera_framing", tmpl.get("pose", {}).get("framing", "full body")),
                "lens": director_vision.get("camera_lens", "85mm"),
                "aperture": director_vision.get("camera_aperture", "f/2.0"),
                "depth_of_field": director_vision.get("depth_of_field", technical.get("depth_of_field", "shallow bokeh"))
            },
            "technical": {
                "resolution": technical.get("resolution", "8k"),
                "skin_texture": technical.get("skin_texture", "hyper-realistic, visible pores"),
                "lens_characteristics": technical.get("lens_characteristics", "")
            },
            "style": {
                "persona": brand_dna.get("_metadata", {}).get("persona", ""),
                "direction": "in the style of " + brand_dna.get("_metadata", {}).get("persona", "")
            }
        }

        # JSON 문자열로 변환
        import json
        prompt = json.dumps(prompt_json, ensure_ascii=False, indent=2)

        return prompt

    # ═══════════════════════════════════════════════════════════════
    # [4] 이미지 생성
    # ═══════════════════════════════════════════════════════════════

    def pil_to_part(self, img: "Image.Image") -> Optional[Any]:
        """PIL 이미지를 Gemini Part로 변환"""
        if img is None or types is None:
            return None
        try:
            buf = BytesIO()
            img.save(buf, format="PNG")
            return types.Part(
                inline_data=types.Blob(
                    mime_type="image/png",
                    data=buf.getvalue()
                )
            )
        except Exception as e:
            print(f"[Workflow] pil_to_part 실패: {e}")
            return None

    def generate_single(
        self,
        prompt: str,
        negative_prompt: str,
        model_images: List = None,
        outfit_images: List = None,
        outfit_description: str = "",
        background_image: Any = None,
        model: str = "gemini-3-pro-image-preview",
        aspect_ratio: str = "3:4"
    ) -> Optional["Image.Image"]:
        """
        단일 이미지 생성

        Args:
            prompt: 메인 프롬프트
            negative_prompt: 네거티브 프롬프트
            model_images: 모델(얼굴) 참조 이미지 리스트
            outfit_images: 착장 참조 이미지 리스트
            background_image: 배경 참조 이미지
            model: Gemini 모델명
            aspect_ratio: 이미지 비율
        """
        client = self._get_client()
        if client is None:
            print("[Workflow] Gemini 클라이언트 없음")
            return None

        # ═══════════════════════════════════════════════════════════
        # 프롬프트 구성: 이미지 먼저 + 핵심 정보 간결하게
        # (모든 분석/기획 과정은 유지, 프롬프트만 요약)
        # ═══════════════════════════════════════════════════════════
        parts = []

        # 1. 모델(얼굴) 참조 이미지 먼저
        if model_images:
            parts.append(types.Part(text="[MODEL - use this exact person's face]:"))
            for img in model_images:
                part = self.pil_to_part(img)
                if part:
                    parts.append(part)

        # 2. 착장 참조 이미지
        if outfit_images:
            parts.append(types.Part(text="\n[OUTFIT - the model must wear ALL these items exactly]:"))
            for img in outfit_images:
                part = self.pil_to_part(img)
                if part:
                    parts.append(part)

        # 3. 착장 분석 결과 (간결하게)
        if outfit_description:
            parts.append(types.Part(text=f"\n[OUTFIT DETAILS]: {outfit_description}"))

        # 4. 핵심 프롬프트 (디렉터 비전 + 브랜드 DNA 핵심만)
        # prompt에서 Location 추출해서 명확하게 배치
        import re
        location_match = re.search(r'Location:\s*([^|]+)', prompt)
        location_instruction = ""
        if location_match:
            loc_text = location_match.group(1).strip()
            location_instruction = f"\n- BACKGROUND: {loc_text} (no people in background, clean and modern)"

        core_prompt = f"""
Generate a fashion editorial photo:{location_instruction}
- Use the EXACT face from the model reference
- Wear ALL outfit items shown above exactly as they appear
- {prompt}

Important: The background must be the specified location, not a studio.
Avoid: {negative_prompt}
"""
        parts.append(types.Part(text=core_prompt))

        # 4. 배경 이미지
        if background_image:
            parts.append(types.Part(text="\n[BACKGROUND REFERENCE]:"))
            bg_part = self.pil_to_part(background_image)
            if bg_part:
                parts.append(bg_part)

        # API 호출 (키 로테이션 포함)
        max_retries = len(self.api_keys)
        for attempt in range(max_retries):
            try:
                client = self._get_client(force_new=(attempt > 0))
                if client is None:
                    return None

                gen_config = types.GenerateContentConfig(
                    response_modalities=['Image'],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio,
                    )
                )

                response = client.models.generate_content(
                    model=model,
                    contents=[types.Content(role="user", parts=parts)],
                    config=gen_config
                )

                # 이미지 추출
                if response and hasattr(response, 'parts'):
                    for part in response.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            return Image.open(BytesIO(part.inline_data.data))

                return None

            except Exception as e:
                error_str = str(e)
                print(f"[Workflow] 이미지 생성 실패 (키 #{self.current_key_index + 1}): {error_str[:100]}")

                # 503/429/499 에러시 다음 키로 로테이션
                if any(code in error_str for code in ["503", "429", "499", "500"]) or "overloaded" in error_str.lower() or "cancelled" in error_str.lower():
                    if self._rotate_api_key():
                        print(f"[Workflow] 재시도 {attempt + 2}/{max_retries}...")
                        time.sleep(2)  # 잠시 대기
                        continue

                return None

        return None

    # ═══════════════════════════════════════════════════════════════
    # [5] 메인 워크플로
    # ═══════════════════════════════════════════════════════════════

    def generate(
        self,
        user_input: str = None,
        brand: str = None,
        style: str = None,
        count: int = 1,
        model_images: List = None,
        outfit_images: List = None,
        background_image: Any = None,
        input_vars: Dict = None,
        model: str = "gemini-3-pro-image-preview",
        aspect_ratio: str = "3:4",
        max_workers: int = 4
    ) -> Dict[str, Any]:
        """
        인물 이미지 생성 메인 함수

        Args:
            user_input: 자연어 입력 (예: "MLB 프리미엄 화보 5장")
            brand: 브랜드 키 (직접 지정 시)
            style: 스타일 키 (직접 지정 시)
            count: 생성 수량
            model_images: 모델(얼굴) 참조 이미지 리스트
            outfit_images: 착장 참조 이미지 리스트
            background_image: 배경 참조 이미지
            input_vars: 추가 변수 (gender, age 등)
            model: Gemini 모델명
            aspect_ratio: 이미지 비율
            max_workers: 병렬 처리 worker 수

        Returns:
            {
                "status": "success" | "error",
                "brand": "mlb-marketing",
                "style": "editorial",
                "count": 5,
                "generated": 5,
                "images": [PIL.Image, ...],
                "prompts": ["prompt1", ...],
                "error": None | "error message"
            }
        """
        start_time = time.time()
        result = {
            "status": "success",
            "brand": None,
            "style": None,
            "count": count,
            "generated": 0,
            "images": [],
            "prompts": [],
            "photo_direction": None,  # 포토 디렉팅 기획
            "outfit_analysis": None,  # 착장 분석 결과
            "error": None
        }

        try:
            # [1] 브랜드/스타일 라우팅
            if brand is None and user_input:
                brand = self.route_brand(user_input)
            if style is None and user_input:
                style = self.route_style(user_input)

            if brand is None:
                result["status"] = "error"
                result["error"] = "브랜드를 감지할 수 없습니다"
                return result

            style = style or "editorial"
            result["brand"] = brand
            result["style"] = style

            print(f"[Workflow] 브랜드: {brand}, 스타일: {style}, 수량: {count}")

            # [2] 정적 데이터 로드
            brand_dna = self.load_brand_dna(brand)
            template = self.load_template(style, brand)

            if not brand_dna:
                result["status"] = "error"
                result["error"] = f"브랜드 DNA를 찾을 수 없습니다: {brand}"
                return result

            persona = brand_dna.get('_metadata', {}).get('persona', 'Unknown')
            print(f"[Workflow] 브랜드 DNA 로드 완료: {persona}")

            # [2.5] 브랜드 디렉터 SKILL.md 로드 및 파싱
            director_skill = self.load_brand_director_skill(brand)
            director_directives = {}
            if director_skill:
                director_directives = self.parse_director_skill(director_skill)
                print(f"[Workflow] 브랜드 디렉터 스킬 파싱 완료: {director_directives.get('persona', 'Unknown')}")
                print(f"  - 스타일: {len(director_directives.get('style_keywords', []))}개")
                print(f"  - 포즈: {len(director_directives.get('pose_guidelines', []))}개")
                print(f"  - DO: {len(director_directives.get('do_rules', []))}개")
                print(f"  - DON'T: {len(director_directives.get('dont_rules', []))}개")

            # [3] 착장 분석 (착장 이미지가 있을 경우)
            outfit_description = ""
            key_features = []
            outfit_analysis = {}
            if outfit_images:
                print(f"[Workflow] 착장 분석 시작 ({len(outfit_images)}개)")
                outfit_analysis = self.analyze_outfit(outfit_images)
                result["outfit_analysis"] = outfit_analysis
                outfit_description = outfit_analysis.get("outfit_description", "")
                key_features = outfit_analysis.get("key_features", [])
                if outfit_description:
                    print(f"[Workflow] 착장 분석 완료: {outfit_description[:50]}...")
                else:
                    print(f"[Workflow] 착장 분석 완료 (garments: {len(outfit_analysis.get('garments', []))}개)")

            # [4] 디렉터 페르소나가 직접 포토 디렉팅 (자아 있는 디렉팅)
            director_vision = {}
            if outfit_images and director_directives:
                print(f"\n[Workflow] 🎬 {director_directives.get('persona', 'Director')}가 착장을 보고 디렉팅 중...")
                director_vision = self.generate_director_vision(
                    outfit_images=outfit_images,
                    outfit_analysis=outfit_analysis,
                    director_directives=director_directives,
                    input_vars=input_vars,
                    user_request=user_input or "",  # 사용자 요청 전달 (배경 등)
                    style=style  # 스타일 전달 (editorial/selfie)
                )
                result["director_vision"] = director_vision

                # 디렉터 비전 출력 (자아 있는 디렉팅)
                if director_vision.get("full_direction"):
                    print("\n" + "="*60)
                    print(f"🎬 [{director_vision.get('director_name', 'Director')}의 포토 디렉팅]")
                    print("="*60)
                    if director_vision.get("concept"):
                        print(f"\n📌 컨셉: {director_vision['concept']}")
                    if director_vision.get("location"):
                        print(f"\n📍 로케이션: {director_vision['location']}")
                    if director_vision.get("pose"):
                        print(f"\n🧍 포즈: {director_vision['pose']}")
                    if director_vision.get("expression"):
                        print(f"\n😎 표정/시선: {director_vision['expression']}")
                    if director_vision.get("outfit_highlight"):
                        print(f"\n👕 착장 포인트: {director_vision['outfit_highlight']}")
                    if director_vision.get("mood"):
                        print(f"\n🌙 무드: {director_vision['mood']}")
                    if director_vision.get("camera"):
                        print(f"\n📷 카메라: {director_vision['camera']}")
                    if director_vision.get("director_comment"):
                        print(f"\n💬 디렉터 한마디: \"{director_vision['director_comment']}\"")
                    print("="*60 + "\n")

            # 기존 photo_direction도 유지 (호환성)
            photo_direction = {
                "brand": brand_dna.get('_metadata', {}).get('brand', brand),
                "persona": director_directives.get('persona') or persona,
                "philosophy": director_directives.get('philosophy', []),
                "outfit": outfit_description,
                "outfit_features": outfit_analysis.get("key_features", []) if outfit_images else [],
                "director_vision": director_vision,  # 새로운 디렉터 비전 추가
            }
            result["photo_direction"] = photo_direction

            # [5] 프롬프트 조립 - 핵심만 간결하게 (과정은 모두 유지, 프롬프트만 요약)
            prompt = self.build_prompt(brand_dna, template, input_vars)

            # 디렉터 비전 핵심만 간결하게 추가 (긴 텍스트 대신 키워드)
            if director_vision.get("full_direction"):
                concise_direction = []
                if director_vision.get("location"):
                    loc = director_vision['location'].split('.')[0][:50]
                    concise_direction.append(f"Location: {loc}")
                if director_vision.get("pose"):
                    pose = director_vision['pose'].split('.')[0][:50]
                    concise_direction.append(f"Pose: {pose}")
                if director_vision.get("expression"):
                    expr = director_vision['expression'].split('.')[0][:40]
                    concise_direction.append(f"Expression: {expr}")
                if director_vision.get("mood"):
                    concise_direction.append(f"Mood: {director_vision['mood'][:50]}")
                if director_vision.get("camera"):
                    # 카메라 정보에서 핵심만 추출 (렌즈mm, 필름룩, 앵글)
                    cam_text = director_vision['camera']
                    cam_keywords = []
                    # 렌즈mm 추출
                    import re as re_cam
                    lens_match = re_cam.search(r'(\d+mm)', cam_text)
                    if lens_match:
                        cam_keywords.append(lens_match.group(1))
                    # 필름룩 추출
                    for film in ['Portra 400', 'Portra 800', 'Cinestill', 'Fuji Pro', 'Ilford']:
                        if film.lower() in cam_text.lower():
                            cam_keywords.append(film + ' film look')
                            break
                    # 조리개 추출
                    aperture_match = re_cam.search(r'f/[\d.]+', cam_text)
                    if aperture_match:
                        cam_keywords.append(aperture_match.group())
                    concise_direction.append(f"Shot on: {', '.join(cam_keywords) if cam_keywords else cam_text[:40]}")

                if concise_direction:
                    prompt += "\n\n[DIRECTION]: " + " | ".join(concise_direction)

            # 폴백: 디렉터 비전이 없으면 정적 지침 (키워드만)
            elif director_directives:
                keywords = []
                if director_directives.get('style_keywords'):
                    keywords.extend(director_directives['style_keywords'][:3])
                if director_directives.get('mood_keywords'):
                    keywords.extend(director_directives['mood_keywords'][:2])
                if keywords:
                    prompt += f"\n\n[STYLE]: {', '.join(keywords)}"

            # 착장 분석 결과 (간결하게)
            if outfit_description:
                # 착장 설명 첫 100자만
                short_outfit = outfit_description[:100] + "..." if len(outfit_description) > 100 else outfit_description
                prompt += f"\n\n[OUTFIT]: {short_outfit}"

            negative = self.build_negative_prompt(brand_dna, template)

            # DON'T 룰을 네거티브에 추가
            if director_directives.get('dont_rules'):
                negative += ", " + ", ".join(director_directives['dont_rules'][:5])

            print(f"[Workflow] 프롬프트 생성 완료 ({len(prompt)} chars)")
            result["prompts"] = [prompt] * count

            # [4] 병렬 이미지 생성
            print(f"[Workflow] 이미지 생성 시작 ({count}장, {max_workers} workers)")

            def generate_one(idx):
                img = self.generate_single(
                    prompt=prompt,
                    negative_prompt=negative,
                    model_images=model_images,
                    outfit_images=outfit_images,
                    outfit_description=outfit_description,
                    background_image=background_image,
                    model=model,
                    aspect_ratio=aspect_ratio
                )
                return (idx, img)

            images = [None] * count
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(generate_one, i) for i in range(count)]

                for future in as_completed(futures):
                    idx, img = future.result()
                    if img:
                        images[idx] = img
                        result["generated"] += 1
                        print(f"[Workflow] {result['generated']}/{count} 완료")

            result["images"] = [img for img in images if img is not None]

            elapsed = time.time() - start_time
            print(f"[Workflow] 완료: {result['generated']}/{count}장, {elapsed:.1f}초")

            return result

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            print(f"[Workflow] 오류: {e}")
            return result


    def generate_with_details(
        self,
        user_input: str = None,
        brand: str = None,
        style: str = None,
        count: int = 1,
        model_images: List = None,
        outfit_images: List = None,
        background_image: Any = None,
        input_vars: Dict = None,
        model: str = "gemini-3-pro-image-preview",
        aspect_ratio: str = "3:4",
        max_workers: int = 4,
        variation_index: int = 0
    ) -> Dict[str, Any]:
        """
        상세 로깅이 포함된 이미지 생성 - 모든 스킬 호출 내용 출력

        Args:
            (generate와 동일)
            variation_index: 연출 번호 (0~4)
        """
        print("\n" + "=" * 70)
        print(f"📋 [스킬 호출 시작] 연출 #{variation_index + 1}")
        print("=" * 70)

        # ================================================================
        # 브랜드/스타일 라우팅 (빠름 - 먼저 실행)
        # ================================================================
        print("\n" + "-" * 50)
        print("🔍 [라우팅] 브랜드/스타일 감지")
        print("-" * 50)
        print(f"  입력: \"{user_input}\"")

        if brand is None and user_input:
            brand = self.route_brand(user_input)
        if style is None and user_input:
            style = self.route_style(user_input)

        style = style or "editorial"
        print(f"  결과: 브랜드={brand}, 스타일={style}")

        # ================================================================
        # 🚀 병렬 처리: 정적 로드 + 착장 분석 동시 실행
        # ================================================================
        from concurrent.futures import ThreadPoolExecutor
        import time as time_module

        print("\n" + "-" * 50)
        print("🚀 [병렬 처리] 정적 로드 + 착장 분석 (VLM) 동시 실행")
        print("-" * 50)

        parallel_start = time_module.time()

        # 병렬 작업 결과 저장용
        brand_dna = {}
        template = {}
        director_directives = {}
        outfit_analysis = {}
        outfit_description = ""

        def load_static_data():
            """정적 데이터 로드 (Brand DNA, 템플릿, 디렉터 스킬)"""
            _brand_dna = self.load_brand_dna(brand)
            _template = self.load_template(style, brand)
            _director_skill = self.load_brand_director_skill(brand)
            _director_directives = {}
            if _director_skill:
                _director_directives = self.parse_director_skill(_director_skill)
            return {
                "brand_dna": _brand_dna,
                "template": _template,
                "director_directives": _director_directives
            }

        def analyze_outfit_parallel():
            """착장 분석 (VLM 호출) - 느린 작업"""
            if outfit_images:
                return self.analyze_outfit(outfit_images)
            return {}

        # 병렬 실행
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_static = executor.submit(load_static_data)
            future_outfit = executor.submit(analyze_outfit_parallel)

            # 결과 수집
            static_result = future_static.result()
            outfit_analysis = future_outfit.result()

        brand_dna = static_result["brand_dna"]
        template = static_result["template"]
        director_directives = static_result["director_directives"]
        outfit_description = outfit_analysis.get("outfit_description", "")

        parallel_elapsed = time_module.time() - parallel_start
        print(f"  ⏱️ 병렬 처리 완료: {parallel_elapsed:.2f}초")

        # 정적 로드 결과 출력
        print("\n" + "-" * 50)
        print("📖 [정적 데이터 로드 결과]")
        print("-" * 50)
        if brand_dna:
            persona = brand_dna.get('_metadata', {}).get('persona', 'Unknown')
            brand_name = brand_dna.get('_metadata', {}).get('brand', brand)
            print(f"  Brand DNA: {brand_name} ({persona})")
            print(f"  철학: {brand_dna.get('identity', {}).get('philosophy', [])[:1]}")
        if template:
            print(f"  템플릿: {template.get('brand', 'default')}_{style}.json")
        if director_directives:
            print(f"  디렉터: {director_directives.get('persona', 'Unknown')}")
            print(f"  DO/DON'T: {len(director_directives.get('do_rules', []))}개 / {len(director_directives.get('dont_rules', []))}개")

        # 착장 분석 결과 출력
        print("\n" + "-" * 50)
        print("👕 [착장 분석 결과] (VLM)")
        print("-" * 50)
        if outfit_analysis.get("garments"):
            print(f"  분석된 아이템: {len(outfit_analysis.get('garments', []))}개")
            for i, garment in enumerate(outfit_analysis.get("garments", [])):
                cat = garment.get('category', 'unknown')
                desc = garment.get('image_gen_description', garment.get('description', ''))[:50]
                print(f"    {i+1}. [{cat}] {desc}...")
            print(f"  핵심 특징: {outfit_analysis.get('key_features', [])}")
        else:
            print(f"  ⚠️ 착장 분석 실패 - fallback 사용 예정")

        # ================================================================
        # SKILL 5: 디렉터 비전 생성 (VLM + 페르소나)
        # ================================================================
        director_vision = {}

        if outfit_images and director_directives:
            print("\n" + "-" * 50)
            print(f"🎥 [SKILL 5] 디렉터 비전 생성")
            print("-" * 50)
            print(f"  디렉터: {director_directives.get('persona', 'Director')}")
            print(f"  사용자 요청: \"{user_input}\"")
            print(f"  연출 번호: #{variation_index + 1} (매번 다른 연출)")

            # 연출마다 다른 포즈/앵글 강제 지정
            director_vision = self.generate_director_vision(
                outfit_images=outfit_images,
                outfit_analysis=outfit_analysis,
                director_directives=director_directives,
                input_vars=input_vars,
                user_request=user_input or "",
                variation_index=variation_index,  # 연출 번호 전달!
                style=style  # 스타일 전달 (editorial/selfie)
            )

            print(f"\n  [디렉터 디렉팅 결과] (JSON 스키마)")
            print(f"  ┌{'─' * 60}")
            if director_vision.get("concept"):
                print(f"  │ 📌 컨셉: {director_vision['concept']}")
            if director_vision.get("location"):
                print(f"  │ 📍 scene.location: {director_vision['location']}")
            if director_vision.get("background"):
                print(f"  │ 🏙️ scene.background: {director_vision['background']}")
            if director_vision.get("pose_full"):
                print(f"  │ 🧍 pose: {director_vision['pose_full'][:80]}...")
            if director_vision.get("expression"):
                print(f"  │ 😎 subject.expression: {director_vision['expression']}")
            if director_vision.get("camera_angle"):
                print(f"  │ 📷 camera.angle: {director_vision['camera_angle']}")
            if director_vision.get("camera_lens"):
                print(f"  │ 🔭 camera.lens: {director_vision['camera_lens']} {director_vision.get('camera_aperture', '')}")
            if director_vision.get("depth_of_field"):
                print(f"  │ 🌫️ camera.dof: {director_vision['depth_of_field']}")
            if director_vision.get("lighting_type"):
                print(f"  │ 💡 lighting: {director_vision['lighting_type']}")
            if director_vision.get("outfit_highlight"):
                print(f"  │ 👕 outfit_notes: {director_vision['outfit_highlight'][:60]}...")
            print(f"  └{'─' * 60}")

        # ================================================================
        # SKILL 6: 프롬프트 조립 (템플릿 기반)
        # ================================================================
        print("\n" + "-" * 50)
        print("📝 [SKILL 6] 최종 프롬프트 조립 (템플릿 기반)")
        print("-" * 50)

        # 착장 데이터 준비 (image_gen_description 활용)
        outfit_data = self.build_outfit_for_template(outfit_analysis)
        print(f"  [착장 키워드] {outfit_data.get('items', '')[:80]}...")

        # 템플릿 기반 프롬프트 생성
        prompt = self.build_prompt_from_template(
            template=template,
            brand_dna=brand_dna,
            outfit_data=outfit_data,
            director_vision=director_vision,
            input_vars=input_vars
        )

        negative = self.build_negative_prompt(brand_dna, template)
        if director_directives.get('dont_rules'):
            negative += ", " + ", ".join(director_directives['dont_rules'][:5])

        print(f"\n  [최종 프롬프트] ({len(prompt)} chars)")
        print(f"  ┌{'─' * 60}")
        for line in prompt.split('\n')[:15]:  # 처음 15줄만
            print(f"  │ {line[:70]}")
        if prompt.count('\n') > 15:
            print(f"  │ ... ({prompt.count(chr(10)) - 15}줄 더)")
        print(f"  └{'─' * 60}")

        print(f"\n  [네거티브] {negative[:100]}...")

        # ================================================================
        # SKILL 7: 이미지 생성 (Gemini)
        # ================================================================
        print("\n" + "-" * 50)
        print("🖼️ [SKILL 7] 이미지 생성 (Gemini)")
        print("-" * 50)
        print(f"  모델: gemini-3-pro-image-preview")
        print(f"  비율: 3:4")
        print(f"  모델 이미지: {len(model_images) if model_images else 0}장")
        print(f"  착장 이미지: {len(outfit_images) if outfit_images else 0}장")

        import time
        start_time = time.time()

        img = self.generate_single(
            prompt=prompt,
            negative_prompt=negative,
            model_images=model_images,
            outfit_images=outfit_images,
            outfit_description=outfit_description,
            background_image=background_image,
            model="gemini-3-pro-image-preview",
            aspect_ratio=aspect_ratio
        )

        elapsed = time.time() - start_time
        print(f"\n  [결과] {'성공' if img else '실패'} ({elapsed:.1f}초)")

        # 상세 정보 (로깅용)
        details = {
            "skills": {
                "1_brand_routing": {
                    "input": user_input,
                    "brand": brand,
                    "style": style
                },
                "2_brand_dna": {
                    "persona": brand_dna.get('_metadata', {}).get('persona', 'Unknown') if brand_dna else None,
                    "brand": brand_dna.get('_metadata', {}).get('brand', brand) if brand_dna else None,
                    "philosophy": brand_dna.get('identity', {}).get('philosophy', []) if brand_dna else []
                },
                "3_director_skill": {
                    "persona": director_directives.get('persona', 'Unknown'),
                    "style_keywords": director_directives.get('style_keywords', []),
                    "pose_guidelines_count": len(director_directives.get('pose_guidelines', [])),
                    "do_rules": director_directives.get('do_rules', []),
                    "dont_rules": director_directives.get('dont_rules', [])
                },
                "4_outfit_analysis": outfit_analysis,
                "5_director_vision": director_vision
            },
            "prompt": prompt,
            "negative_prompt": negative,
            "director_vision": director_vision.get('full_direction', '') if director_vision else '',
            "elapsed_seconds": elapsed
        }

        # 결과 반환
        return {
            "status": "success" if img else "error",
            "brand": brand,
            "style": style,
            "count": 1,
            "generated": 1 if img else 0,
            "images": [img] if img else [],
            "prompts": [prompt],
            "outfit_analysis": outfit_analysis,
            "director_vision": director_vision,
            "details": details,  # 상세 로깅용
            "error": None if img else "이미지 생성 실패"
        }


# 테스트용
if __name__ == "__main__":
    workflow = ImageGenerationWorkflow()
    print(workflow.route_brand("MLB 프리미엄 화보"))  # mlb-marketing
    print(workflow.route_brand("MLB 스트릿 그래픽"))  # mlb-graphic
    print(workflow.route_brand("Discovery 아웃도어"))  # discovery
    brand_dna = workflow.load_brand_dna("mlb-marketing")
    template = workflow.load_template("editorial")
    prompt = workflow.build_prompt(brand_dna, template, {"gender": "여성", "age": "20대 초반"})
    print(prompt)
