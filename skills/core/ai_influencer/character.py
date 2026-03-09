"""
AI 인플루언서 캐릭터 관리 모듈

캐릭터 폴더에서 프로필과 얼굴 이미지를 로드
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# 캐릭터 데이터 기본 경로
CHARACTER_BASE_PATH = Path(__file__).parent.parent.parent / "db" / "ai_influencer"


@dataclass
class FaceFeatures:
    """얼굴 특징"""

    face_shape: str = ""
    eyes: str = ""
    nose: str = ""
    lips: str = ""
    skin: str = ""

    def to_prompt_text(self) -> str:
        """프롬프트용 텍스트 생성"""
        parts = []
        if self.face_shape:
            parts.append(f"얼굴형: {self.face_shape}")
        if self.eyes:
            parts.append(f"눈: {self.eyes}")
        if self.nose:
            parts.append(f"코: {self.nose}")
        if self.lips:
            parts.append(f"입술: {self.lips}")
        if self.skin:
            parts.append(f"피부: {self.skin}")
        return "\n".join(parts)


@dataclass
class StylePreferences:
    """스타일 선호도"""

    brand_affinity: List[str] = field(default_factory=list)
    preferred_colors: List[str] = field(default_factory=list)
    makeup_style: str = "natural"


@dataclass
class Character:
    """AI 인플루언서 캐릭터"""

    name: str
    name_en: str
    gender: str
    age: str
    ethnicity: str
    face_features: FaceFeatures
    style: StylePreferences
    personality: str
    face_images: List[Path]  # 얼굴 이미지 경로들
    folder_path: Path  # 캐릭터 폴더 경로
    style_guide: Optional[str] = None  # 스타일 가이드 텍스트

    def get_face_prompt(self) -> str:
        """얼굴 동일성 강화용 프롬프트 생성"""
        text = f"""★★★ 얼굴 동일성 최우선 ★★★
이 사람의 얼굴 특징을 정확히 재현하세요:
{self.face_features.to_prompt_text()}

다른 사람처럼 보이면 실패입니다!"""
        return text

    def get_model_info(self) -> Dict:
        """스키마의 '모델' 섹션용 정보"""
        return {
            "국적": self.ethnicity,
            "성별": self.gender,
            "나이": self.age,
        }

    def __repr__(self) -> str:
        return f"Character(name='{self.name}', face_images={len(self.face_images)}장)"


def list_characters(base_path: Path = None) -> List[str]:
    """
    등록된 캐릭터 목록 반환

    Args:
        base_path: 캐릭터 데이터 기본 경로 (기본값: db/ai_influencer/)

    Returns:
        캐릭터 이름(폴더명) 목록
    """
    if base_path is None:
        base_path = CHARACTER_BASE_PATH

    if not base_path.exists():
        return []

    characters = []
    for folder in base_path.iterdir():
        if folder.is_dir() and (folder / "profile.json").exists():
            characters.append(folder.name)

    return sorted(characters)


def load_character(name: str, base_path: Path = None) -> Character:
    """
    캐릭터 로드

    Args:
        name: 캐릭터 이름 (폴더명)
        base_path: 캐릭터 데이터 기본 경로

    Returns:
        Character 객체

    Raises:
        FileNotFoundError: 캐릭터 폴더 또는 profile.json이 없을 때
        ValueError: profile.json 파싱 실패
    """
    if base_path is None:
        base_path = CHARACTER_BASE_PATH

    folder_path = base_path / name

    # 폴더 확인
    if not folder_path.exists():
        raise FileNotFoundError(f"캐릭터 폴더 없음: {folder_path}")

    # profile.json 로드
    profile_path = folder_path / "profile.json"
    if not profile_path.exists():
        raise FileNotFoundError(f"profile.json 없음: {profile_path}")

    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            profile = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"profile.json 파싱 실패: {e}")

    # 얼굴 이미지 로드
    face_folder = folder_path / "face"
    face_images = []
    if face_folder.exists():
        for ext in ["*.jpg", "*.jpeg", "*.png"]:
            face_images.extend(face_folder.glob(ext))
        face_images = sorted(face_images)

    if len(face_images) < 1:
        raise ValueError(f"얼굴 이미지 없음: {face_folder}")

    # 스타일 가이드 로드 (선택적)
    style_guide = None
    style_guide_path = folder_path / "style_guide.md"
    if style_guide_path.exists():
        with open(style_guide_path, "r", encoding="utf-8") as f:
            style_guide = f.read()

    # FaceFeatures 파싱
    face_data = profile.get("face_features", {})
    face_features = FaceFeatures(
        face_shape=face_data.get("face_shape", ""),
        eyes=face_data.get("eyes", ""),
        nose=face_data.get("nose", ""),
        lips=face_data.get("lips", ""),
        skin=face_data.get("skin", ""),
    )

    # StylePreferences 파싱
    style_data = profile.get("style", {})
    style_prefs = StylePreferences(
        brand_affinity=style_data.get("brand_affinity", []),
        preferred_colors=style_data.get("preferred_colors", []),
        makeup_style=style_data.get("makeup_style", "natural"),
    )

    # Character 생성
    character = Character(
        name=profile.get("name", name),
        name_en=profile.get("name_en", name),
        gender=profile.get("gender", "여성"),
        age=profile.get("age", "20대 초반"),
        ethnicity=profile.get("ethnicity", "한국인"),
        face_features=face_features,
        style=style_prefs,
        personality=profile.get("personality", ""),
        face_images=face_images,
        folder_path=folder_path,
        style_guide=style_guide,
    )

    return character


def create_character_template(name: str, base_path: Path = None) -> Path:
    """
    새 캐릭터 템플릿 생성

    Args:
        name: 캐릭터 이름 (폴더명)
        base_path: 캐릭터 데이터 기본 경로

    Returns:
        생성된 폴더 경로
    """
    if base_path is None:
        base_path = CHARACTER_BASE_PATH

    folder_path = base_path / name
    folder_path.mkdir(parents=True, exist_ok=True)

    # face 폴더 생성
    face_folder = folder_path / "face"
    face_folder.mkdir(exist_ok=True)

    # profile.json 템플릿 생성
    profile_template = {
        "name": name,
        "name_en": name,
        "gender": "여성",
        "age": "20대 초반",
        "ethnicity": "한국인",
        "face_features": {
            "face_shape": "계란형",
            "eyes": "크고 또렷한 눈",
            "nose": "높은 콧대",
            "lips": "도톰한 입술",
            "skin": "맑은 피부톤",
        },
        "style": {
            "brand_affinity": ["MLB", "스트릿"],
            "preferred_colors": ["블랙", "화이트"],
            "makeup_style": "natural",
        },
        "personality": "밝고 친근한 인플루언서",
    }

    profile_path = folder_path / "profile.json"
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile_template, f, ensure_ascii=False, indent=2)

    # style_guide.md 템플릿
    style_guide = """# 스타일 가이드

## 선호 스타일
- 캐주얼 스트릿
- MLB 브랜드

## 피해야 할 스타일
- 너무 포멀한 스타일
- 과한 액세서리

## 참고 사항
- 얼굴 이미지는 face/ 폴더에 최소 3장 추가
- front.jpg (정면), side.jpg (측면), smile.jpg (미소) 권장
"""
    style_guide_path = folder_path / "style_guide.md"
    with open(style_guide_path, "w", encoding="utf-8") as f:
        f.write(style_guide)

    print(f"[Character] 템플릿 생성: {folder_path}")
    print(f"  - profile.json 수정 필요")
    print(f"  - face/ 폴더에 얼굴 이미지 추가 필요 (최소 3장)")

    return folder_path
