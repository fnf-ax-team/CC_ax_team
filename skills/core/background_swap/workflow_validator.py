"""
배경 교체 워크플로 검증기 - ValidatorRegistry 인터페이스 구현
"""

from typing import Any, Dict, List
from PIL import Image

from .validator import BackgroundSwapValidator, BackgroundSwapValidationResult


class BackgroundSwapWorkflowValidator:
    """
    ValidatorRegistry 인터페이스를 위한 워크플로 검증기.
    내부적으로 BackgroundSwapValidator를 사용.
    """

    def __init__(self, client=None, api_key: str = None):
        """
        Args:
            client: Gemini client (optional)
            api_key: API key (client가 없을 경우 사용)
        """
        self.client = client
        self.api_key = api_key
        self._validator = None

    def _get_validator(self) -> BackgroundSwapValidator:
        """내부 검증기 가져오기 (lazy init)"""
        if self._validator is None:
            if self.api_key:
                self._validator = BackgroundSwapValidator(self.api_key)
            else:
                raise ValueError("API key required for validation")
        return self._validator

    def validate(
        self,
        generated_image: Image.Image,
        reference_images: Dict[str, Any] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        워크플로 검증 인터페이스.

        Args:
            generated_image: 생성된 이미지
            reference_images: {"source": PIL.Image} 형태의 참조 이미지
            **kwargs: 추가 옵션

        Returns:
            {
                "passed": bool,
                "score": int,
                "grade": str,
                "criteria": {...},
                "issues": [...]
            }
        """
        validator = self._get_validator()

        # source 이미지 추출
        source_image = None
        if reference_images:
            source_image = reference_images.get("source")

        # 검증 실행
        result = validator.validate(generated_image, source_image)

        return {
            "passed": result.passed,
            "score": result.total_score,
            "grade": result.grade,
            "criteria": {
                "model_preservation": result.model_preservation,
                "relight_naturalness": result.relight_naturalness,
                "lighting_match": result.lighting_match,
                "ground_contact": result.ground_contact,
                "physics_plausibility": result.physics_plausibility,
                "edge_quality": result.edge_quality,
                "prop_style_consistency": result.prop_style_consistency,
                "color_temperature_compliance": result.color_temperature_compliance,
                "perspective_match": result.perspective_match,
            },
            "issues": result.issues,
        }


__all__ = ["BackgroundSwapWorkflowValidator"]
