"""
이커머스 상세페이지 이미지 세트 일괄 생성 모듈.
모델컷 5장 + 제품 누끼 + 디테일 크롭을 한 번에 생성.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Any, Optional

from PIL import Image

from core.config import IMAGE_MODEL, VISION_MODEL
from core.api import _get_next_api_key as get_next_api_key
from google import genai


# 포즈 시퀀스 (상세페이지 슬롯 순서)
DETAIL_PAGE_POSES = [
    "front_standing",  # 모델컷 1: 정면 자연
    "front_casual",  # 모델컷 2: 정면 캐주얼
    "front_casual",  # 모델컷 3: 정면 캐주얼2 (다른 seed)
    "front_standing",  # 모델컷 4: 정면 자연2 (다른 seed)
    "detail_closeup",  # 모델컷 5: 디테일/상반신
]


class DetailPageGenerator:
    """상세페이지 이미지 세트 생성기"""

    def __init__(self, client: Any = None, api_key: Optional[str] = None):
        """초기화

        Args:
            client: Google GenAI 클라이언트 (없으면 api_key로 생성)
            api_key: Gemini API 키 (client, api_key 모두 없으면 자동 조회)
        """
        if client is not None:
            self.client = client
        else:
            resolved_key = api_key or get_next_api_key()
            self.client = genai.Client(api_key=resolved_key)

        # 기존 모듈에서 함수 import
        from core.ecommerce.generator import generate_with_validation
        from core.ecommerce.analyzer import analyze_outfit_for_ecommerce
        from core.ecommerce.presets import POSE_PRESETS, BACKGROUND_PRESETS

        self._generate_with_validation = generate_with_validation
        self._analyze_outfit = analyze_outfit_for_ecommerce
        self.POSE_PRESETS = POSE_PRESETS
        self.BACKGROUND_PRESETS = BACKGROUND_PRESETS

    def generate_model_shots(
        self,
        face_images: list,
        outfit_images: list,
        background_preset: str = "white_studio",
        aspect_ratio: str = "3:4",
        resolution: str = "2K",
        model_spec: Optional[dict] = None,
    ) -> list:
        """모델컷 5장 순차 생성 (포즈별)

        Args:
            face_images: 얼굴 이미지 리스트
            outfit_images: 착장 이미지 리스트
            background_preset: 배경 프리셋 (기본: white_studio)
            aspect_ratio: 비율 (기본: 3:4)
            resolution: 해상도 (기본: 2K)
            model_spec: 모델 스펙 {"height": "175cm", "fitting_size": "S / 240mm"}

        Returns:
            list[dict]: 각 포즈별 생성 결과
            [{"slot_id": str, "pose": str, "image": PIL.Image, "validation": dict, "attempts": int}]
        """
        results = []

        for i, pose_id in enumerate(DETAIL_PAGE_POSES):
            print(f"[MODEL SHOT {i+1}/5] Generating {pose_id}...")

            # generate_with_validation은 내부에서 착장/얼굴 분석을 수행하므로
            # 직접 client를 전달
            result = self._generate_with_validation(
                face_images=face_images,
                outfit_images=outfit_images,
                client=self.client,
                pose=pose_id,
                background=background_preset,
                num_images=1,
                max_retries=2,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
            )

            results.append(
                {
                    "slot_id": f"model_{i+1}",
                    "pose": pose_id,
                    "image": result.get("image"),
                    "validation": {
                        "passed": result.get("passed", False),
                        "score": result.get("score", 0),
                        "grade": result.get("grade", "F"),
                        "criteria": result.get("criteria", {}),
                        "history": result.get("history", []),
                    },
                    "attempts": result.get("attempts", 1),
                }
            )

        return results

    def prepare_product_shots(
        self,
        product_images: list,
    ) -> list:
        """제품 누끼 준비 (배경 제거 또는 원본 사용)

        Args:
            product_images: 제품 이미지 리스트 [앞면, 뒷면]

        Returns:
            list[dict]: 제품 이미지 결과
        """
        results = []
        labels = ["product_front", "product_back"]

        for i, img in enumerate(product_images[:2]):
            if isinstance(img, (str, Path)):
                img = Image.open(img)
            results.append(
                {
                    "slot_id": labels[i] if i < len(labels) else f"product_{i+1}",
                    "image": img,
                    "source": "product_image",
                }
            )

        return results

    def prepare_detail_crops(
        self,
        product_images: list,
    ) -> list:
        """디테일 크롭 준비 (로고/라벨/원단)

        향후 VLM으로 위치 감지 후 자동 크롭 구현 예정.
        현재는 원본 이미지를 그대로 사용.

        Args:
            product_images: 제품 이미지 리스트

        Returns:
            list[dict]: 디테일 크롭 결과
        """
        results = []
        detail_types = ["logo_detail", "label_detail", "fabric_detail"]

        # 현재: 제품 이미지를 디테일로 재사용
        # TODO: VLM 기반 자동 크롭 구현
        for i, detail_id in enumerate(detail_types):
            img_idx = min(i, len(product_images) - 1)
            img = product_images[img_idx]
            if isinstance(img, (str, Path)):
                img = Image.open(img)

            results.append(
                {
                    "slot_id": detail_id,
                    "image": img,
                    "source": "crop_detail",
                    "crop_target": detail_id.replace("_detail", ""),
                }
            )

        return results

    def generate_full_set(
        self,
        face_images: list,
        outfit_images: list,
        product_images: list,
        background_preset: str = "white_studio",
        aspect_ratio: str = "3:4",
        resolution: str = "2K",
        model_spec: Optional[dict] = None,
        fabric_info: Optional[dict] = None,
    ) -> dict:
        """상세페이지 전체 이미지 세트 생성

        Args:
            face_images: 얼굴 이미지 리스트
            outfit_images: 착장 이미지 리스트
            product_images: 제품 이미지 리스트 [앞면, 뒷면, (디테일들)]
            background_preset: 배경 프리셋
            aspect_ratio: 비율
            resolution: 해상도
            model_spec: 모델 스펙 (선택)
            fabric_info: 소재 정보 (선택)

        Returns:
            dict: 전체 이미지 세트 + 메타데이터
        """
        print("=" * 60)
        print("[DETAIL PAGE] Full set generation started")
        print("=" * 60)

        # 1. 모델컷 5장 생성
        print("\n[PHASE 1/3] Generating model shots...")
        model_shots = self.generate_model_shots(
            face_images=face_images,
            outfit_images=outfit_images,
            background_preset=background_preset,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            model_spec=model_spec,
        )

        # 2. 제품 누끼 준비
        print("\n[PHASE 2/3] Preparing product shots...")
        product_shots = self.prepare_product_shots(product_images)

        # 3. 디테일 크롭 준비
        print("\n[PHASE 3/3] Preparing detail crops...")
        detail_crops = self.prepare_detail_crops(product_images)

        # 전체 결과 조합
        all_images = model_shots + product_shots + detail_crops

        result = {
            "model_shots": model_shots,
            "product_shots": product_shots,
            "detail_crops": detail_crops,
            "all_images": all_images,
            "metadata": {
                "total_slots": len(all_images),
                "model_shots_count": len(model_shots),
                "product_shots_count": len(product_shots),
                "detail_crops_count": len(detail_crops),
                "background_preset": background_preset,
                "aspect_ratio": aspect_ratio,
                "resolution": resolution,
                "model_spec": model_spec,
                "fabric_info": fabric_info,
                "generated_at": datetime.now().isoformat(),
            },
        }

        print(f"\n[DETAIL PAGE] Complete! {len(all_images)} images ready.")
        return result

    def save_full_set(
        self,
        result: dict,
        output_dir: Optional[Path] = None,
        description: str = "detail_page",
    ) -> Path:
        """전체 세트 저장 (표준 폴더 구조)

        Args:
            result: generate_full_set() 결과
            output_dir: 저장 경로 (없으면 자동 생성)
            description: 설명 텍스트

        Returns:
            Path: 저장된 폴더 경로
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if output_dir is None:
            output_dir = Path(f"Fnf_studio_outputs/ecommerce/{timestamp}_{description}")

        images_dir = output_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        # 이미지 저장
        for item in result["all_images"]:
            img = item.get("image")
            if img is not None:
                slot_id = item["slot_id"]
                dest = images_dir / f"{slot_id}.jpg"
                if isinstance(img, Image.Image):
                    img.save(dest, quality=95)
                elif isinstance(img, (str, Path)):
                    shutil.copy(img, dest)

        # 메타데이터 저장 (config.json)
        metadata = result.get("metadata", {})
        with open(output_dir / "config.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        # 검수 결과 저장 (validation.json)
        validations = {}
        for item in result.get("model_shots", []):
            if item.get("validation"):
                validations[item["slot_id"]] = item["validation"]

        if validations:
            with open(output_dir / "validation.json", "w", encoding="utf-8") as f:
                json.dump(validations, f, ensure_ascii=False, indent=2)

        print(f"[SAVED] {output_dir}")
        return output_dir


__all__ = [
    "DetailPageGenerator",
    "DETAIL_PAGE_POSES",
]
