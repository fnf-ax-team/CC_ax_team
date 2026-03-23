"""
이커머스 End-to-End 파이프라인.
제품 정보 입력 -> AI 이미지 생성 -> Figma 상세페이지 조립 -> 채널별 배너 생성.

이 모듈은 전체 워크플로를 오케스트레이션하고,
각 단계의 결과를 다음 단계에 전달한다.

사용법:
    from core.ecommerce.pipeline import EcommercePipeline, PipelineConfig

    config = PipelineConfig(
        product_name="MLB NY 빅로고 반팔티",
        brand="MLB",
        face_image_dir="inputs/face",
        outfit_image_dir="inputs/outfit",
        product_image_paths=["inputs/product_front.jpg", "inputs/product_back.jpg"],
    )
    pipeline = EcommercePipeline(config)
    result = pipeline.run()
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Any, Optional
from dataclasses import dataclass, field


@dataclass
class PipelineConfig:
    """파이프라인 설정"""

    # 제품 정보
    product_name: str = ""
    brand: str = "MLB"
    price: Optional[str] = None
    discount: Optional[str] = None

    # 모델 스펙
    model_spec: Optional[dict] = (
        None  # {"height": "175cm", "fitting_size": "S / 240mm"}
    )
    fabric_info: Optional[dict] = None  # {"icon": "SPAN", "description": "..."}

    # 이미지 경로
    face_image_dir: Optional[str] = None
    outfit_image_dir: Optional[str] = None
    product_image_paths: list = field(default_factory=list)  # [앞면, 뒷면, ...]
    detail_image_paths: list = field(default_factory=list)  # [로고, 라벨, 원단]
    model_image_paths: list = field(
        default_factory=list
    )  # 기존 모델 이미지 (AI 생성 안 할 때)

    # 생성 설정
    generate_model_shots: bool = True  # True면 AI 생성, False면 기존 이미지 사용
    aspect_ratio: str = "3:4"
    resolution: str = "2K"
    background_preset: str = "white_studio"

    # 배너 설정
    channels: list = field(
        default_factory=lambda: ["naver", "google", "kakao", "meta", "youtube"]
    )
    cta_text: str = "자세히 보기"

    # Figma 설정
    figma_channel: Optional[str] = None  # Figma 연결 채널명
    detail_page_template: str = "mlb_standard"

    # 이미지 서빙 URL (Figma에서 이미지 로드용)
    image_base_url: str = "http://localhost:8000/outputs"

    # API 클라이언트 (외부에서 주입)
    client: Any = None
    api_key: Optional[str] = None


@dataclass
class PipelineResult:
    """파이프라인 실행 결과"""

    success: bool = False

    # Phase별 결과
    ai_generation: Optional[dict] = None  # AI 이미지 생성 결과
    detail_page_actions: list = field(default_factory=list)  # Figma 상세페이지 액션
    banner_actions: dict = field(default_factory=dict)  # 채널별 Figma 배너 액션

    # 저장 경로
    output_dir: Optional[Path] = None

    # 메타데이터
    metadata: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)


def _serialize_detail_action(action) -> dict:
    """figma_builder.FigmaAction -> dict 직렬화 (상세페이지 액션)"""
    return {
        "tool": action.tool,
        "params": action.params,
        "description": action.description,
        "slot_id": getattr(action, "slot_id", None),
        "node_ref": getattr(action, "node_ref", None),
        "depends_on": getattr(action, "depends_on", None),
    }


def _serialize_banner_action(action) -> dict:
    """figma_banner_builder.FigmaAction -> dict 직렬화 (배너 액션)"""
    return {
        "tool": action.tool,
        "params": action.params,
        "description": action.description,
        "zone_id": getattr(action, "zone_id", None),
        "node_ref": getattr(action, "node_ref", None),
    }


class EcommercePipeline:
    """이커머스 E2E 파이프라인

    Phase 1: AI 모델 이미지 5장 생성 (DetailPageGenerator)
    Phase 2: Figma 상세페이지 빌드 시퀀스 생성 (DetailPageFigmaBuilder)
    Phase 3: Figma 채널 배너 빌드 시퀀스 생성 (BannerFigmaBuilder)
    Phase 4: 결과 저장

    NOTE: Phase 2/3은 Figma MCP 도구 호출 시퀀스만 생성한다.
    실제 Figma 호출은 Claude가 반환된 시퀀스를 순차 실행하여 수행한다.
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.result = PipelineResult()

    def run(self) -> PipelineResult:
        """전체 파이프라인 실행

        Returns:
            PipelineResult: 실행 결과 (Figma 액션 시퀀스 포함)
        """
        print("=" * 70)
        print("[PIPELINE] E2E Ecommerce Pipeline Started")
        print(f"[PIPELINE] Product: {self.config.product_name}")
        print(f"[PIPELINE] Brand: {self.config.brand}")
        print("=" * 70)

        try:
            # Phase 1: AI 이미지 생성 (선택적)
            if self.config.generate_model_shots:
                self._phase_1_generate_images()

            # Phase 2: Figma 상세페이지 빌드 시퀀스
            self._phase_2_detail_page()

            # Phase 3: Figma 채널 배너 빌드 시퀀스
            self._phase_3_channel_banners()

            # Phase 4: 결과 저장
            self._phase_4_save()

            self.result.success = True

        except Exception as e:
            self.result.errors.append(str(e))
            print(f"[PIPELINE ERROR] {e}")
            import traceback

            traceback.print_exc()

        self._print_summary()
        return self.result

    # ------------------------------------------------------------------
    # Phase 1: AI 이미지 생성
    # ------------------------------------------------------------------

    def _phase_1_generate_images(self):
        """Phase 1: AI 모델 이미지 생성 (DetailPageGenerator 사용)"""
        print("\n[PHASE 1/4] AI Image Generation")
        print("-" * 40)

        # 이미지 로드
        face_images = self._load_images_from_dir(self.config.face_image_dir)
        outfit_images = self._load_images_from_dir(self.config.outfit_image_dir)

        if not face_images or not outfit_images:
            msg = "Face or outfit images not found. Skipping AI generation."
            print(f"  [WARN] {msg}")
            self.result.errors.append(msg)
            return

        # 제품 이미지 로드 (PIL.Image 또는 경로)
        from PIL import Image as PILImage

        product_images = []
        for p in self.config.product_image_paths:
            if Path(p).exists():
                product_images.append(PILImage.open(p))

        # DetailPageGenerator 사용
        from core.ecommerce.detail_page import DetailPageGenerator

        generator = DetailPageGenerator(
            client=self.config.client,
            api_key=self.config.api_key,
        )

        ai_result = generator.generate_full_set(
            face_images=face_images,
            outfit_images=outfit_images,
            product_images=product_images,
            background_preset=self.config.background_preset,
            aspect_ratio=self.config.aspect_ratio,
            resolution=self.config.resolution,
            model_spec=self.config.model_spec,
            fabric_info=self.config.fabric_info,
        )

        self.result.ai_generation = ai_result
        total = ai_result["metadata"]["total_slots"]
        print(f"  [OK] {total} images generated")

    # ------------------------------------------------------------------
    # Phase 2: Figma 상세페이지
    # ------------------------------------------------------------------

    def _phase_2_detail_page(self):
        """Phase 2: Figma 상세페이지 빌드 시퀀스 생성"""
        print("\n[PHASE 2/4] Figma Detail Page Build")
        print("-" * 40)

        from core.ecommerce.figma_builder import DetailPageFigmaBuilder

        builder = DetailPageFigmaBuilder(
            template_id=self.config.detail_page_template,
        )

        # 이미지 URL 매핑 (Figma에서 로드할 URL)
        image_urls = self._build_image_url_map()

        actions = builder.build_sequence(
            product_name=self.config.product_name,
            model_spec=self.config.model_spec,
            fabric_info=self.config.fabric_info,
            image_urls=image_urls,
        )

        self.result.detail_page_actions = actions
        print(f"  [OK] {len(actions)} Figma actions generated for detail page")

    # ------------------------------------------------------------------
    # Phase 3: 채널 배너
    # ------------------------------------------------------------------

    def _phase_3_channel_banners(self):
        """Phase 3: Figma 채널 배너 빌드 시퀀스 생성"""
        print("\n[PHASE 3/4] Figma Channel Banners Build")
        print("-" * 40)

        from core.banner.figma_banner_builder import BannerFigmaBuilder

        builder = BannerFigmaBuilder(brand=self.config.brand)

        # 배너에 사용할 제품 이미지 URL
        product_image_url = ""
        if self.config.product_image_paths:
            first_product = Path(self.config.product_image_paths[0]).name
            product_image_url = f"{self.config.image_base_url}/{first_product}"

        for channel in self.config.channels:
            try:
                actions = builder.build_channel_banners(
                    channel=channel,
                    product_name=self.config.product_name,
                    product_image_url=product_image_url,
                    price=self.config.price,
                    cta_text=self.config.cta_text,
                    discount=self.config.discount,
                )
                self.result.banner_actions[channel] = actions
                print(f"  [OK] {channel}: {len(actions)} Figma actions")
            except Exception as e:
                msg = f"{channel} banner build failed: {e}"
                self.result.errors.append(msg)
                print(f"  [WARN] {msg}")

    # ------------------------------------------------------------------
    # Phase 4: 저장
    # ------------------------------------------------------------------

    def _phase_4_save(self):
        """Phase 4: 결과 저장"""
        print("\n[PHASE 4/4] Saving Results")
        print("-" * 40)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        desc = self.config.product_name.replace(" ", "_").lower()[:30]
        output_dir = Path(f"Fnf_studio_outputs/ecommerce/{timestamp}_{desc}")
        output_dir.mkdir(parents=True, exist_ok=True)

        # AI 생성 이미지 저장 (Phase 1 결과가 있으면)
        if self.result.ai_generation:
            from core.ecommerce.detail_page import DetailPageGenerator

            gen = DetailPageGenerator(
                client=self.config.client,
                api_key=self.config.api_key,
            )
            gen.save_full_set(
                result=self.result.ai_generation,
                output_dir=output_dir / "detail_page",
            )

        # Figma 액션 시퀀스 저장 (참고/재실행용)
        actions_dir = output_dir / "figma_actions"
        actions_dir.mkdir(exist_ok=True)

        # 상세페이지 액션
        if self.result.detail_page_actions:
            dp_data = [
                _serialize_detail_action(a) for a in self.result.detail_page_actions
            ]
            with open(
                actions_dir / "detail_page_actions.json", "w", encoding="utf-8"
            ) as f:
                json.dump(dp_data, f, ensure_ascii=False, indent=2)

        # 배너 액션 (채널별)
        for channel, actions in self.result.banner_actions.items():
            banner_data = [_serialize_banner_action(a) for a in actions]
            with open(
                actions_dir / f"banner_{channel}_actions.json", "w", encoding="utf-8"
            ) as f:
                json.dump(banner_data, f, ensure_ascii=False, indent=2)

        # 파이프라인 설정 저장
        config_data = {
            "product_name": self.config.product_name,
            "brand": self.config.brand,
            "price": self.config.price,
            "discount": self.config.discount,
            "channels": self.config.channels,
            "template": self.config.detail_page_template,
            "aspect_ratio": self.config.aspect_ratio,
            "resolution": self.config.resolution,
            "background_preset": self.config.background_preset,
            "generate_model_shots": self.config.generate_model_shots,
            "model_spec": self.config.model_spec,
            "fabric_info": self.config.fabric_info,
            "timestamp": datetime.now().isoformat(),
            "detail_page_actions_count": len(self.result.detail_page_actions),
            "banner_actions_count": {
                ch: len(acts) for ch, acts in self.result.banner_actions.items()
            },
        }
        with open(output_dir / "pipeline_config.json", "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)

        self.result.output_dir = output_dir
        print(f"  [OK] Saved to: {output_dir}")

    # ------------------------------------------------------------------
    # 유틸리티
    # ------------------------------------------------------------------

    def _build_image_url_map(self) -> dict:
        """슬롯별 이미지 URL 맵 생성

        AI 생성 이미지, 기존 모델 이미지, 제품 이미지, 디테일 이미지를
        각 슬롯 ID에 매핑한 URL 딕셔너리를 반환한다.
        """
        url_map = {}
        base = self.config.image_base_url

        # AI 생성 이미지가 있으면 해당 URL 사용
        if self.result.ai_generation:
            for item in self.result.ai_generation.get("all_images", []):
                slot_id = item.get("slot_id", "")
                if slot_id:
                    url_map[slot_id] = f"{base}/ecommerce/latest/images/{slot_id}.jpg"

        # 기존 모델 이미지 사용 (AI 생성 안 했을 때)
        if self.config.model_image_paths:
            for i, path in enumerate(self.config.model_image_paths[:5]):
                url_map[f"model_{i+1}"] = f"{base}/{Path(path).name}"

        # 제품 이미지
        product_slot_ids = ["product_front", "product_back"]
        for i, path in enumerate(self.config.product_image_paths[:2]):
            slot_id = (
                product_slot_ids[i] if i < len(product_slot_ids) else f"product_{i+1}"
            )
            url_map[slot_id] = f"{base}/{Path(path).name}"

        # 디테일 이미지
        detail_slot_ids = ["logo_detail", "label_detail", "fabric_detail"]
        for i, path in enumerate(self.config.detail_image_paths[:3]):
            if i < len(detail_slot_ids):
                url_map[detail_slot_ids[i]] = f"{base}/{Path(path).name}"

        return url_map

    def _load_images_from_dir(self, dir_path: Optional[str]) -> list:
        """폴더에서 이미지 파일 로드

        Args:
            dir_path: 이미지 폴더 경로

        Returns:
            list[PIL.Image]: 로드된 이미지 리스트 (수정일 기준 정렬)
        """
        if not dir_path:
            return []

        from PIL import Image as PILImage

        p = Path(dir_path)
        if not p.exists():
            return []

        exts = {".jpg", ".jpeg", ".png", ".webp"}
        files = sorted([f for f in p.iterdir() if f.suffix.lower() in exts])
        return [PILImage.open(f) for f in files]

    def _print_summary(self):
        """파이프라인 실행 요약 출력"""
        print("\n" + "=" * 70)
        print("[PIPELINE SUMMARY]")
        print(f"  Product: {self.config.product_name}")
        print(f"  Brand: {self.config.brand}")
        print(f"  Status: {'SUCCESS' if self.result.success else 'FAILED'}")

        if self.result.ai_generation:
            meta = self.result.ai_generation.get("metadata", {})
            print(f"  AI Generated: {meta.get('total_slots', 0)} images")

        print(f"  Detail Page Actions: {len(self.result.detail_page_actions)}")

        total_banner = sum(len(a) for a in self.result.banner_actions.values())
        channel_count = len(self.result.banner_actions)
        print(f"  Banner Actions: {total_banner} across {channel_count} channels")

        if self.result.output_dir:
            print(f"  Output: {self.result.output_dir}")

        if self.result.errors:
            print(f"  Errors: {len(self.result.errors)}")
            for err in self.result.errors:
                print(f"    - {err}")

        print("=" * 70)


# ------------------------------------------------------------------
# 편의 함수
# ------------------------------------------------------------------


def run_ecommerce_pipeline(
    product_name: str,
    brand: str = "MLB",
    face_image_dir: str = None,
    outfit_image_dir: str = None,
    product_image_paths: list = None,
    channels: list = None,
    **kwargs,
) -> PipelineResult:
    """이커머스 파이프라인 간편 실행 함수

    Args:
        product_name: 상품명
        brand: 브랜드 (기본: MLB)
        face_image_dir: 얼굴 이미지 폴더 경로
        outfit_image_dir: 착장 이미지 폴더 경로
        product_image_paths: 제품 이미지 경로 리스트
        channels: 배너 채널 리스트 (기본: 전 채널)
        **kwargs: PipelineConfig 추가 설정

    Returns:
        PipelineResult: 실행 결과
    """
    config = PipelineConfig(
        product_name=product_name,
        brand=brand,
        face_image_dir=face_image_dir,
        outfit_image_dir=outfit_image_dir,
        product_image_paths=product_image_paths or [],
        channels=channels or ["naver", "google", "kakao", "meta", "youtube"],
        **kwargs,
    )
    pipeline = EcommercePipeline(config)
    return pipeline.run()


__all__ = [
    "PipelineConfig",
    "PipelineResult",
    "EcommercePipeline",
    "run_ecommerce_pipeline",
]
