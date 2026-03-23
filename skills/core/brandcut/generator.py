"""
이미지 생성 모듈 - 순수 브랜드컷 생성만 담당

역할: 프롬프트 + 참조 이미지 → 이미지 생성
검증/재시도 로직은 retry_generator.py에서 처리
"""

import json
import time
from io import BytesIO
from typing import Optional, List, Union
from pathlib import Path

from PIL import Image
from google import genai
from google.genai import types

from core.config import IMAGE_MODEL


def pil_to_part(img: Image.Image, max_size: int = 1024) -> types.Part:
    """PIL Image를 Gemini Part로 변환"""
    if max(img.size) > max_size:
        img = img.copy()
        img.thumbnail((max_size, max_size), Image.LANCZOS)

    buffer = BytesIO()
    img.save(buffer, format="PNG")

    return types.Part(
        inline_data=types.Blob(mime_type="image/png", data=buffer.getvalue())
    )


def generate_brandcut(
    prompt_json: dict,
    face_images: List[Union[str, Path, Image.Image]],
    outfit_images: List[Union[str, Path, Image.Image]],
    pose_reference: Optional[Image.Image] = None,
    expression_reference: Optional[Image.Image] = None,  # ★ 표정 레퍼런스 추가
    style_reference: Optional[Image.Image] = None,
    auto_style_reference: bool = True,  # T6: 스타일 레퍼런스 자동 선택
    api_key: Optional[str] = None,
    num_images: int = 1,
    aspect_ratio: str = "auto",
    resolution: str = "1K",
    temperature: float = 0.25,
) -> Union[Optional[Image.Image], List[Optional[Image.Image]]]:
    """
    브랜드컷 이미지 생성 (단일 또는 배치)

    순수 생성만 담당. 검증/재시도는 retry_generator.py에서 처리.

    Args:
        prompt_json: 프롬프트 JSON 객체 (치트시트 기반)
        face_images: 얼굴 이미지 목록
        outfit_images: 착장 이미지 목록 (최우선)
        pose_reference: 포즈 레퍼런스 이미지 (선택)
        expression_reference: ★ 표정 레퍼런스 이미지 (선택) - K-뷰티 표정만 복사
        style_reference: 스타일 레퍼런스 이미지 (선택) - 무드/조명/분위기 복사
        auto_style_reference: 스타일 레퍼런스 자동 선택 여부 (T6)
        api_key: Gemini API 키
        num_images: 생성할 이미지 수량 (기본 1)
        aspect_ratio: 화면 비율 (기본 3:4)
        resolution: 해상도 (1K/2K/4K)
        temperature: 생성 온도 (기본 0.25)

    Returns:
        num_images == 1: PIL.Image (실패 시 None)
        num_images > 1: List[PIL.Image] (각 이미지, 실패 시 None 포함)
    """
    # ============================================================
    # T6: 스타일 레퍼런스 자동 선택
    # ============================================================
    if auto_style_reference and style_reference is None:
        try:
            from .style_selector import select_style_reference_image

            style_reference = select_style_reference_image(prompt_json, top_k=3)
            if style_reference:
                print(
                    "[Generator] Auto-selected style reference from MLB style library"
                )
        except Exception as e:
            # 스타일 인덱스 없어도 생성은 계속
            print(f"[Generator] Style reference auto-select skipped: {e}")

    # 배치 모드
    if num_images > 1:
        return _generate_batch(
            prompt_json=prompt_json,
            face_images=face_images,
            outfit_images=outfit_images,
            pose_reference=pose_reference,
            expression_reference=expression_reference,  # ★ 표정 레퍼런스 전달
            style_reference=style_reference,
            auto_style_reference=False,  # 이미 선택됨
            api_key=api_key,
            num_images=num_images,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            temperature=temperature,
        )

    # 단일 모드
    # API 키 처리
    if api_key is None:
        from core.api import _get_next_api_key

        api_key = _get_next_api_key()

    # 클라이언트 생성
    client = genai.Client(api_key=api_key)

    # 프롬프트 텍스트 (한국어 레이어 우선)
    if "_korean_prompt" in prompt_json:
        prompt_text = prompt_json["_korean_prompt"]
        # JSON도 함께 전송 (착장 정확도용)
        prompt_text += (
            f"\n\n[JSON Reference]\n{json.dumps(prompt_json, ensure_ascii=False)}"
        )
    else:
        prompt_text = json.dumps(prompt_json, ensure_ascii=False)

    # API 파트 구성 - 순서 중요!
    # 1. 포즈 레퍼런스 (최우선, 맨 앞에 배치)
    # 2. 프롬프트 텍스트
    # 3. 포즈 상세 정보
    # 4. 얼굴 이미지
    # 5. 착장 이미지

    parts = []

    # ============================================================
    # 1. 포즈 레퍼런스 (최우선 - 맨 앞에 배치!)
    # ============================================================
    if pose_reference is not None:
        parts.append(
            types.Part(
                text="""★★★★★ POSE REFERENCE - COPY THIS EXACTLY! ★★★★★

⚠️⚠️⚠️ THIS IMAGE IS THE MOST IMPORTANT INPUT! ⚠️⚠️⚠️

YOU MUST MATCH EXACTLY:

1. CAMERA ANGLE (카메라 앵글) - CRITICAL!
   - LOW ANGLE (로우앵글) = 아래에서 위로 올려다봄
   - EYE LEVEL (아이레벨) = 눈높이
   - HIGH ANGLE (하이앵글) = 위에서 아래로 내려다봄
   → IF REFERENCE IS LOW ANGLE, YOURS MUST BE LOW ANGLE!

2. FRAMING (구도) - CRITICAL!
   - FULL BODY (전신) = 머리부터 발끝까지
   - KNEE-UP (무릎위) = 머리부터 무릎까지
   - WAIST-UP (허리위) = 머리부터 허리까지
   → IF REFERENCE SHOWS FULL BODY, YOURS MUST SHOW FULL BODY!

3. LEG POSITION (다리) - CRITICAL!
   - SPREAD APART (벌림) = 다리를 넓게 벌림
   - TOGETHER (모음) = 다리를 모음
   - ONE BENT (한쪽 구부림) = 한쪽만 구부림
   → COPY THE EXACT LEG POSITION FROM REFERENCE!

❌ WRONG (이렇게 하면 REJECTED):
- Reference: LOW ANGLE → Generated: EYE LEVEL
- Reference: FULL BODY → Generated: HALF BODY
- Reference: LEGS SPREAD → Generated: LEGS TOGETHER

✅ RIGHT (이렇게 해야 함):
- Reference: LOW ANGLE → Generated: LOW ANGLE ✓
- Reference: FULL BODY → Generated: FULL BODY ✓
- Reference: LEGS SPREAD → Generated: LEGS SPREAD ✓

NOW STUDY THIS REFERENCE IMAGE:"""
            )
        )
        parts.append(pil_to_part(pose_reference))
        parts.append(
            types.Part(
                text="""
★★★ REMINDER: COPY THE ABOVE IMAGE'S ANGLE, FRAMING, AND LEG POSITION! ★★★
"""
            )
        )

    # ============================================================
    # 1.5. 표정 레퍼런스 (포즈 다음, 프롬프트 전)
    # ============================================================
    if expression_reference is not None:
        # 표정 세분화 정보 추출 (prompt_json에서)
        expression_info = prompt_json.get("표정", {})
        expression_prompt = expression_info.get("프롬프트", "")
        expression_preset = expression_info.get("프리셋", "")
        expression_intensity = expression_info.get("강도", 60)
        expression_keywords = expression_info.get("키워드", [])

        # 세분화된 표정 정보가 있으면 포함
        detailed_info = ""
        if expression_info.get("세분화"):
            detailed = expression_info["세분화"]
            eyes = detailed.get("eyes", {})
            mouth = detailed.get("mouth", {})
            chin = detailed.get("chin", {})

            detailed_info = f"""
## Detailed Expression Analysis:
- Eyes: {eyes.get('openness', 'natural')}, {eyes.get('eye_corner', 'neutral')} corners, {eyes.get('gaze_intensity', 'natural')} gaze
- Eye smile: {eyes.get('eye_smile', 'none')}
- Eyebrows: {eyes.get('eyebrows', 'natural')}
- Lips: {mouth.get('lip_state', 'closed')}, {mouth.get('mouth_corner', 'neutral')} corners
- Lip emphasis: {mouth.get('lip_emphasis', 'natural')}, {mouth.get('lip_tension', 'relaxed')} tension
- Chin: {chin.get('chin_position', 'neutral')}, {chin.get('jaw_tension', 'relaxed')} jaw
"""

        parts.append(
            types.Part(
                text=f"""★★★★★ EXPRESSION REFERENCE - COPY THIS EXPRESSION EXACTLY! ★★★★★

⚠️⚠️⚠️ THIS IMAGE DEFINES THE EXPRESSION/MOOD TO COPY! ⚠️⚠️⚠️

## K-Beauty Expression Style: {expression_preset if expression_preset else 'custom'}
## Expression Intensity: {expression_intensity}/100
## Mood Keywords: {', '.join(expression_keywords) if expression_keywords else 'cool, confident'}

FROM THIS REFERENCE IMAGE, YOU MUST COPY:

1. EYE EXPRESSION (눈 표현) - CRITICAL!
   - Eye openness (눈 크기): 크게 뜸 / 반쯤 감음 / 나른하게
   - Eye corner angle (눈꼬리): 올라감 / 내려감 / 중립
   - Gaze intensity (눈빛 강도): 강렬 / 부드러움 / 몽환적
   - Eye smile (눈웃음): 있음 / 없음

2. MOUTH EXPRESSION (입 표현) - CRITICAL!
   - Lip state (입 상태): 다문 / 살짝 벌림 / 파우팅
   - Mouth corner angle (입꼬리): 올라감 / 내려감 / 중립
   - Lip emphasis (입술 강조): 도톰하게 / 자연스럽게

3. CHIN/JAW ANGLE (턱 각도)
   - Chin position (턱 위치): 들어올림 / 중립 / 숙임
{detailed_info}
{f'## Expression Prompt: {expression_prompt}' if expression_prompt else ''}

★★★ DO NOT COPY FROM THIS IMAGE ★★★
- Face identity (얼굴 특징) → use FACE REFERENCE instead
- Makeup details
- Hair style
- Outfit

NOW STUDY THIS EXPRESSION REFERENCE:"""
            )
        )
        parts.append(pil_to_part(expression_reference))
        parts.append(
            types.Part(
                text="""
★★★ REMINDER: MATCH THE EXACT EXPRESSION MOOD, INTENSITY, AND MICRO-EXPRESSIONS! ★★★
- If reference has half-lidded eyes → YOUR eyes must be half-lidded
- If reference has chin raised → YOUR chin must be raised
- If reference has lips parted → YOUR lips must be parted
"""
            )
        )

    # ============================================================
    # 2. 프롬프트 텍스트
    # ============================================================
    parts.append(types.Part(text=prompt_text))

    # ============================================================
    # 2.5. 스타일 레퍼런스 (프롬프트 다음, 얼굴 이미지 전)
    #      인플루언서 패턴: prompt -> style -> face -> outfit
    # ============================================================
    if style_reference is not None:
        # T6: 강화된 스타일 레퍼런스 지시문 (MLB 스타일 DNA 반영)
        parts.append(
            types.Part(
                text="""[STYLE REFERENCE] - MLB Brand Editorial Style:

★★★ COPY FROM THIS IMAGE ★★★
- Overall mood and atmosphere (languid, cool, unbothered)
- Skin texture and finish (glossy, dewy, highlighted)
- Expression vibe (slightly parted lips, hooded eyes, intense gaze)
- Accessory styling (hoop earrings, chain necklace if present)
- Editorial fashion photography feel
- Body language and confidence level
- "Young & Rich" languid chic aesthetic - bored rich kid energy

★★★ DO NOT COPY ★★★
- Face (use FACE REFERENCE instead)
- Outfit/clothing (use OUTFIT REFERENCE instead)
- Exact pose (use POSE REFERENCE if provided)
- Background

MATCH the premium street vibe and fashion magazine aesthetic.
Capture the languid chic energy - confident but unbothered."""
            )
        )
        parts.append(pil_to_part(style_reference))

    # 포즈/촬영/표정 정보를 별도로 강조 (JSON에서 추출)
    pose_info = prompt_json.get("포즈", {})
    camera_info = prompt_json.get("촬영", {})
    expr_info = prompt_json.get("표정", {})

    if pose_info or camera_info or expr_info:
        # ★ 세분화된 표정 정보 처리
        expression_section = f"""
## 표정 (EXPRESSION) - 레퍼런스와 동일하게!
- 베이스무드: {expr_info.get("베이스", "cool")}
- 바이브: {expr_info.get("바이브", "mysterious")}
- 시선: {expr_info.get("시선", "direct")}
- 입: {expr_info.get("입", "closed")}
- 눈: {expr_info.get("눈", "natural")}
- 눈썹: {expr_info.get("눈썹", "natural")}"""

        # 세분화 표정 데이터가 있으면 상세 정보 추가
        if expr_info.get("세분화"):
            detailed = expr_info["세분화"]
            eyes = detailed.get("eyes", {})
            mouth = detailed.get("mouth", {})
            chin = detailed.get("chin", {})

            expression_section += f"""

### ★★★ K-BEAUTY DETAILED EXPRESSION ★★★
- 프리셋: {expr_info.get("프리셋", "natural")}
- 표정 강도: {expr_info.get("강도", 60)}/100
- 무드 키워드: {', '.join(expr_info.get("키워드", []))}

#### 눈 (Eyes) - 상세:
- 눈 크기: {eyes.get('openness', 'natural')} (wide_open/natural/half_lidded/slightly_closed)
- 눈꼬리 방향: {eyes.get('eye_corner', 'neutral')} (upturned/neutral/downturned)
- 눈빛 강도: {eyes.get('gaze_intensity', 'soft_gentle')}
- 눈웃음: {eyes.get('eye_smile', 'none')} (none/slight/full)
- 눈썹: {eyes.get('eyebrows', 'natural_relaxed')}

#### 입 (Mouth) - 상세:
- 입 상태: {mouth.get('lip_state', 'closed_neutral')}
- 입꼬리 각도: {mouth.get('mouth_corner', 'neutral')} (upturned/neutral/downturned)
- 입술 강조: {mouth.get('lip_emphasis', 'natural')}
- 입 긴장도: {mouth.get('lip_tension', 'relaxed')}

#### 턱/얼굴 (Chin/Face):
- 턱 위치: {chin.get('chin_position', 'neutral')} (raised/neutral/lowered)
- 턱 긴장도: {chin.get('jaw_tension', 'relaxed')}"""

            # 프롬프트가 있으면 추가
            if expr_info.get("프롬프트"):
                expression_section += f"""

#### 표정 프롬프트:
{expr_info.get("프롬프트")}"""

        pose_emphasis = f"""
[★★★ POSE/CAMERA/EXPRESSION DETAILS - MUST FOLLOW EXACTLY ★★★]

## 촬영 (CAMERA) - 반드시 따라하세요!
- 높이/앵글: {camera_info.get("높이", "눈높이")}
- 프레이밍: {camera_info.get("프레이밍", "MS")}

## 포즈 (POSE) - 각 부위별로 정확히 따라하세요!
- 기본자세(stance): {pose_info.get("stance", "stand")}
- 체중분배: {pose_info.get("체중분배", "균등")}
- 몸방향: {pose_info.get("몸방향", "정면")}
- 왼팔: {pose_info.get("왼팔", "natural")}
- 오른팔: {pose_info.get("오른팔", "relaxed")}
- 왼손: {pose_info.get("왼손", "relaxed")}
- 오른손: {pose_info.get("오른손", "relaxed")}
- 왼다리: {pose_info.get("왼다리", "support")}
- 오른다리: {pose_info.get("오른다리", "knee_10")}
- 다리간격: {pose_info.get("다리간격", "어깨너비")}
- 어깨: {pose_info.get("어깨", "수평")}
- 상체: {pose_info.get("상체", "똑바로")}
- 머리: {pose_info.get("머리", "정면")}
- 힙: {pose_info.get("힙", "neutral")}
{expression_section}

⚠️ 위 정보와 다르게 생성하면 REJECTED됩니다!
"""
        parts.append(types.Part(text=pose_emphasis))

    # ============================================================
    # 3. 착장 정보 강조 (prompt_json에서 동적 추출)
    # ============================================================
    outfit_info = prompt_json.get("착장", {})
    if outfit_info:
        # 프롬프트가 있는 아이템만 추출
        outfit_lines = []
        for category, data in outfit_info.items():
            if isinstance(data, dict) and data.get("프롬프트"):
                outfit_lines.append(f"- {category}: {data['프롬프트']}")

        if outfit_lines:
            outfit_emphasis = f"""
[★★★ OUTFIT DETAILS - MUST MATCH EXACTLY ★★★]

## 착장 아이템 (반드시 모두 포함!)
{chr(10).join(outfit_lines)}

⚠️ CRITICAL OUTFIT RULES:
1. EVERY item above MUST appear in the generated image
2. COLORS must match exactly (e.g., "brown with cream" = brown + cream)
3. LOGOS and PATTERNS must be preserved
4. FIT must match (oversized, cropped, wide, etc.)
5. STYLING must match (off-shoulder, worn normally, etc.)

❌ WRONG: Missing any item, wrong color, missing logo
✅ RIGHT: All items visible with correct colors and details
"""
            parts.append(types.Part(text=outfit_emphasis))

    # 얼굴 이미지 전체 전송
    for i, img_input in enumerate(face_images):
        if isinstance(img_input, (str, Path)):
            img = Image.open(img_input).convert("RGB")
        else:
            img = img_input.convert("RGB") if img_input.mode != "RGB" else img_input

        parts.append(
            types.Part(
                text=f"""
[CRITICAL] [FACE REFERENCE {i+1}] - COPY THIS FACE EXACTLY! [CRITICAL]

[!][!][!] THIS PERSON'S FACE MUST BE PRESERVED 100% [!][!][!]

YOU MUST MATCH:
- Eye shape (double eyelid, eye size, eye corners)
- Nose (bridge, tip, nostrils)
- Lips (thickness, philtrum)
- Jawline (chin line)
- Cheekbones (prominence)

[X] WRONG: Different person's face
[OK] RIGHT: 100% same person, recognizable immediately

FACE IDENTITY FAILURE = AUTOMATIC REJECTION
"""
            )
        )
        parts.append(pil_to_part(img))

    # ============================================================
    # 착장 이미지 전체 전송 - 아이템별 상세 지시 포함
    # ============================================================

    # 착장 상세 정보 추출 (prompt_json에서)
    outfit_details = prompt_json.get("착장", {})
    headwear_info = outfit_details.get("헤드웨어", {}).get("프롬프트", "")
    outer_info = outfit_details.get("아우터", {}).get("프롬프트", "")
    top_info = outfit_details.get("상의", {}).get("프롬프트", "")
    bottom_info = outfit_details.get("하의", {}).get("프롬프트", "")
    bag_info = outfit_details.get("가방", {}).get("프롬프트", "")

    # 헤드웨어 특별 강조 (NO BRIM, 로고 위치 등)
    if headwear_info:
        headwear_critical = f"""
★★★★★ HEADWEAR (BEANIE) - CRITICAL REQUIREMENTS ★★★★★

{headwear_info}

⚠️⚠️⚠️ ABSOLUTE REQUIREMENTS FOR BEANIE ⚠️⚠️⚠️

1. STRUCTURE:
   - IF prompt says "NO BRIM" → YOU MUST generate skull cap style WITHOUT ANY FOLD
   - [NEVER] add brim, visor, or fold-over cuff
   - [NEVER] add any rim or edge at the bottom

2. LOGO POSITION:
   - IF prompt says "front_right" → logo MUST be on the RIGHT SIDE of front
   - [NEVER] place logo in center
   - [NEVER] place logo on left side

3. TEXTURE:
   - IF prompt says "fuzzy" or "hairy" → MUST show visible fluffy/fuzzy fibers
   - [NEVER] make it smooth or flat knit

4. COLOR:
   - Match the EXACT color from prompt (charcoal ≠ black ≠ grey)

❌ COMMON MISTAKES TO AVOID:
- Adding a folded brim when "NO BRIM" is specified
- Putting logo in center when "front_right" is specified
- Making smooth texture when "fuzzy" is specified

✅ CORRECT:
- Skull cap with NO fold, logo on right, fuzzy texture visible
"""
        parts.append(types.Part(text=headwear_critical))

    # 전체 착장 요약
    outfit_summary = f"""
[★★★ ALL OUTFIT ITEMS - MUST REPRODUCE EXACTLY ★★★]

HEADWEAR: {headwear_info if headwear_info else 'N/A'}
OUTER: {outer_info if outer_info else 'N/A'}
TOP: {top_info if top_info else 'N/A'}
BOTTOM: {bottom_info if bottom_info else 'N/A'}
BAG: {bag_info if bag_info else 'N/A'}

NOW STUDY EACH OUTFIT IMAGE BELOW AND COPY EVERY DETAIL:
"""
    parts.append(types.Part(text=outfit_summary))

    # 착장 이미지 전송
    for i, img_input in enumerate(outfit_images):
        if isinstance(img_input, (str, Path)):
            img = Image.open(img_input).convert("RGB")
        else:
            img = img_input.convert("RGB") if img_input.mode != "RGB" else img_input

        parts.append(
            types.Part(
                text=f"[OUTFIT REFERENCE {i+1}] - Copy every detail from this image:"
            )
        )
        parts.append(pil_to_part(img))

    # 최대 3회 재시도 (API 에러용)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=IMAGE_MODEL,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    response_modalities=["IMAGE", "TEXT"],
                    image_config=types.ImageConfig(
                        aspect_ratio=aspect_ratio, image_size=resolution
                    ),
                ),
            )

            # 이미지 추출
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    return Image.open(BytesIO(part.inline_data.data))

            print("[Generator] No image in response")
            return None

        except Exception as e:
            error_str = str(e).lower()

            # 재시도 가능 에러 판별
            is_retryable = (
                "429" in error_str
                or "rate" in error_str
                or "503" in error_str
                or "overload" in error_str
                or "timeout" in error_str
            )

            if not is_retryable:
                print(f"[Generator] Error: {e}")
                return None

            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(
                    f"[Generator] Retry {attempt + 1}/{max_retries} - waiting {wait_time}s"
                )
                time.sleep(wait_time)
            else:
                print(f"[Generator] Max retries exceeded: {e}")

    return None


def _generate_batch(
    prompt_json: dict,
    face_images: List[Union[str, Path, Image.Image]],
    outfit_images: List[Union[str, Path, Image.Image]],
    pose_reference: Optional[Image.Image],
    expression_reference: Optional[Image.Image],  # ★ 표정 레퍼런스 추가
    style_reference: Optional[Image.Image],
    auto_style_reference: bool,
    api_key: Optional[str],
    num_images: int,
    aspect_ratio: str,
    resolution: str,
    temperature: float,
) -> List[Optional[Image.Image]]:
    """
    배치 이미지 생성 (순수 생성만, 검증 없음)

    Args:
        num_images: 생성할 이미지 수량

    Returns:
        List[PIL.Image]: 생성된 이미지 목록 (실패한 이미지는 None)
    """
    print(f"\n[Generator] Batch: {num_images} images | {aspect_ratio} | {resolution}")

    images = []
    for i in range(num_images):
        print(f"[Generator] Generating {i + 1}/{num_images}...")

        # 단일 이미지 생성 (재귀 호출)
        img = generate_brandcut(
            prompt_json=prompt_json,
            face_images=face_images,
            outfit_images=outfit_images,
            pose_reference=pose_reference,
            expression_reference=expression_reference,  # ★ 표정 레퍼런스 전달
            style_reference=style_reference,
            auto_style_reference=auto_style_reference,  # 이미 False로 전달됨
            api_key=api_key,
            num_images=1,  # 단일 모드로 호출
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            temperature=temperature,
        )
        images.append(img)

        if img:
            print(f"[Generator] {i + 1}/{num_images} OK")
        else:
            print(f"[Generator] {i + 1}/{num_images} FAILED")

        # Rate limit 방지 (마지막 제외)
        if i < num_images - 1:
            time.sleep(1)

    success = sum(1 for img in images if img is not None)
    print(f"[Generator] Batch complete: {success}/{num_images} success")

    return images
