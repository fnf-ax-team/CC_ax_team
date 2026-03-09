"""
VLM 기반 분석 모듈 (Composition 패턴)

기존 core/outfit_analyzer.py를 래핑하여 확장.
- 착장 분석: OutfitAnalyzer 재사용
- 포즈 분석: PoseAnalyzer 재사용 (인플루언서 모듈)
- 표정 분석: ExpressionAnalyzer 재사용 (인플루언서 모듈)
"""

from PIL import Image
from google import genai
from core.outfit_analyzer import OutfitAnalyzer, OutfitAnalysis
from core.ai_influencer.pose_analyzer import (
    PoseAnalyzer,
    PoseAnalysisResult,
)
from core.ai_influencer.expression_analyzer import (
    ExpressionAnalyzer,
    ExpressionAnalysisResult,
)


class BrandcutAnalyzer:
    """브랜드컷 전용 분석기 (OutfitAnalyzer 래핑)"""

    def __init__(self, client=None):
        """
        초기화

        Args:
            client: Google GenAI client instance (optional, legacy 호환)
        """
        self.client = client
        if client:
            self._outfit_analyzer = OutfitAnalyzer(client)
        else:
            self._outfit_analyzer = None

    def analyze_outfit(self, images: list) -> OutfitAnalysis:
        """
        착장 분석 - 기존 OutfitAnalyzer 위임

        Args:
            images: List of outfit image paths

        Returns:
            OutfitAnalysis with all extracted information
        """
        if self._outfit_analyzer is None:
            raise ValueError("OutfitAnalyzer requires a client instance")
        return self._outfit_analyzer.analyze(images)

    def analyze_pose(self, image, api_key=None) -> PoseAnalysisResult:
        """
        포즈 분석 - PoseAnalyzer 위임

        Args:
            image: Image path (str) or PIL.Image object
            api_key: Gemini API key (None이면 자동 로드)

        Returns:
            PoseAnalysisResult
        """
        analyzer = PoseAnalyzer(api_key=api_key)
        return analyzer.analyze(image)

    def analyze_expression(self, image, api_key=None) -> ExpressionAnalysisResult:
        """
        표정 분석 - ExpressionAnalyzer 위임

        Args:
            image: Image path (str) or PIL.Image object
            api_key: Gemini API key (None이면 자동 로드)

        Returns:
            ExpressionAnalysisResult
        """
        analyzer = ExpressionAnalyzer(api_key=api_key)
        return analyzer.analyze(image)

    def analyze_pose_expression(self, image, api_key=None) -> dict:
        """
        포즈/표정 레퍼런스 분석 (backward compatible)

        내부에서 PoseAnalyzer + ExpressionAnalyzer를 호출하고,
        기존 dict 형식으로 반환 + _pose_result / _expression_result 키 추가.

        Args:
            image: Image path (str) or PIL.Image object
            api_key: Gemini API key (None이면 자동 로드)

        Returns:
            dict: {
                "pose": {...},
                "expression": {...},
                "camera": {...},
                "prompt_text": str,
                "_pose_result": PoseAnalysisResult,
                "_expression_result": ExpressionAnalysisResult,
            }
        """
        # 포즈 분석
        pose_result = self.analyze_pose(image, api_key=api_key)

        # 표정 분석
        expr_result = self.analyze_expression(image, api_key=api_key)

        # legacy dict 형식으로 변환
        pose_dict = {
            "stance": pose_result.stance,
            "left_arm": pose_result.left_arm,
            "right_arm": pose_result.right_arm,
            "left_hand": pose_result.left_hand,
            "right_hand": pose_result.right_hand,
            "left_leg": pose_result.left_leg,
            "right_leg": pose_result.right_leg,
            "hip": pose_result.hip,
            "torso_tilt": pose_result.torso_tilt,
            "shoulder_line": pose_result.shoulder_line,
            "face_direction": pose_result.face_direction,
        }

        expression_dict = expr_result.to_preset_format()

        camera_dict = {
            "camera_height": pose_result.camera_height,
            "framing": pose_result.framing,
            "camera_angle": pose_result.camera_angle,
        }

        # prompt_text 조합
        prompt_text = (
            f"{pose_result.summary or pose_result.stance}, "
            f"{expr_result.to_prompt_text()}"
        )

        return {
            "pose": pose_dict,
            "expression": expression_dict,
            "camera": camera_dict,
            "prompt_text": prompt_text,
            # 새 타입 접근용
            "_pose_result": pose_result,
            "_expression_result": expr_result,
        }


# 편의 함수 (시그니처: client가 첫 번째)
def analyze_outfit(client, images: list) -> OutfitAnalysis:
    """
    착장 이미지 분석 -> OutfitAnalysis 반환

    Args:
        client: Google GenAI client instance (첫 번째 매개변수)
        images: List of outfit image paths (두 번째 매개변수)

    Returns:
        OutfitAnalysis with all extracted information
    """
    analyzer = BrandcutAnalyzer(client)
    return analyzer.analyze_outfit(images)


def analyze_pose_expression(client, image) -> dict:
    """
    포즈/표정 레퍼런스 분석 -> JSON 반환 (backward compatible)

    Args:
        client: Google GenAI client instance (첫 번째 매개변수)
        image: Image path or PIL.Image object (두 번째 매개변수)

    Returns:
        dict: {
            "pose": {...},
            "expression": {...},
            "camera": {...},
            "prompt_text": str,
            "_pose_result": PoseAnalysisResult,
            "_expression_result": ExpressionAnalysisResult,
        }
    """
    analyzer = BrandcutAnalyzer(client)
    return analyzer.analyze_pose_expression(image)


def analyze_pose(client_or_image, image=None, api_key=None) -> PoseAnalysisResult:
    """
    포즈 분석 (편의 함수)

    두 가지 호출 방식 지원:
    - analyze_pose(client, image)  # legacy
    - analyze_pose(image, api_key=key)  # 인플루언서 스타일

    Returns:
        PoseAnalysisResult
    """
    if image is not None:
        # legacy: analyze_pose(client, image)
        analyzer = BrandcutAnalyzer()
        return analyzer.analyze_pose(image, api_key=api_key)
    else:
        # 인플루언서 스타일: analyze_pose(image)
        analyzer = BrandcutAnalyzer()
        return analyzer.analyze_pose(client_or_image, api_key=api_key)


def analyze_expression(
    client_or_image, image=None, api_key=None
) -> ExpressionAnalysisResult:
    """
    표정 분석 (편의 함수)

    두 가지 호출 방식 지원:
    - analyze_expression(client, image)  # legacy
    - analyze_expression(image, api_key=key)  # 인플루언서 스타일

    Returns:
        ExpressionAnalysisResult
    """
    if image is not None:
        # legacy: analyze_expression(client, image)
        analyzer = BrandcutAnalyzer()
        return analyzer.analyze_expression(image, api_key=api_key)
    else:
        # 인플루언서 스타일: analyze_expression(image)
        analyzer = BrandcutAnalyzer()
        return analyzer.analyze_expression(client_or_image, api_key=api_key)
