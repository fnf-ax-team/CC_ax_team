"""
Tripo 3D API 클라이언트

Tripo 3D API와 통신하여 3D 모델 생성을 처리합니다.
에러 핸들링, 재시도 로직, 비동기 태스크 폴링을 포함합니다.
"""

import httpx
import asyncio
from typing import Optional, Dict, Any

from core.config import (
    TRIPO_API_BASE,
    TRIPO_API_KEY,
    TripoErrorCode,
    TRIPO_RATE_LIMIT_DELAY,
    TRIPO_MAX_RETRIES,
    TRIPO_POLL_TIMEOUT,
    TRIPO_POLL_INTERVAL,
)


class TripoAPIError(Exception):
    """Tripo API 에러"""

    def __init__(self, status_code: int, message: str, retryable: bool = False):
        self.status_code = status_code
        self.message = message
        self.retryable = retryable
        super().__init__(f"Tripo API Error {status_code}: {message}")


def is_tripo_error_retryable(status_code: int) -> bool:
    """
    재시도 가능한 에러인지 확인

    Args:
        status_code: HTTP 상태 코드

    Returns:
        bool: 재시도 가능하면 True
    """
    return status_code in [
        TripoErrorCode.RATE_LIMIT,
        TripoErrorCode.SERVER_ERROR,
        TripoErrorCode.SERVICE_UNAVAILABLE,
    ]


def get_tripo_retry_delay(status_code: int, attempt: int) -> int:
    """
    에러 코드별 재시도 대기 시간 계산

    Args:
        status_code: HTTP 상태 코드
        attempt: 현재 재시도 횟수 (0-indexed)

    Returns:
        int: 대기 시간 (초)
    """
    if status_code == TripoErrorCode.RATE_LIMIT:
        return TRIPO_RATE_LIMIT_DELAY
    else:
        # 일반 에러: exponential backoff
        return (attempt + 1) * 5


class Tripo3DClient:
    """Tripo 3D API 클라이언트 (에러 처리 포함)"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Tripo3DClient 초기화

        Args:
            api_key: Tripo API 키 (없으면 환경변수에서 로드)

        Raises:
            ValueError: API 키가 설정되지 않은 경우
        """
        self.api_key = api_key or TRIPO_API_KEY
        if not self.api_key:
            raise ValueError("TRIPO_API_KEY not set. Add to .env file.")
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    async def _handle_response(self, response: httpx.Response) -> dict:
        """
        응답 처리 및 에러 핸들링

        Args:
            response: httpx 응답 객체

        Returns:
            dict: JSON 응답

        Raises:
            TripoAPIError: API 에러 발생 시
        """
        status = response.status_code

        if status == 200:
            return response.json()

        error_msg = response.text
        retryable = is_tripo_error_retryable(status)

        error_messages = {
            400: "Bad request - check image format and parameters",
            401: "Invalid API key",
            402: "Insufficient credits - top up your Tripo account",
            403: "Access forbidden",
            404: "Resource not found",
            429: "Rate limit exceeded",
            500: "Tripo server error",
            503: "Tripo service unavailable",
        }

        raise TripoAPIError(status, error_messages.get(status, error_msg), retryable)

    async def create_task_with_retry(
        self, image_url: str, mode: str = "detailed", texture: bool = True
    ) -> str:
        """
        3D 생성 태스크 생성 (재시도 포함)

        Args:
            image_url: 입력 이미지 URL
            mode: 생성 모드 ("detailed" or "fast")
            texture: 텍스처 포함 여부

        Returns:
            str: 태스크 ID

        Raises:
            TripoAPIError: API 에러 발생 시
        """
        for attempt in range(TRIPO_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{TRIPO_API_BASE}/image-to-3d",
                        headers=self.headers,
                        json={"image_url": image_url, "mode": mode, "texture": texture},
                    )
                    result = await self._handle_response(response)
                    return result["task_id"]

            except TripoAPIError as e:
                if e.retryable and attempt < TRIPO_MAX_RETRIES - 1:
                    delay = get_tripo_retry_delay(e.status_code, attempt)
                    print(
                        f"[Tripo] Retrying in {delay}s (attempt {attempt + 1}/{TRIPO_MAX_RETRIES})"
                    )
                    await asyncio.sleep(delay)
                else:
                    raise
            except httpx.TimeoutException:
                if attempt < TRIPO_MAX_RETRIES - 1:
                    delay = (attempt + 1) * 5
                    print(f"[Tripo] Timeout, retrying in {delay}s")
                    await asyncio.sleep(delay)
                else:
                    raise TripoAPIError(0, "Request timeout after retries", False)

    async def poll_task(
        self,
        task_id: str,
        max_wait: int = TRIPO_POLL_TIMEOUT,
        poll_interval: int = TRIPO_POLL_INTERVAL,
    ) -> dict:
        """
        태스크 상태 폴링

        Args:
            task_id: 태스크 ID
            max_wait: 최대 대기 시간 (초)
            poll_interval: 폴링 간격 (초)

        Returns:
            dict: 완료된 태스크 결과

        Raises:
            TripoAPIError: API 에러 발생 시
            TimeoutError: 타임아웃 발생 시
        """
        elapsed = 0
        async with httpx.AsyncClient(timeout=30.0) as client:
            while elapsed < max_wait:
                try:
                    response = await client.get(
                        f"{TRIPO_API_BASE}/task/{task_id}", headers=self.headers
                    )
                    result = await self._handle_response(response)

                    status = result.get("status")
                    if status == "completed":
                        return result
                    elif status == "failed":
                        raise TripoAPIError(
                            500,
                            f"Task failed: {result.get('error', 'Unknown error')}",
                            False,
                        )

                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval

                except TripoAPIError as e:
                    if e.retryable:
                        await asyncio.sleep(poll_interval)
                        elapsed += poll_interval
                    else:
                        raise

        raise TimeoutError(f"Task {task_id} timeout after {max_wait}s")

    async def download_model(self, model_url: str, output_path: str) -> str:
        """
        3D 모델 다운로드

        Args:
            model_url: 모델 다운로드 URL
            output_path: 저장 경로

        Returns:
            str: 저장된 파일 경로

        Raises:
            TripoAPIError: 다운로드 실패 시
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(model_url)
            if response.status_code != 200:
                raise TripoAPIError(
                    response.status_code,
                    f"Failed to download model: {response.text}",
                    False,
                )
            with open(output_path, "wb") as f:
                f.write(response.content)
        return output_path

    async def upload_images(self, image_paths: list[str]) -> list[str]:
        """
        이미지 업로드 (Shoes 3D용)

        Args:
            image_paths: 이미지 경로 리스트

        Returns:
            list[str]: 업로드된 이미지 URL 리스트

        Raises:
            TripoAPIError: 업로드 실패 시
        """
        uploaded_urls = []
        for image_path in image_paths:
            # TODO: 실제 Tripo upload API 구현
            # 현재는 로컬 파일 경로를 반환 (임시)
            uploaded_urls.append(image_path)
        return uploaded_urls

    async def create_task(
        self,
        type: str,
        images: list[str],
        mode: str = "detailed",
        quad_mesh: bool = True,
        target_faces: int = 50000
    ) -> str:
        """
        3D 생성 태스크 생성 (Shoes 3D용)

        Args:
            type: 태스크 타입 (image_to_model)
            images: 이미지 URL 리스트
            mode: 생성 모드 (detailed, fast)
            quad_mesh: 쿼드 메쉬 사용 여부
            target_faces: 목표 폴리곤 수

        Returns:
            str: 태스크 ID

        Raises:
            TripoAPIError: 태스크 생성 실패 시
        """
        # 실제 Tripo API 호출 (image-to-3d)
        image_url = images[0] if images else ""
        texture = mode == "detailed"

        return await self.create_task_with_retry(
            image_url=image_url,
            mode=mode,
            texture=texture
        )

    async def render_view(
        self,
        model_id: str,
        camera_angle: dict,
        lighting: str = "studio_3point",
        resolution: list[int] = None,
        samples: int = 128,
        background: str = "transparent",
        format: str = "png"
    ) -> str:
        """
        3D 모델 렌더링 (미구현 - 향후 확장)

        Args:
            model_id: 모델 ID
            camera_angle: 카메라 각도
            lighting: 조명 설정
            resolution: 해상도
            samples: 샘플 수
            background: 배경
            format: 포맷

        Returns:
            str: 렌더링 이미지 URL

        Raises:
            NotImplementedError: 아직 구현 안됨
        """
        raise NotImplementedError("Tripo render API not implemented yet")
