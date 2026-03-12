"""
이미지 생성기 - Gemini API를 사용한 배경 교체 이미지 생성
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from io import BytesIO
from PIL import Image
from typing import Dict, Any, Optional, Union, Callable
from .config import PipelineConfig
from core.utils import ImageUtils


class ImageGenerator:
    """이미지 생성기"""

    def __init__(self, config: PipelineConfig):
        self.config = config

    def generate(
        self,
        image_path: str,
        prompt: str,
        output_path: str,
        api_key: Union[str, Callable[[], str]],
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        """이미지 생성"""
        from google import genai
        from google.genai import types

        image_bytes = ImageUtils.load_image(image_path, self.config.max_image_size)

        result = {
            "input": image_path,
            "output": output_path,
            "status": "pending"
        }

        for attempt in range(self.config.api_retry_count):
            try:
                # Resolve API key (rotate on each attempt)
                key = api_key() if callable(api_key) else api_key
                client = genai.Client(api_key=key)

                # aspect ratio 계산
                img = Image.open(image_path)
                aspect_ratio = ImageUtils.get_aspect_ratio(*img.size)

                response = client.models.generate_content(
                    model=self.config.image_model,
                    contents=[types.Content(role="user", parts=[
                        types.Part(text=prompt),
                        types.Part(inline_data=types.Blob(mime_type="image/png", data=image_bytes)),
                    ])],
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        response_modalities=["IMAGE", "TEXT"],
                        image_config=types.ImageConfig(
                            aspect_ratio=aspect_ratio,
                            image_size=self.config.image_size
                        )
                    )
                )

                # 이미지 추출
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        result_image = Image.open(BytesIO(part.inline_data.data))
                        result_image.save(output_path, quality=95)

                        result["status"] = "success"
                        result["size"] = f"{result_image.size[0]}x{result_image.size[1]}"
                        return result

                # 이미지 없이 텍스트만 반환된 경우
                result["status"] = "error"
                result["error"] = "No image in response"
                return result

            except Exception as e:
                error_msg = str(e)
                if attempt < self.config.api_retry_count - 1:
                    wait = self.config.api_retry_delay * (attempt + 1)
                    time.sleep(wait)
                else:
                    result["status"] = "error"
                    result["error"] = error_msg[:200]

        return result
