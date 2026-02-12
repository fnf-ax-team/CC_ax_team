"""
셀피/인플루언서 VLM 기반 분석 모듈

얼굴 분석 및 착장 분석 기능 제공
- 얼굴 분석: 성별, 나이대, 얼굴형, 피부톤, 특징 감지
- 착장 분석: 카테고리, 스타일, 색상, 디테일 추출
"""

import json
import re
from typing import Union, Optional

from PIL import Image
from google import genai

from core.config import VISION_MODEL
from .templates import FACE_ANALYSIS_PROMPT, OUTFIT_ANALYSIS_PROMPT


class SelfieAnalyzer:
    """셀피/인플루언서 전용 분석기"""

    def __init__(self, client: genai.Client):
        """
        초기화

        Args:
            client: Google GenAI client instance
        """
        self.client = client

    def analyze_face(self, image: Union[str, Image.Image]) -> dict:
        """
        얼굴 이미지 분석 → 성별, 특징 등 JSON 반환

        Args:
            image: 이미지 경로(str) 또는 PIL.Image 객체

        Returns:
            dict: {
                "gender": str,
                "age_range": str,
                "face_shape": str,
                "skin_tone": str,
                "features": list,
                "description": str
            }
        """
        # 이미지 로드
        pil_image = self._load_image(image)
        if pil_image is None:
            return self._get_fallback_face_analysis()

        # VLM 호출
        try:
            response = self.client.models.generate_content(
                model=VISION_MODEL,
                contents=[FACE_ANALYSIS_PROMPT, pil_image],
            )

            response_text = response.text.strip()
            data = self._parse_json_response(response_text)

            # 필수 키 검증
            if "gender" not in data:
                print("[SelfieAnalyzer] Warning: gender 키 누락, 기본값 사용")
                return self._get_fallback_face_analysis()

            return data

        except Exception as e:
            print(f"[SelfieAnalyzer] 얼굴 분석 실패: {e}")
            return self._get_fallback_face_analysis()

    def analyze_outfit(self, image: Union[str, Image.Image]) -> dict:
        """
        착장 이미지 분석 → 카테고리, 스타일 등 JSON 반환

        Args:
            image: 이미지 경로(str) 또는 PIL.Image 객체

        Returns:
            dict: {
                "category": str,
                "top": dict,
                "bottom": dict,
                "style": str,
                "prompt_text": str
            }
        """
        # 이미지 로드
        pil_image = self._load_image(image)
        if pil_image is None:
            return self._get_fallback_outfit_analysis()

        # VLM 호출
        try:
            response = self.client.models.generate_content(
                model=VISION_MODEL,
                contents=[OUTFIT_ANALYSIS_PROMPT, pil_image],
            )

            response_text = response.text.strip()
            data = self._parse_json_response(response_text)

            # 필수 키 검증
            if "category" not in data:
                print("[SelfieAnalyzer] Warning: category 키 누락, 기본값 사용")
                return self._get_fallback_outfit_analysis()

            return data

        except Exception as e:
            print(f"[SelfieAnalyzer] 착장 분석 실패: {e}")
            return self._get_fallback_outfit_analysis()

    def _load_image(self, image: Union[str, Image.Image]) -> Optional[Image.Image]:
        """이미지 로드 (경로 또는 PIL Image)"""
        if isinstance(image, str):
            try:
                return Image.open(image)
            except Exception as e:
                print(f"[SelfieAnalyzer] 이미지 로드 실패 {image}: {e}")
                return None
        return image

    def _parse_json_response(self, response_text: str) -> dict:
        """JSON 응답 파싱 (마크다운 코드 블록 제거)"""
        # 마크다운 코드 블록에서 JSON 추출
        json_match = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL
        )
        if json_match:
            response_text = json_match.group(1)

        # JSON 파싱 시도
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"[SelfieAnalyzer] JSON 파싱 에러: {e}")

            # JSON 객체 직접 추출 시도
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}")

            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                try:
                    return json.loads(response_text[start_idx : end_idx + 1])
                except json.JSONDecodeError:
                    pass

            return {}

    def _get_fallback_face_analysis(self) -> dict:
        """얼굴 분석 실패 시 기본값"""
        return {
            "gender": "female",
            "age_range": "mid_20s",
            "face_shape": "oval",
            "skin_tone": "light",
            "features": [],
            "description": "20대 중반 여성",
        }

    def _get_fallback_outfit_analysis(self) -> dict:
        """착장 분석 실패 시 기본값"""
        return {
            "category": "casual",
            "top": {
                "item": "casual top",
                "color": "",
                "fit": "regular",
                "details": [],
            },
            "bottom": {
                "item": "",
                "color": "",
                "details": [],
            },
            "style": "casual everyday",
            "prompt_text": "casual everyday outfit",
        }


# 편의 함수 (시그니처: client가 첫 번째)
def analyze_face(client: genai.Client, image: Union[str, Image.Image]) -> dict:
    """
    얼굴 이미지 분석 → 성별, 특징 등 JSON 반환

    Args:
        client: Google GenAI client instance
        image: 이미지 경로(str) 또는 PIL.Image 객체

    Returns:
        dict: {
            "gender": str,
            "age_range": str,
            "face_shape": str,
            "skin_tone": str,
            "features": list,
            "description": str
        }
    """
    analyzer = SelfieAnalyzer(client)
    return analyzer.analyze_face(image)
