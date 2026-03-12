"""
Shoes 3D 파이프라인 - 5단계 통합 워크플로
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from core.config import IMAGE_MODEL, VISION_MODEL, TRIPO_API_BASE, TRIPO_API_KEY
from core.tripo_client import Tripo3DClient, TripoAPIError

# 절대 import로 변경 (패키지가 아닌 경우 대비)
try:
    from .shoe_analyzer import analyze_shoe
    from .silhouette_generator import generate_silhouette_views
    from .material_mapper import map_materials_to_pbr, get_dominant_material_pbr
    from .renderer import RENDER_ANGLES, render_config, validate_3d_quality, check_quality_thresholds
except ImportError:
    from shoe_analyzer import analyze_shoe
    from silhouette_generator import generate_silhouette_views
    from material_mapper import map_materials_to_pbr, get_dominant_material_pbr
    from renderer import RENDER_ANGLES, render_config, validate_3d_quality, check_quality_thresholds

logger = logging.getLogger(__name__)


@dataclass
class Shoes3DResult:
    """3D 생성 결과"""
    model_path: str
    renders: List[str]
    validation: Dict[str, float]
    analysis: Dict[str, Any]
    metadata: Dict[str, Any]


class Shoes3DPipeline:
    """신발 3D 모델 생성 파이프라인"""

    def __init__(self, gemini_api_key: str, tripo_api_key: Optional[str] = None):
        """
        파이프라인 초기화

        Args:
            gemini_api_key: Gemini API 키
            tripo_api_key: Tripo API 키 (없으면 환경변수에서 로드)
        """
        self.gemini_api_key = gemini_api_key
        self.tripo_client = Tripo3DClient(api_key=tripo_api_key)

    async def run(
        self,
        input_images: List[str],
        quality: str = "standard",
        render_angles: List[str] = None,
        background: str = "white_studio",
        output_dir: str = None
    ) -> Shoes3DResult:
        """
        5단계 파이프라인 실행

        Args:
            input_images: 입력 이미지 경로 리스트
            quality: 품질 (draft, standard, premium)
            render_angles: 렌더링할 각도 리스트 (기본값: front, side, three_quarter)
            background: 배경 스타일
            output_dir: 출력 디렉토리 (없으면 자동 생성)

        Returns:
            Shoes3DResult: 생성 결과
        """
        # 기본값 설정
        if render_angles is None:
            render_angles = ["front", "side", "three_quarter"]

        if output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = f"outputs/shoes_3d_{timestamp}"

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"=== Shoes 3D 파이프라인 시작 ===")
        logger.info(f"입력 이미지: {len(input_images)}개")
        logger.info(f"품질: {quality}")
        logger.info(f"렌더링 각도: {render_angles}")

        try:
            # Stage 1: 입력 분석
            logger.info("[Stage 1/5] 신발 분석 중...")
            analysis = await analyze_shoe(
                image_path=input_images[0],
                api_key=self.gemini_api_key
            )

            # 분석 결과 저장
            with open(output_path / "input_analysis.json", "w", encoding="utf-8") as f:
                import json
                json.dump(analysis, f, indent=2, ensure_ascii=False)

            # Stage 2: 실루엣 참조 이미지 생성
            logger.info("[Stage 2/5] 실루엣 참조 이미지 생성 중...")
            reference_dir = output_path / "reference_images"
            silhouette_images = await generate_silhouette_views(
                shoe_analysis=analysis,
                angles=["front", "side", "back", "top"],
                api_key=self.gemini_api_key,
                output_dir=reference_dir
            )

            # Stage 3: 3D 모델 생성 (Tripo API)
            logger.info("[Stage 3/5] 3D 모델 생성 중...")

            # 품질별 설정
            quality_presets = {
                "draft": {"target_faces": 20000, "mode": "fast"},
                "standard": {"target_faces": 50000, "mode": "detailed"},
                "premium": {"target_faces": 100000, "mode": "detailed"}
            }
            preset = quality_presets.get(quality, quality_presets["standard"])

            # 이미지 업로드
            uploaded_urls = await self.tripo_client.upload_images(silhouette_images)

            # 3D 생성 작업 생성
            task_id = await self.tripo_client.create_task(
                type="image_to_model",
                images=uploaded_urls,
                mode=preset["mode"],
                quad_mesh=True,
                target_faces=preset["target_faces"]
            )

            # 작업 완료 대기
            task_result = await self.tripo_client.poll_task(
                task_id=task_id,
                timeout=300,
                poll_interval=5
            )

            # 모델 다운로드
            model_dir = output_path / "model"
            model_dir.mkdir(exist_ok=True)
            model_path = model_dir / "shoe_model.glb"

            await self.tripo_client.download_model(
                model_url=task_result.model_url,
                output_path=str(model_path)
            )

            logger.info(f"3D 모델 저장: {model_path}")

            # Stage 4: 소재 매핑
            logger.info("[Stage 4/5] 소재 매핑 중...")
            pbr_materials = map_materials_to_pbr(analysis["materials"])

            # PBR 파라미터 저장
            with open(model_dir / "pbr_materials.json", "w", encoding="utf-8") as f:
                import json
                json.dump(pbr_materials, f, indent=2, ensure_ascii=False)

            # Stage 5: 렌더링 (현재는 Tripo render API 미구현으로 스킵)
            logger.info("[Stage 5/5] 렌더링 중...")
            renders_dir = output_path / "renders"
            renders_dir.mkdir(exist_ok=True)

            # TODO: Tripo render API 구현 후 활성화
            # render_paths = []
            # for angle in render_angles:
            #     render_url = await self.tripo_client.render_view(
            #         model_id=task_result.task_id,
            #         camera_angle=RENDER_ANGLES[angle],
            #         **render_config
            #     )
            #     render_path = renders_dir / f"{angle}.png"
            #     await self.tripo_client.download_model(render_url, str(render_path))
            #     render_paths.append(str(render_path))

            # 임시: 참조 이미지를 렌더링으로 대체
            render_paths = silhouette_images[:len(render_angles)]

            # 품질 검증
            logger.info("품질 검증 중...")
            validation = await validate_3d_quality(
                original_image=input_images[0],
                render_images=render_paths,
                api_key=self.gemini_api_key
            )

            # 검증 결과 저장
            with open(output_path / "validation_report.json", "w", encoding="utf-8") as f:
                import json
                json.dump(validation, f, indent=2, ensure_ascii=False)

            # 메타데이터 생성
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "input_images": input_images,
                "quality": quality,
                "render_angles": render_angles,
                "background": background,
                "analysis": analysis,
                "pbr_materials": pbr_materials,
                "validation": validation,
                "model_path": str(model_path),
                "renders": render_paths
            }

            # 메타데이터 저장
            with open(output_path / "metadata.json", "w", encoding="utf-8") as f:
                import json
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            logger.info(f"=== 파이프라인 완료 ===")
            logger.info(f"출력 디렉토리: {output_path}")
            logger.info(f"총점: {validation['overall_score']:.1f}")

            return Shoes3DResult(
                model_path=str(model_path),
                renders=render_paths,
                validation=validation,
                analysis=analysis,
                metadata=metadata
            )

        except TripoAPIError as e:
            logger.error(f"Tripo API 에러: {e}")
            raise

        except Exception as e:
            logger.error(f"파이프라인 에러: {e}")
            raise
