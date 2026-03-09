"""
VLM 기반 분석 모듈 (Composition 패턴)

기존 core/outfit_analyzer.py를 래핑하여 확장.
- 착장 분석: OutfitAnalyzer 재사용
- 포즈/표정 분석: 신규 추가
- 무드/분위기 분석: 신규 추가
"""

from PIL import Image
from google import genai
from core.outfit_analyzer import OutfitAnalyzer, OutfitAnalysis
from core.config import VISION_MODEL
from .templates import (
    POSE_EXPRESSION_ANALYSIS_PROMPT,
    MOOD_ANALYSIS_PROMPT,
)
import json
import re


class BrandcutAnalyzer:
    """브랜드컷 전용 분석기 (OutfitAnalyzer 래핑)"""

    def __init__(self, client):
        """
        초기화

        Args:
            client: Google GenAI client instance
        """
        self.client = client
        self._outfit_analyzer = OutfitAnalyzer(client)  # 재사용

    def analyze_outfit(self, images: list) -> OutfitAnalysis:
        """
        착장 분석 - 기존 OutfitAnalyzer 위임

        Args:
            images: List of outfit image paths

        Returns:
            OutfitAnalysis with all extracted information
        """
        return self._outfit_analyzer.analyze(images)

    def analyze_pose_expression(self, image) -> dict:
        """
        포즈/표정 레퍼런스 분석 → JSON 반환

        Args:
            image: Image path (str) or PIL.Image object

        Returns:
            dict: {
                "pose": {...},
                "expression": {...},
                "camera": {...},
                "prompt_text": str
            }
        """
        # 이미지 로드
        if isinstance(image, str):
            try:
                pil_image = Image.open(image)
            except Exception as e:
                print(f"Error loading image {image}: {e}")
                return self._get_fallback_pose_analysis()
        else:
            pil_image = image

        # VLM 호출
        try:
            response = self.client.models.generate_content(
                model=VISION_MODEL,
                contents=[POSE_EXPRESSION_ANALYSIS_PROMPT, pil_image],
            )

            response_text = response.text.strip()

            # JSON 파싱
            data = self._parse_json_response(response_text)

            # 필수 키 검증
            if not all(k in data for k in ["pose", "expression", "camera"]):
                print("Warning: Missing required keys in pose analysis")
                return self._get_fallback_pose_analysis()

            return data

        except Exception as e:
            print(f"Error during pose/expression analysis: {e}")
            return self._get_fallback_pose_analysis()

    def analyze_mood(self, image) -> dict:
        """
        무드/분위기 레퍼런스 분석 → JSON 반환

        Args:
            image: Image path (str) or PIL.Image object

        Returns:
            dict: {
                "mood": str,
                "lighting": str,
                "color_grade": str,
                "background_feel": str,
                "keywords": list,
                "prompt_text": str
            }
        """
        # 이미지 로드
        if isinstance(image, str):
            try:
                pil_image = Image.open(image)
            except Exception as e:
                print(f"Error loading image {image}: {e}")
                return self._get_fallback_mood_analysis()
        else:
            pil_image = image

        # VLM 호출
        try:
            response = self.client.models.generate_content(
                model=VISION_MODEL, contents=[MOOD_ANALYSIS_PROMPT, pil_image]
            )

            response_text = response.text.strip()

            # JSON 파싱
            data = self._parse_json_response(response_text)

            # 필수 키 검증
            if not all(k in data for k in ["mood", "lighting", "color_grade"]):
                print("Warning: Missing required keys in mood analysis")
                return self._get_fallback_mood_analysis()

            return data

        except Exception as e:
            print(f"Error during mood analysis: {e}")
            return self._get_fallback_mood_analysis()

    def _parse_json_response(self, response_text: str) -> dict:
        """JSON 응답 파싱 (마크다운 코드 블록 제거)"""
        # Try to extract JSON from markdown code blocks
        json_match = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL
        )
        if json_match:
            response_text = json_match.group(1)

        # Try to parse JSON
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Response text: {response_text[:500]}")

            # Try to find JSON object in text
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}")

            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                try:
                    return json.loads(response_text[start_idx : end_idx + 1])
                except json.JSONDecodeError:
                    pass

            # Return empty dict on failure
            return {}

    def _get_fallback_pose_analysis(self) -> dict:
        """포즈 분석 실패 시 폴백"""
        return {
            "pose": {
                "stance": "standing naturally",
                "weight": "evenly distributed",
                "legs": "feet shoulder-width apart",
                "arms": "relaxed at sides",
                "shoulders": "level and relaxed",
                "head": "straight, looking forward",
            },
            "expression": {
                "eyes": "natural, open",
                "eyebrows": "relaxed",
                "mouth": "closed, neutral",
                "mood": "natural, confident",
            },
            "camera": {
                "gaze": "looking at camera",
                "angle": "eye level",
                "framing": "MFS (mid-full shot)",
            },
            "prompt_text": "standing naturally with confident expression, eye-level shot, mid-full shot framing",
        }

    def _get_fallback_mood_analysis(self) -> dict:
        """무드 분석 실패 시 폴백"""
        return {
            "mood": "natural, clean",
            "lighting": "soft natural daylight",
            "color_grade": "cool neutral tones, clean",
            "background_feel": "minimal, modern",
            "keywords": ["natural", "clean", "modern", "minimal"],
            "prompt_text": "natural clean atmosphere with soft daylight, cool neutral tones, minimal modern background",
        }


# 편의 함수 (시그니처: client가 첫 번째)
def analyze_outfit(client, images: list) -> OutfitAnalysis:
    """
    착장 이미지 분석 → OutfitAnalysis 반환

    Args:
        client: Google GenAI client instance (첫 번째 매개변수)
        images: List of outfit image paths (두 번째 매개변수)

    Returns:
        OutfitAnalysis with all extracted information

    Note: 시그니처가 (client, images) 순서로 기존 outfit_analyzer.py와 동일
    """
    analyzer = BrandcutAnalyzer(client)
    return analyzer.analyze_outfit(images)


def analyze_pose_expression(client, image) -> dict:
    """
    포즈/표정 레퍼런스 분석 → JSON 반환

    Args:
        client: Google GenAI client instance (첫 번째 매개변수)
        image: Image path or PIL.Image object (두 번째 매개변수)

    Returns:
        dict: {
            "pose": {...},
            "expression": {...},
            "camera": {...},
            "prompt_text": str
        }

    Note: 시그니처가 (client, image) 순서로 일관성 유지
    """
    analyzer = BrandcutAnalyzer(client)
    return analyzer.analyze_pose_expression(image)


def analyze_mood(client, image) -> dict:
    """
    무드/분위기 레퍼런스 분석 → JSON 반환

    Args:
        client: Google GenAI client instance (첫 번째 매개변수)
        image: Image path or PIL.Image object (두 번째 매개변수)

    Returns:
        dict: {
            "mood": str,
            "lighting": str,
            "color_grade": str,
            "background_feel": str,
            "keywords": list,
            "prompt_text": str
        }

    Note: 시그니처가 (client, image) 순서로 일관성 유지
    """
    analyzer = BrandcutAnalyzer(client)
    return analyzer.analyze_mood(image)
