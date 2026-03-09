"""
FNF Studio 테스트용 이미지 선택 유틸리티

워크플로 타입에 따라 db/ 폴더에서 적절한 이미지를 자동으로 선택합니다.
VLM 기반 착장 자동 분류 및 코디네이션 기능 포함.
"""

import logging
import random
import time
from enum import Enum
from pathlib import Path
from typing import Dict, List, Literal, Optional, TypedDict

from PIL import Image

# 기존 WorkflowType 사용 (새로 정의하지 않음!)
from core.validators import WorkflowType

logger = logging.getLogger(__name__)

# =============================================================================
# 상수 정의
# =============================================================================

# 프로젝트 루트 기준 db 폴더 경로
# core/test_agent/test_utils.py -> core/test_agent -> core -> project_root -> db
DB_ROOT = Path(__file__).resolve().parent.parent.parent / "db"

# 지원 이미지 확장자
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}

# API 이미지 제한
MAX_IMAGES = 14

# VLM Rate limit 방지용 딜레이 (초)
VLM_CALL_DELAY = 0.5


# =============================================================================
# 타입 정의
# =============================================================================


class ImageSet(TypedDict, total=False):
    """워크플로별 이미지 세트"""

    face: List[Path]
    outfit: List[Path]
    style_ref: List[Path]
    reference: List[Path]
    source: List[Path]
    background: List[Path]
    scene_ref: List[Path]
    ugc_style: List[Path]
    fabric_ref: List[Path]
    product: List[Path]


class OutfitCategory(str, Enum):
    """착장 카테고리 (VLM 분류용)"""

    OUTER = "outer"  # 아우터: 자켓, 코트, 점퍼, 가디건
    TOP = "top"  # 상의: 티셔츠, 블라우스, 셔츠, 니트
    BOTTOM = "bottom"  # 하의: 바지, 스커트, 청바지, 쇼츠
    SHOES = "shoes"  # 신발: 운동화, 부츠, 샌들, 슬리퍼
    HAT = "hat"  # 모자: 캡, 비니, 버킷햇, 볼캡
    ACCESSORY = "accessory"  # 악세사리: 가방, 선글라스, 목걸이
    ONEPIECE = "onepiece"  # 원피스/세트: 드레스, 점프수트
    UNKNOWN = "unknown"  # 분류 불가


# =============================================================================
# 폴더 매핑 정의
# =============================================================================

# 이미지 타입별 폴더 매핑
FOLDER_MAPPING: Dict[str, List[Path]] = {
    # 얼굴/모델 이미지
    "face": [
        DB_ROOT / "model" / "Discovery_고윤정",
        DB_ROOT / "model" / "Discovery_변우석",
        DB_ROOT / "model" / "MLB_KARINA",
        DB_ROOT / "model" / "인플깜찍걸",
    ],
    # 착장 이미지
    "outfit": [
        DB_ROOT / "착장용",
        DB_ROOT / "product" / "WEAR",
    ],
    # 스타일 레퍼런스 (브랜드컷용)
    "style_ref": [
        DB_ROOT / "mlb_style",
    ],
    # 레퍼런스 이미지 (reference_brandcut용)
    "reference": [
        DB_ROOT / "mlb_style",
        DB_ROOT / "marketing",
    ],
    # 배경 이미지 (수정됨: 배경 소스 폴더!)
    "background": [
        DB_ROOT / "260112_배경교체" / "배경 소스",  # 실제 배경 이미지
        DB_ROOT / "AX 배경참고_(베를린 인스피레이션) (2)",
    ],
    # 소스 이미지 (배경교체용 - 인물 포함 이미지)
    "source": [
        DB_ROOT / "260112_배경교체",  # 루트의 PNG 파일들
        DB_ROOT / "mlb_style",
    ],
    # UGC 스타일
    "ugc_style": [
        DB_ROOT / "marketing",
    ],
    # 원단 이미지
    "fabric_ref": [
        DB_ROOT / "fabric" / "fabric_swatch_only",
    ],
    # 제품 이미지
    "product": [
        DB_ROOT / "product" / "ACC",
        DB_ROOT / "product" / "BAG",
        DB_ROOT / "product" / "CAP",
        DB_ROOT / "product" / "SHOES",
    ],
    # 씬 레퍼런스 (셀피용)
    "scene_ref": [
        DB_ROOT / "marketing",
    ],
}

# 모델명 -> 폴더 매핑 (검색용)
MODEL_MAPPING: Dict[str, Path] = {
    # 한글
    "고윤정": DB_ROOT / "model" / "Discovery_고윤정",
    "변우석": DB_ROOT / "model" / "Discovery_변우석",
    "카리나": DB_ROOT / "model" / "MLB_KARINA",
    # 영문
    "koyunjung": DB_ROOT / "model" / "Discovery_고윤정",
    "byunwoosung": DB_ROOT / "model" / "Discovery_변우석",
    "karina": DB_ROOT / "model" / "MLB_KARINA",
}

# 워크플로별 필요 이미지 타입 (기존 WorkflowType enum 키 사용!)
WORKFLOW_REQUIREMENTS: Dict[WorkflowType, List[str]] = {
    WorkflowType.BRANDCUT: ["face", "outfit", "style_ref"],
    WorkflowType.REFERENCE_BRANDCUT: ["reference", "face", "outfit"],
    WorkflowType.BACKGROUND_SWAP: ["source", "background"],
    WorkflowType.SELFIE: ["face", "scene_ref"],
    WorkflowType.UGC: ["face", "outfit", "ugc_style"],
    WorkflowType.FABRIC_GENERATION: ["fabric_ref"],
    WorkflowType.PRODUCT_STYLED: ["product", "scene_ref"],
    WorkflowType.FACE_SWAP: ["face", "reference"],
    WorkflowType.MULTI_FACE_SWAP: ["face", "reference"],
    WorkflowType.POSE_CHANGE: ["face", "reference"],
    WorkflowType.POSE_COPY: ["face", "reference"],
    WorkflowType.OUTFIT_SWAP: ["face", "outfit", "reference"],
    WorkflowType.ECOMMERCE: ["face", "outfit"],
    WorkflowType.PRODUCT_DESIGN: ["product"],
    WorkflowType.SHOES_3D: ["product"],
}

# 워크플로별 기본 이미지 개수 (VLM 분류 실패 시 fallback)
DEFAULT_COUNTS: Dict[WorkflowType, Dict[str, int]] = {
    WorkflowType.BRANDCUT: {
        "face": 1,
        "outfit": 6,  # fallback 최대값 (VLM 자동 분류 우선!)
        "style_ref": 1,
    },
    WorkflowType.REFERENCE_BRANDCUT: {
        "reference": 1,
        "face": 1,
        "outfit": 6,
    },
    WorkflowType.BACKGROUND_SWAP: {
        "source": 1,
        "background": 1,
    },
    WorkflowType.SELFIE: {
        "face": 1,
        "scene_ref": 1,
    },
    WorkflowType.UGC: {
        "face": 1,
        "outfit": 5,
        "ugc_style": 1,
    },
    WorkflowType.FABRIC_GENERATION: {
        "fabric_ref": 3,
    },
    WorkflowType.PRODUCT_STYLED: {
        "product": 1,
        "scene_ref": 1,
    },
    WorkflowType.FACE_SWAP: {
        "face": 1,
        "reference": 1,
    },
    WorkflowType.MULTI_FACE_SWAP: {
        "face": 3,
        "reference": 1,
    },
    WorkflowType.POSE_CHANGE: {
        "face": 1,
        "reference": 1,
    },
    WorkflowType.POSE_COPY: {
        "face": 1,
        "reference": 1,
    },
    WorkflowType.OUTFIT_SWAP: {
        "face": 1,
        "outfit": 4,
        "reference": 1,
    },
    WorkflowType.ECOMMERCE: {
        "face": 1,
        "outfit": 5,
    },
    WorkflowType.PRODUCT_DESIGN: {
        "product": 2,
    },
    WorkflowType.SHOES_3D: {
        "product": 3,
    },
}


# VLM 분류 프롬프트
CLASSIFY_OUTFIT_PROMPT = """이 의류 이미지를 분류하세요.

카테고리 중 하나만 답하세요:
- outer (아우터: 자켓, 코트, 점퍼, 가디건, 패딩)
- top (상의: 티셔츠, 블라우스, 셔츠, 니트, 맨투맨)
- bottom (하의: 바지, 스커트, 청바지, 쇼츠, 슬랙스)
- shoes (신발: 운동화, 부츠, 샌들, 슬리퍼, 구두)
- hat (모자: 캡, 비니, 버킷햇, 볼캡, 베레모)
- accessory (악세서리: 가방, 선글라스, 목걸이, 시계, 벨트)
- onepiece (원피스/세트: 드레스, 점프수트, 세트업)

응답 형식 (정확히 이 형식만):
category: [카테고리명]

예시:
category: top
"""


# =============================================================================
# 핵심 함수
# =============================================================================


def list_images(
    folder: Path, extensions: set = IMAGE_EXTENSIONS, recursive: bool = False
) -> List[Path]:
    """폴더 내 이미지 파일 목록 반환

    Args:
        folder: 검색할 폴더 경로
        extensions: 허용할 확장자 세트
        recursive: True면 하위 폴더까지 재귀 탐색

    Returns:
        이미지 파일 경로 리스트
    """
    if not folder.exists():
        logger.warning(f"Folder not found: {folder}")
        return []

    if recursive:
        # 재귀 탐색
        images = [
            f
            for f in folder.rglob("*")
            if f.is_file() and f.suffix.lower() in extensions
        ]
    else:
        # 현재 폴더만
        images = [
            f
            for f in folder.iterdir()
            if f.is_file() and f.suffix.lower() in extensions
        ]

    if not images:
        logger.debug(f"No images found in: {folder}")

    return images


def select_images(
    image_type: str,
    count: int = 1,
    model_name: Optional[str] = None,
    random_select: bool = True,
    seed: Optional[int] = None,
    recursive: bool = False,
) -> List[Path]:
    """
    이미지 타입에 따라 이미지 선택.

    Args:
        image_type: 이미지 타입 (face, outfit, style_ref 등)
        count: 선택할 이미지 수
        model_name: 특정 모델 필터 (고윤정, karina 등)
        random_select: True면 랜덤 선택, False면 처음부터 순서대로
        seed: 랜덤 시드 (재현성 보장용)
        recursive: 하위 폴더까지 재귀 탐색 여부

    Returns:
        선택된 이미지 경로 리스트 (절대 경로)
    """
    if seed is not None:
        random.seed(seed)

    # 모델명 필터가 있으면 해당 폴더만 사용
    if model_name and image_type == "face":
        model_key = model_name.lower().replace(" ", "")
        if model_key in MODEL_MAPPING:
            folders = [MODEL_MAPPING[model_key]]
        else:
            # 부분 매칭 시도
            folders = [
                path for key, path in MODEL_MAPPING.items() if model_key in key.lower()
            ]
            if not folders:
                logger.warning(f"Model not found: {model_name}, using all face folders")
                folders = FOLDER_MAPPING.get(image_type, [])
    else:
        folders = FOLDER_MAPPING.get(image_type, [])

    if not folders:
        logger.warning(f"No folders mapped for image type: {image_type}")
        return []

    # 모든 이미지 수집
    all_images = []
    for folder in folders:
        all_images.extend(list_images(folder, recursive=recursive))

    if not all_images:
        logger.warning(f"No images found for type: {image_type}")
        return []

    # 요청 수량 > 가용 이미지 처리
    if count > len(all_images):
        logger.warning(
            f"Requested {count} images but only {len(all_images)} available "
            f"for type '{image_type}'. Returning all available."
        )
        count = len(all_images)

    # 선택
    if random_select:
        selected = random.sample(all_images, count)
    else:
        selected = all_images[:count]

    # 절대 경로로 반환
    return [p.resolve() for p in selected]


def get_model_list() -> List[str]:
    """사용 가능한 모델 목록 반환"""
    return list(MODEL_MAPPING.keys())


def get_image_count(image_type: str, recursive: bool = False) -> int:
    """해당 타입의 총 이미지 수 반환

    Args:
        image_type: 이미지 타입
        recursive: 하위 폴더 포함 여부

    Returns:
        이미지 총 개수
    """
    folders = FOLDER_MAPPING.get(image_type, [])
    total = 0
    for folder in folders:
        total += len(list_images(folder, recursive=recursive))
    return total


def validate_image_count(images: ImageSet, max_images: int = MAX_IMAGES) -> bool:
    """이미지 총 개수가 제한 이하인지 검증

    Args:
        images: 이미지 세트
        max_images: 최대 이미지 수 (기본 14)

    Returns:
        True if valid, False if exceeds limit
    """
    total = sum(len(paths) for paths in images.values())
    if total > max_images:
        logger.warning(
            f"Total images ({total}) exceeds API limit ({max_images}). "
            f"Distribution: {', '.join(f'{k}={len(v)}' for k, v in images.items())}"
        )
        return False
    logger.debug(f"Image count OK: {total}/{max_images}")
    return True


def get_default_counts(workflow: WorkflowType) -> Dict[str, int]:
    """워크플로별 기본 이미지 개수 반환

    Args:
        workflow: 워크플로 타입

    Returns:
        이미지 타입별 기본 개수 딕셔너리
    """
    return DEFAULT_COUNTS.get(workflow, {}).copy()


# =============================================================================
# VLM 착장 분류 함수
# =============================================================================


def classify_outfit(
    image_path: Path, client=None, api_key: Optional[str] = None
) -> OutfitCategory:
    """VLM으로 의류 이미지 카테고리 분류

    Args:
        image_path: 의류 이미지 경로
        client: Gemini 클라이언트 (없으면 새로 생성)
        api_key: API 키 (없으면 _get_next_api_key() 사용)

    Returns:
        OutfitCategory enum 값
    """
    from google import genai
    from google.genai import types
    from core.config import VISION_MODEL
    from core.api import _get_next_api_key
    from core.utils import pil_to_part

    # 클라이언트 생성
    if client is None:
        if api_key is None:
            api_key = _get_next_api_key()
        client = genai.Client(api_key=api_key)

    try:
        # PIL Image 로드 후 pil_to_part 사용
        pil_image = Image.open(str(image_path)).convert("RGB")
        image_part = pil_to_part(pil_image, max_size=512)

        # VLM 호출
        response = client.models.generate_content(
            model=VISION_MODEL,
            config=types.GenerateContentConfig(
                temperature=0.1,
            ),
            contents=[
                types.Content(
                    role="user",
                    parts=[image_part, types.Part(text=CLASSIFY_OUTFIT_PROMPT)],
                )
            ],
        )

        # 응답 파싱
        text = response.text.strip().lower()

        # "category: xxx" 형식 파싱
        if "category:" in text:
            category_str = text.split("category:")[-1].strip()
        else:
            category_str = text

        # enum 매핑
        for cat in OutfitCategory:
            if cat.value in category_str:
                return cat

        logger.warning(f"Unknown category for {image_path}: {text}")
        return OutfitCategory.UNKNOWN

    except Exception as e:
        logger.error(f"Failed to classify {image_path}: {e}")
        return OutfitCategory.UNKNOWN


def classify_outfit_batch(
    image_paths: List[Path],
    client=None,
    api_key: Optional[str] = None,
    delay: float = VLM_CALL_DELAY,
) -> Dict[Path, OutfitCategory]:
    """여러 이미지 일괄 분류 (Rate limit 고려)

    Args:
        image_paths: 이미지 경로 리스트
        client: Gemini 클라이언트
        api_key: API 키
        delay: 호출 간 딜레이 (기본 0.5초)

    Returns:
        {이미지 경로: 카테고리} 딕셔너리
    """
    from google import genai
    from core.api import _get_next_api_key

    if client is None:
        if api_key is None:
            api_key = _get_next_api_key()
        client = genai.Client(api_key=api_key)

    results = {}
    for i, path in enumerate(image_paths):
        results[path] = classify_outfit(path, client=client)

        # Rate limit 방지: 마지막 아이템이 아니면 딜레이
        if i < len(image_paths) - 1 and delay > 0:
            time.sleep(delay)

    return results


def classify_outfit_batch_fallback(
    image_paths: List[Path], max_count: int = 6
) -> List[Path]:
    """VLM 분류 실패 시 fallback: 랜덤 N개 선택

    Args:
        image_paths: 이미지 경로 리스트
        max_count: 최대 선택 개수 (기본 6)

    Returns:
        랜덤 선택된 이미지 경로 리스트
    """
    if len(image_paths) <= max_count:
        return list(image_paths)
    return random.sample(list(image_paths), max_count)


def auto_coordinate(
    outfit_folder: Path,
    include_outer: bool = True,
    include_hat: bool = True,
    include_accessory: bool = False,
    client=None,
    api_key: Optional[str] = None,
    seed: Optional[int] = None,
    recursive: bool = False,
    use_vlm: bool = True,
    fallback_count: int = 6,
) -> List[Path]:
    """착장 폴더에서 자동 코디네이션 조합

    VLM으로 이미지를 분류하고 카테고리별로 1개씩 선택하여
    완성된 코디네이션을 반환합니다.

    Args:
        outfit_folder: 착장 이미지 폴더 경로
        include_outer: 아우터 포함 여부 (겨울/간절기)
        include_hat: 모자 포함 여부
        include_accessory: 악세서리 포함 여부
        client: Gemini 클라이언트
        api_key: API 키
        seed: 랜덤 시드 (재현성)
        recursive: 하위 폴더 포함 여부
        use_vlm: VLM 분류 사용 여부 (False면 랜덤 선택)
        fallback_count: VLM 실패 시 선택할 이미지 수

    Returns:
        코디네이션에 포함된 이미지 경로 리스트
    """
    if seed is not None:
        random.seed(seed)

    # 폴더 내 모든 이미지 수집
    all_images = list_images(outfit_folder, recursive=recursive)

    if not all_images:
        logger.warning(f"No images found in {outfit_folder}")
        return []

    # VLM 미사용 시 fallback
    if not use_vlm:
        logger.info(f"VLM disabled, using fallback selection: {fallback_count} images")
        return classify_outfit_batch_fallback(all_images, fallback_count)

    try:
        # VLM으로 분류
        classified = classify_outfit_batch(all_images, client=client, api_key=api_key)

        # 카테고리별 그룹핑
        grouped: Dict[OutfitCategory, List[Path]] = {cat: [] for cat in OutfitCategory}
        for path, category in classified.items():
            grouped[category].append(path)

        # 로그: 분류 결과
        for cat, paths in grouped.items():
            if paths:
                logger.info(f"  {cat.value}: {len(paths)} images")

        # 모든 분류가 UNKNOWN이면 fallback
        non_unknown = sum(
            len(v) for k, v in grouped.items() if k != OutfitCategory.UNKNOWN
        )
        if non_unknown == 0:
            logger.warning("All items classified as UNKNOWN, using fallback")
            return classify_outfit_batch_fallback(all_images, fallback_count)

        # 코디네이션 조합
        outfit_items: List[Path] = []

        # 원피스가 있으면 상의+하의 대신 사용
        has_onepiece = len(grouped[OutfitCategory.ONEPIECE]) > 0

        # 필수: 상의 (원피스 없을 때)
        if not has_onepiece and grouped[OutfitCategory.TOP]:
            outfit_items.append(random.choice(grouped[OutfitCategory.TOP]))

        # 필수: 하의 (원피스 없을 때)
        if not has_onepiece and grouped[OutfitCategory.BOTTOM]:
            outfit_items.append(random.choice(grouped[OutfitCategory.BOTTOM]))

        # 원피스/세트
        if has_onepiece:
            outfit_items.append(random.choice(grouped[OutfitCategory.ONEPIECE]))

        # 필수: 신발
        if grouped[OutfitCategory.SHOES]:
            outfit_items.append(random.choice(grouped[OutfitCategory.SHOES]))

        # 선택: 아우터
        if include_outer and grouped[OutfitCategory.OUTER]:
            outfit_items.append(random.choice(grouped[OutfitCategory.OUTER]))

        # 선택: 모자
        if include_hat and grouped[OutfitCategory.HAT]:
            outfit_items.append(random.choice(grouped[OutfitCategory.HAT]))

        # 선택: 악세서리
        if include_accessory and grouped[OutfitCategory.ACCESSORY]:
            outfit_items.append(random.choice(grouped[OutfitCategory.ACCESSORY]))

        logger.info(f"Auto-coordinated outfit: {len(outfit_items)} items")

        return outfit_items

    except Exception as e:
        logger.error(f"VLM classification failed: {e}, using fallback")
        return classify_outfit_batch_fallback(all_images, fallback_count)


def get_coordinated_outfit(
    model_name: Optional[str] = None,
    include_outer: bool = True,
    include_hat: bool = True,
    seed: Optional[int] = None,
    use_vlm: bool = True,
) -> Dict[str, List[Path]]:
    """착장 + 얼굴 이미지 함께 반환 (편의 함수)

    Args:
        model_name: 모델 필터 (카리나, 고윤정 등)
        include_outer: 아우터 포함 여부
        include_hat: 모자 포함 여부
        seed: 랜덤 시드
        use_vlm: VLM 착장 분류 사용 여부

    Returns:
        {"face": [Path], "outfit": [Path, ...]}
    """
    # 착장 자동 코디네이션
    outfit_items = auto_coordinate(
        outfit_folder=DB_ROOT / "착장용",
        include_outer=include_outer,
        include_hat=include_hat,
        seed=seed,
        use_vlm=use_vlm,
    )

    # 얼굴 이미지
    face_images = select_images(
        image_type="face", count=1, model_name=model_name, seed=seed
    )

    return {"face": face_images, "outfit": outfit_items}


# =============================================================================
# 워크플로별 선택 함수
# =============================================================================


def get_test_images(
    workflow: WorkflowType,
    model_name: Optional[str] = None,
    counts: Optional[Dict[str, int]] = None,
    random_select: bool = True,
    seed: Optional[int] = None,
    recursive: bool = False,
    validate: bool = True,
    use_vlm_coordination: bool = True,
    include_outer: bool = True,
    include_hat: bool = True,
    include_accessory: bool = False,
) -> ImageSet:
    """
    워크플로 타입에 맞는 테스트 이미지 세트 반환.

    Args:
        workflow: 워크플로 타입 (core.validators.WorkflowType)
        model_name: 특정 모델 필터 (얼굴 이미지용)
        counts: 이미지 타입별 개수 지정 (VLM 미사용 시 fallback)
        random_select: 랜덤 선택 여부
        seed: 랜덤 시드
        recursive: 하위 폴더까지 재귀 탐색 여부
        validate: 14개 제한 검증 여부 (기본 True)
        use_vlm_coordination: VLM 착장 자동 분류 사용 (기본 True)
        include_outer: 아우터 포함 여부 (겨울/간절기)
        include_hat: 모자 포함 여부
        include_accessory: 악세서리 포함 여부

    Returns:
        ImageSet - 워크플로에 필요한 이미지 경로 딕셔너리
    """
    if seed is not None:
        random.seed(seed)

    required_types = WORKFLOW_REQUIREMENTS.get(workflow, [])

    if not required_types:
        logger.warning(f"No requirements defined for workflow: {workflow}")
        return {}

    result: ImageSet = {}

    for img_type in required_types:
        # 착장은 VLM 자동 분류 사용
        if img_type == "outfit" and use_vlm_coordination:
            result["outfit"] = auto_coordinate(
                outfit_folder=DB_ROOT / "착장용",
                include_outer=include_outer,
                include_hat=include_hat,
                include_accessory=include_accessory,
                seed=seed,
                recursive=recursive,
            )
            # product/WEAR 폴더도 대안으로 시도
            if not result["outfit"]:
                result["outfit"] = auto_coordinate(
                    outfit_folder=DB_ROOT / "product" / "WEAR",
                    include_outer=include_outer,
                    include_hat=include_hat,
                    include_accessory=include_accessory,
                    seed=seed,
                    recursive=recursive,
                )
        else:
            # 기타 이미지 타입은 기존 방식
            default_counts = get_default_counts(workflow)
            final_counts = {**default_counts, **(counts or {})}
            count = final_counts.get(img_type, 1)

            result[img_type] = select_images(
                image_type=img_type,
                count=count,
                model_name=model_name if img_type == "face" else None,
                random_select=random_select,
                seed=None,
                recursive=recursive,
            )

    # 14개 제한 검증
    if validate:
        validate_image_count(result)

    return result


# =============================================================================
# 편의 함수
# =============================================================================


def get_brandcut_images(
    model_name: Optional[str] = None,
    season: Literal["summer", "winter"] = "summer",
    seed: Optional[int] = None,
    use_vlm: bool = True,
) -> ImageSet:
    """브랜드컷 테스트용 이미지 간편 선택 (VLM 자동 코디네이션)

    Args:
        model_name: 모델 필터 (카리나, 고윤정 등)
        season: 시즌 ("summer": 아우터 제외, "winter": 아우터 포함)
        seed: 랜덤 시드
        use_vlm: VLM 착장 분류 사용 (기본 True)

    Note:
        - VLM이 착장을 자동 분류하여 코디네이션 조합
        - 여름: 상의+하의+신발+모자 (아우터 제외)
        - 겨울: 아우터+상의+하의+신발+모자 (아우터 포함)
    """
    include_outer = season == "winter"

    return get_test_images(
        WorkflowType.BRANDCUT,
        model_name=model_name,
        seed=seed,
        use_vlm_coordination=use_vlm,
        include_outer=include_outer,
        include_hat=True,
        include_accessory=False,
    )


def get_background_swap_images(
    seed: Optional[int] = None, recursive: bool = False
) -> ImageSet:
    """배경교체 테스트용 이미지 간편 선택

    Args:
        seed: 랜덤 시드
        recursive: 소스 이미지 폴더 재귀 탐색 여부

    Note:
        source=1, background=1 (레퍼런스는 1장만!)
    """
    return get_test_images(
        WorkflowType.BACKGROUND_SWAP,
        seed=seed,
        recursive=recursive,
        use_vlm_coordination=False,  # 배경교체는 착장 불필요
    )


def get_ugc_images(
    model_name: Optional[str] = None, seed: Optional[int] = None, use_vlm: bool = True
) -> ImageSet:
    """UGC 테스트용 이미지 간편 선택

    Note:
        face=1, outfit=VLM자동, ugc_style=1
    """
    return get_test_images(
        WorkflowType.UGC,
        model_name=model_name,
        seed=seed,
        use_vlm_coordination=use_vlm,
        include_outer=False,  # UGC는 보통 가벼운 착장
        include_hat=True,
    )


# =============================================================================
# 모듈 테스트용
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=== Test Image Selector ===\n")
    print(f"DB_ROOT: {DB_ROOT}")
    print(f"DB_ROOT exists: {DB_ROOT.exists()}")

    # 모델 목록
    print("\nAvailable models:", get_model_list())

    # 이미지 수 확인
    print(f"\nFace images: {get_image_count('face')}")
    print(f"Outfit images: {get_image_count('outfit')}")
    print(f"Background images: {get_image_count('background')}")

    # VLM 없이 테스트 (API 호출 안 함)
    print("\n--- Testing without VLM (fallback mode) ---")
    images = get_brandcut_images(
        model_name="카리나",
        season="winter",
        seed=42,
        use_vlm=False,  # VLM 없이 테스트
    )

    print(f"\nFace: {len(images.get('face', []))} images")
    print(f"Outfit: {len(images.get('outfit', []))} images")
    print(f"Style Ref: {len(images.get('style_ref', []))} images")

    # 14개 제한 검증
    print(f"\nValidation: {validate_image_count(images)}")
