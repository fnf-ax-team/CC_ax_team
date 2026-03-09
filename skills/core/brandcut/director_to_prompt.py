"""
director_to_prompt.py

director_analysis JSON을 프롬프트 문자열로 변환하는 모듈.
A급 이미지의 촬영 정보를 Gemini가 이해할 수 있는 텍스트로 변환.
"""

from typing import Optional
import json
from pathlib import Path


def get_angle_description(height_cm: float) -> str:
    """카메라 높이를 앵글 설명으로 변환"""
    if height_cm < 30:
        return "extreme low angle (shot from ground level)"
    elif height_cm < 50:
        return "low angle (shot from below eye level)"
    elif height_cm < 100:
        return "slightly low angle"
    elif height_cm < 150:
        return "eye level"
    elif height_cm < 180:
        return "slightly high angle"
    else:
        return "high angle (shot from above)"


def get_tilt_description(tilt_deg: float) -> str:
    """틸트 각도를 설명으로 변환"""
    if tilt_deg < -5:
        return f"tilted {abs(tilt_deg)} degrees downward (looking down)"
    elif tilt_deg < -1:
        return f"tilted slightly downward ({abs(tilt_deg)} degrees)"
    elif tilt_deg > 5:
        return f"tilted {tilt_deg} degrees upward (looking up)"
    elif tilt_deg > 1:
        return f"tilted slightly upward ({tilt_deg} degrees)"
    else:
        return "level (no tilt)"


def convert_camera_to_prompt(camera: dict) -> str:
    """
    카메라 JSON -> 프롬프트 문자열 변환

    Input:
    {
        "camera_height_cm": 5,
        "tilt_deg": -2,
        "lens_mm": "85",
        "aperture": "f/2.0",
        "camera_distance_m": 3
    }

    Output:
    "shot from 5cm height (extreme low angle), camera tilted -2 degrees,
     85mm lens f/2.0 aperture, shallow depth of field"
    """
    height = camera.get("camera_height_cm", 100)
    tilt = camera.get("tilt_deg", 0)
    lens = camera.get("lens_mm", "50")
    aperture = camera.get("aperture", "f/2.8")
    distance = camera.get("camera_distance_m", 3)

    angle_desc = get_angle_description(height)
    tilt_desc = get_tilt_description(tilt)

    parts = [
        f"Shot from {height}cm height ({angle_desc})",
        f"camera {tilt_desc}",
        f"{lens}mm lens at {aperture} aperture",
        f"camera {distance}m away from subject",
        "shallow depth of field with soft background blur",
    ]

    return ", ".join(parts) + "."


def convert_pose_to_prompt(pose: dict) -> str:
    """
    포즈 JSON -> 프롬프트 문자열 변환

    Input:
    {
        "overall_pose_category": "confident_standing",
        "weight_distribution": "left 55%, right 45%",
        "torso_rotation_deg": -5,
        "shoulder_tilt_deg": -2,
        "head_tilt_deg": -3,
        "chin_angle_deg": 3,
        "left_arm_position": "hand on hip",
        "right_arm_position": "holding bag strap",
        "stance_width_cm": 20,
        "pose_energy_level": 3
    }
    """
    category = pose.get("overall_pose_category", "confident_standing")
    weight = pose.get("weight_distribution", "centered")
    torso_rot = pose.get("torso_rotation_deg", 0)
    shoulder_tilt = pose.get("shoulder_tilt_deg", 0)
    head_tilt = pose.get("head_tilt_deg", 0)
    chin = pose.get("chin_angle_deg", 0)
    left_arm = pose.get("left_arm_position", "relaxed at side")
    right_arm = pose.get("right_arm_position", "relaxed at side")
    stance = pose.get("stance_width_cm", 20)
    energy = pose.get("pose_energy_level", 3)

    # 포즈 카테고리 설명
    category_desc = {
        "confident_standing": "confident standing pose with natural weight shift",
        "relaxed_lean": "casually leaning against a surface",
        "seated": "seated pose with relaxed posture",
        "walking": "mid-stride walking pose",
        "dynamic": "dynamic action pose",
    }.get(category, "natural standing pose")

    parts = [
        f"{category_desc}",
        f"weight distribution {weight}" if weight != "centered" else None,
        f"torso rotated {torso_rot} degrees" if abs(torso_rot) > 2 else None,
        f"shoulders tilted {shoulder_tilt} degrees" if abs(shoulder_tilt) > 1 else None,
        f"head tilted {head_tilt} degrees to the side" if abs(head_tilt) > 1 else None,
        f"chin angled {chin} degrees" if abs(chin) > 2 else None,
        f"left arm: {left_arm}",
        f"right arm: {right_arm}",
        f"stance width approximately {stance}cm",
    ]

    # None 제거
    parts = [p for p in parts if p]

    # 에너지 레벨 추가
    if energy <= 3:
        parts.append("calm and composed energy")
    elif energy <= 5:
        parts.append("moderate dynamic energy")
    else:
        parts.append("high energy and movement")

    return ". ".join(parts) + "."


def convert_expression_to_prompt(expression: dict) -> str:
    """
    표정 JSON -> 프롬프트 문자열 변환

    Input:
    {
        "overall_expression": "cool",
        "mouth_state": "closed_neutral",
        "mouth_corner_angle_deg": 2,
        "eye_openness_percent": 85,
        "gaze_direction_horizontal_deg": 0,
        "gaze_direction_vertical_deg": -2,
        "eyebrow_position": "relaxed",
        "expression_intensity": 4,
        "attractiveness_vibe": "mysterious"
    }
    """
    overall = expression.get("overall_expression", "neutral")
    mouth = expression.get("mouth_state", "closed_neutral")
    corner = expression.get("mouth_corner_angle_deg", 0)
    eye_open = expression.get("eye_openness_percent", 80)
    gaze_h = expression.get("gaze_direction_horizontal_deg", 0)
    gaze_v = expression.get("gaze_direction_vertical_deg", 0)
    eyebrow = expression.get("eyebrow_position", "relaxed")
    intensity = expression.get("expression_intensity", 5)
    vibe = expression.get("attractiveness_vibe", "natural")

    # 표정 기본 설명
    expression_base = {
        "cool": "cool and confident expression",
        "natural_smile": "natural subtle smile",
        "dreamy": "dreamy soft expression",
        "neutral": "neutral relaxed expression",
        "serious": "serious focused expression",
        "playful": "playful lighthearted expression",
    }.get(overall, "natural expression")

    # 입 상태
    mouth_desc = {
        "closed_neutral": "lips gently closed",
        "closed_smile": "closed-lip subtle smile",
        "parted": "lips slightly parted",
        "parted_slight": "lips barely parted",
        "wide_smile": "wide genuine smile",
    }.get(mouth, "natural mouth position")

    # 입꼬리
    if corner > 2:
        corner_desc = f"mouth corners slightly raised ({corner} degrees)"
    elif corner < -2:
        corner_desc = f"mouth corners slightly lowered ({abs(corner)} degrees)"
    else:
        corner_desc = None

    # 눈 크기
    if eye_open >= 85:
        eye_desc = f"eyes wide open ({eye_open}% openness), alert and engaging"
    elif eye_open >= 75:
        eye_desc = f"eyes naturally open ({eye_open}% openness)"
    elif eye_open >= 60:
        eye_desc = f"eyes slightly narrowed ({eye_open}% openness), sultry look"
    else:
        eye_desc = f"eyes relaxed and dreamy ({eye_open}% openness)"

    # 시선
    if abs(gaze_h) < 3 and abs(gaze_v) < 3:
        gaze_desc = "direct gaze into camera"
    else:
        h_dir = "to the right" if gaze_h > 0 else "to the left" if gaze_h < 0 else ""
        v_dir = "upward" if gaze_v > 0 else "downward" if gaze_v < 0 else ""
        gaze_desc = f"gaze {h_dir} {v_dir}".strip() if h_dir or v_dir else "direct gaze"

    parts = [
        expression_base,
        mouth_desc,
        corner_desc,
        eye_desc,
        gaze_desc,
        f"{eyebrow} eyebrows",
        f"expression intensity {intensity}/10",
        f"{vibe} vibe",
    ]

    parts = [p for p in parts if p]
    return ". ".join(parts) + "."


def convert_composition_to_prompt(composition: dict) -> str:
    """
    구도 JSON -> 프롬프트 문자열 변환
    """
    framing = composition.get("framing_type", "MS")
    headroom = composition.get("headroom_percent", 10)
    dof = composition.get("depth_of_field", "shallow")
    blur = composition.get("background_blur_percent", 70)

    framing_desc = {
        "ECU": "extreme close-up on face",
        "CU": "close-up shot (face and shoulders)",
        "MCU": "medium close-up (chest up)",
        "MS": "medium shot (waist up)",
        "MFS": "medium full shot (knees up)",
        "FS": "full shot (entire body)",
        "EFS": "extreme full shot with environment",
    }.get(framing, "medium shot")

    parts = [
        framing_desc,
        f"{headroom}% headroom above subject",
        f"{dof} depth of field",
        f"background blurred approximately {blur}%",
    ]

    return ". ".join(parts) + "."


def convert_brand_vibe_to_prompt(brand_vibe: dict) -> str:
    """
    브랜드 바이브 JSON -> 프롬프트 문자열 변환
    """
    keywords = brand_vibe.get("mood_keywords", ["cool", "urban"])
    energy = brand_vibe.get("energy_level", 4)
    sophistication = brand_vibe.get("sophistication_level", 5)
    street = brand_vibe.get("street_cred_level", 6)

    mood_str = ", ".join(keywords)

    # 에너지 설명
    if energy <= 3:
        energy_desc = "calm and relaxed"
    elif energy <= 5:
        energy_desc = "moderately energetic"
    else:
        energy_desc = "dynamic and vibrant"

    parts = [
        f"Brand mood: {mood_str}",
        f"{energy_desc} energy",
        f"sophistication level {sophistication}/10",
        f"street credibility {street}/10",
    ]

    return ". ".join(parts) + "."


def director_to_full_prompt(
    director_json: dict,
    outfit_description: Optional[str] = None,
    face_description: Optional[str] = None,
    additional_instructions: Optional[str] = None,
) -> str:
    """
    director_analysis JSON 전체를 완전한 프롬프트로 변환

    Args:
        director_json: director_analysis JSON 데이터
        outfit_description: 착장 분석 결과 텍스트 (analyze_outfit 결과)
        face_description: 얼굴 설명 (선택)
        additional_instructions: 추가 지시 (선택)

    Returns:
        완전한 프롬프트 문자열
    """
    camera = director_json.get("camera", {})
    pose = director_json.get("pose", {})
    expression = director_json.get("expression", {})
    composition = director_json.get("composition", {})
    brand_vibe = director_json.get("brand_vibe", {})
    signature = director_json.get("signature", {})

    # 각 섹션 변환
    camera_prompt = convert_camera_to_prompt(camera)
    pose_prompt = convert_pose_to_prompt(pose)
    expression_prompt = convert_expression_to_prompt(expression)
    composition_prompt = convert_composition_to_prompt(composition)
    vibe_prompt = convert_brand_vibe_to_prompt(brand_vibe)

    # 시그니처 요소
    sig_pose = signature.get("signature_pose_element", "")
    sig_style = signature.get("signature_styling_element", "")
    sig_mood = signature.get("signature_mood_element", "")

    # 프롬프트 조립
    prompt_parts = [
        "Generate a high-fashion editorial photograph for MLB brand.",
        "",
        "=== CAMERA & ANGLE (CRITICAL - MUST FOLLOW) ===",
        camera_prompt,
        "",
        "=== POSE (MUST FOLLOW ANGLES PRECISELY) ===",
        pose_prompt,
        "",
        "=== EXPRESSION (MUST MATCH SPECIFICATIONS) ===",
        expression_prompt,
        "",
        "=== COMPOSITION ===",
        composition_prompt,
        "",
        "=== BRAND VIBE ===",
        vibe_prompt,
    ]

    # 시그니처 요소 추가
    if sig_pose or sig_style or sig_mood:
        prompt_parts.extend(
            [
                "",
                "=== SIGNATURE ELEMENTS ===",
                f"Key pose element: {sig_pose}" if sig_pose else None,
                f"Styling highlight: {sig_style}" if sig_style else None,
                f"Mood essence: {sig_mood}" if sig_mood else None,
            ]
        )

    # 착장 설명 추가 (CRITICAL)
    if outfit_description:
        prompt_parts.extend(
            [
                "",
                "=== OUTFIT (CRITICAL - MUST MATCH EXACTLY) ===",
                outfit_description,
                "IMPORTANT: The outfit details, colors, and logos MUST match the reference image exactly.",
            ]
        )

    # 얼굴 설명 추가
    if face_description:
        prompt_parts.extend(["", "=== FACE REFERENCE ===", face_description])

    # 추가 지시
    if additional_instructions:
        prompt_parts.extend(
            ["", "=== ADDITIONAL INSTRUCTIONS ===", additional_instructions]
        )

    # 세련됨 프롬프트 (A급 분석 기반 구체적 지시)
    from .sophistication_prompt import get_sophistication_summary

    prompt_parts.append("")
    prompt_parts.append(get_sophistication_summary())

    # 강조 지시
    prompt_parts.extend(
        [
            "",
            "=== CRITICAL REQUIREMENTS ===",
            "1. Camera angle MUST follow the specified height precisely",
            "2. ASYMMETRY: One shoulder lower, head tilted, weight shifted",
            "3. Expression: Alert eyes with slight squint, lips barely parted",
            "4. Color: 6000-6500K cool tone, 40-55% saturation",
            "5. Styling: Jacket off-shoulder or draped, cap low to eyebrows",
            "6. If outfit reference provided, clothing MUST match exactly",
            "7. AVOID: Flat lighting, symmetrical pose, forced smile, over-saturation",
        ]
    )

    # None 제거하고 조립
    prompt_parts = [p for p in prompt_parts if p is not None]
    return "\n".join(prompt_parts)


def load_director_json(json_path: str | Path) -> dict:
    """director_analysis JSON 파일 로드"""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


# 테스트용
if __name__ == "__main__":
    # 샘플 테스트
    sample_json = {
        "camera": {
            "camera_height_cm": 5,
            "tilt_deg": -2,
            "lens_mm": "85",
            "aperture": "f/2.0",
            "camera_distance_m": 3,
        },
        "pose": {
            "overall_pose_category": "confident_standing",
            "weight_distribution": "left 55%, right 45%",
            "torso_rotation_deg": -5,
            "shoulder_tilt_deg": -2,
            "head_tilt_deg": -3,
            "left_arm_position": "hand on hip",
            "right_arm_position": "holding jacket",
            "pose_energy_level": 3,
        },
        "expression": {
            "overall_expression": "cool",
            "mouth_state": "closed_neutral",
            "mouth_corner_angle_deg": 2,
            "eye_openness_percent": 85,
            "expression_intensity": 4,
            "attractiveness_vibe": "mysterious",
        },
        "composition": {
            "framing_type": "MS",
            "headroom_percent": 10,
            "depth_of_field": "shallow",
            "background_blur_percent": 70,
        },
        "brand_vibe": {
            "mood_keywords": ["cool", "urban", "chic"],
            "energy_level": 4,
            "sophistication_level": 6,
            "street_cred_level": 7,
        },
        "signature": {
            "signature_pose_element": "Off-shoulder jacket",
            "signature_mood_element": "Effortless cool",
        },
    }

    outfit_desc = """
    MLB branded varsity jacket in navy blue with white NY logo on chest.
    Black tank top underneath.
    Dark blue denim cargo pants with MLB patch on pocket.
    Black MLB cap with white logo.
    """

    prompt = director_to_full_prompt(sample_json, outfit_description=outfit_desc)
    print(prompt)
