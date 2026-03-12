"""
KlingAI Video API 클라이언트

KlingAI API와 통신하여 비디오 생성을 처리합니다.
JWT 인증, 에러 핸들링, 비동기 태스크 폴링을 포함합니다.
"""

import time
import base64
import jwt
import httpx
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any

from .config import (
    KLING_API_BASE,
    KLING_ACCESS_KEY,
    KLING_SECRET_KEY,
    KLING_DEFAULT_MODEL,
    KlingErrorCode,
    KLING_MAX_RETRIES,
    KLING_POLL_TIMEOUT,
    KLING_POLL_INTERVAL,
    KLING_JWT_TTL,
)


class KlingAPIError(Exception):
    """KlingAI API 에러"""

    def __init__(self, status_code: int, message: str, retryable: bool = False):
        self.status_code = status_code
        self.message = message
        self.retryable = retryable
        super().__init__(f"KlingAI API Error {status_code}: {message}")


def is_kling_error_retryable(status_code: int) -> bool:
    """
    재시도 가능한 에러인지 확인

    Args:
        status_code: HTTP 상태 코드

    Returns:
        bool: 재시도 가능하면 True
    """
    return status_code in [
        KlingErrorCode.RATE_LIMIT,
        KlingErrorCode.SERVER_ERROR,
        KlingErrorCode.SERVICE_UNAVAILABLE,
    ]


def get_kling_retry_delay(status_code: int, attempt: int) -> int:
    """
    에러 코드별 재시도 대기 시간 계산

    Args:
        status_code: HTTP 상태 코드
        attempt: 현재 재시도 횟수 (0-indexed)

    Returns:
        int: 대기 시간 (초)
    """
    if status_code == KlingErrorCode.RATE_LIMIT:
        return 60  # rate limit은 60초 대기
    else:
        return (attempt + 1) * 5


class KlingAIClient:
    """KlingAI Video API 클라이언트 (JWT 인증 + 에러 처리 포함)"""

    def __init__(
        self,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
    ):
        """
        KlingAIClient 초기화

        Args:
            access_key: KlingAI Access Key (없으면 환경변수에서 로드)
            secret_key: KlingAI Secret Key (없으면 환경변수에서 로드)

        Raises:
            ValueError: API 키가 설정되지 않은 경우
        """
        self.access_key = access_key or KLING_ACCESS_KEY
        self.secret_key = secret_key or KLING_SECRET_KEY
        if not self.access_key or not self.secret_key:
            raise ValueError(
                "KLING_ACCESS_KEY and KLING_SECRET_KEY not set. " "Add to .env file."
            )
        self._token: Optional[str] = None
        self._token_expires: float = 0

    def _generate_jwt(self) -> str:
        """
        JWT 토큰 생성 (HS256, 30분 TTL)

        캐싱된 토큰이 유효하면 재사용, 만료 60초 전에 갱신.

        Returns:
            str: JWT 토큰
        """
        now = time.time()
        # 만료 60초 전이면 재사용
        if self._token and now < self._token_expires - 60:
            return self._token

        headers = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "iss": self.access_key,
            "exp": int(now) + KLING_JWT_TTL,
            "nbf": int(now) - 5,
        }
        self._token = jwt.encode(
            payload, self.secret_key, algorithm="HS256", headers=headers
        )
        self._token_expires = now + KLING_JWT_TTL
        return self._token

    def _get_headers(self) -> Dict[str, str]:
        """인증 헤더 반환"""
        token = self._generate_jwt()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def _handle_response(self, response: httpx.Response) -> dict:
        """
        응답 처리 및 에러 핸들링

        Args:
            response: httpx 응답 객체

        Returns:
            dict: 응답 data 필드

        Raises:
            KlingAPIError: API 에러 발생 시
        """
        status = response.status_code

        if status == 200:
            data = response.json()
            if data.get("code") == 0:
                return data.get("data", {})
            # API 레벨 에러 (HTTP 200이지만 code != 0)
            raise KlingAPIError(
                status,
                data.get("message", "Unknown API error"),
                False,
            )

        error_msg = response.text
        retryable = is_kling_error_retryable(status)

        # 400 에러는 실제 API 응답 본문 포함 (디버깅 용이)
        if status == 400:
            try:
                error_data = response.json()
                detail = error_data.get("message", error_msg)
                raise KlingAPIError(status, f"Bad request: {detail}", False)
            except (ValueError, KeyError):
                raise KlingAPIError(status, f"Bad request: {error_msg}", False)

        error_messages = {
            401: "Invalid API key or expired JWT token",
            403: "Access forbidden",
            404: "Resource not found",
            429: "Rate limit exceeded",
            500: "KlingAI server error",
            503: "KlingAI service unavailable",
        }

        raise KlingAPIError(
            status,
            error_messages.get(status, error_msg),
            retryable,
        )

    async def _submit_task(self, url: str, body: dict) -> str:
        """
        태스크 제출 (재시도 포함)

        Args:
            url: API 엔드포인트 URL
            body: 요청 바디

        Returns:
            str: 태스크 ID

        Raises:
            KlingAPIError: API 에러 발생 시
        """
        for attempt in range(KLING_MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        url, headers=self._get_headers(), json=body
                    )
                    result = await self._handle_response(response)
                    return result["task_id"]

            except KlingAPIError as e:
                if e.retryable and attempt < KLING_MAX_RETRIES - 1:
                    delay = get_kling_retry_delay(e.status_code, attempt)
                    print(
                        f"[KlingAI] Retrying in {delay}s "
                        f"(attempt {attempt + 1}/{KLING_MAX_RETRIES})"
                    )
                    await asyncio.sleep(delay)
                else:
                    raise
            except httpx.TimeoutException:
                if attempt < KLING_MAX_RETRIES - 1:
                    delay = (attempt + 1) * 5
                    print(f"[KlingAI] Timeout, retrying in {delay}s")
                    await asyncio.sleep(delay)
                else:
                    raise KlingAPIError(0, "Request timeout after retries", False)

    async def text_to_video(
        self,
        prompt: str,
        model_name: Optional[str] = None,
        mode: str = "std",
        aspect_ratio: str = "16:9",
        duration: str = "5",
        cfg_scale: float = 0.5,
        negative_prompt: str = "",
        camera_control: Optional[Dict] = None,
        callback_url: Optional[str] = None,
    ) -> str:
        """
        텍스트-투-비디오(T2V) 태스크 생성

        Args:
            prompt: 비디오 프롬프트
            model_name: KlingAI 모델 (기본: KLING_DEFAULT_MODEL)
            mode: "std" (Standard) 또는 "pro" (Professional)
            aspect_ratio: "16:9", "9:16", "1:1"
            duration: "5" 또는 "10" (초)
            cfg_scale: 0.0~1.0 (프롬프트 충실도)
            negative_prompt: 네거티브 프롬프트
            camera_control: 카메라 컨트롤 (V1.x 모델만)
            callback_url: 완료 시 웹훅 URL

        Returns:
            str: 태스크 ID
        """
        model_name = model_name or KLING_DEFAULT_MODEL

        body = {
            "model_name": model_name,
            "prompt": prompt,
            "mode": mode,
            "aspect_ratio": aspect_ratio,
            "duration": duration,
            "cfg_scale": cfg_scale,
        }
        if negative_prompt:
            body["negative_prompt"] = negative_prompt
        if camera_control and model_name.startswith("kling-v1"):
            body["camera_control"] = camera_control
        if callback_url:
            body["callback_url"] = callback_url

        return await self._submit_task(f"{KLING_API_BASE}/v1/videos/text2video", body)

    async def image_to_video(
        self,
        image: str,
        prompt: str = "",
        model_name: Optional[str] = None,
        mode: str = "std",
        duration: str = "5",
        cfg_scale: float = 0.5,
        negative_prompt: str = "",
        image_tail: Optional[str] = None,
        enable_audio: bool = False,
        callback_url: Optional[str] = None,
    ) -> str:
        """
        이미지-투-비디오(I2V) 태스크 생성

        Args:
            image: 이미지 URL 또는 base64 문자열
            prompt: 모션 프롬프트 (선택)
            model_name: KlingAI 모델 (기본: KLING_DEFAULT_MODEL)
            mode: "std" (Standard) 또는 "pro" (Professional)
            duration: "5" 또는 "10" (초)
            cfg_scale: 0.0~1.0 (프롬프트 충실도)
            negative_prompt: 네거티브 프롬프트
            image_tail: 끝 프레임 이미지 URL (선택)
            enable_audio: 네이티브 오디오 생성 (kling-v2-6 + pro 모드 필수)
            callback_url: 완료 시 웹훅 URL

        Returns:
            str: 태스크 ID
        """
        model_name = model_name or KLING_DEFAULT_MODEL

        body = {
            "model_name": model_name,
            "image": image,
            "mode": mode,
            "duration": duration,
            "cfg_scale": cfg_scale,
        }
        if prompt:
            body["prompt"] = prompt
        if negative_prompt:
            body["negative_prompt"] = negative_prompt
        if image_tail:
            body["image_tail"] = image_tail
        if enable_audio:
            body["enable_audio"] = True
        if callback_url:
            body["callback_url"] = callback_url

        return await self._submit_task(f"{KLING_API_BASE}/v1/videos/image2video", body)

    @staticmethod
    def image_to_base64(image_path: str) -> str:
        """
        로컬 이미지를 base64 문자열로 변환 (I2V용)

        Args:
            image_path: 이미지 파일 경로

        Returns:
            str: base64 인코딩된 문자열
        """
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    async def poll_task(
        self,
        task_id: str,
        task_type: str = "text2video",
        max_wait: int = KLING_POLL_TIMEOUT,
        poll_interval: int = KLING_POLL_INTERVAL,
    ) -> dict:
        """
        태스크 상태 폴링 (succeed될 때까지 대기)

        Args:
            task_id: 태스크 ID
            task_type: "text2video" 또는 "image2video"
            max_wait: 최대 대기 시간 (초)
            poll_interval: 폴링 간격 (초)

        Returns:
            dict: 완료된 태스크 결과

        Raises:
            KlingAPIError: API 에러 발생 시
            TimeoutError: 타임아웃 발생 시
        """
        url = f"{KLING_API_BASE}/v1/videos/{task_type}/{task_id}"
        elapsed = 0
        attempt = 0

        async with httpx.AsyncClient(timeout=30.0) as client:
            while elapsed < max_wait:
                try:
                    attempt += 1
                    response = await client.get(url, headers=self._get_headers())
                    result = await self._handle_response(response)

                    status = result.get("task_status")
                    print(f"[KlingAI] [{attempt}] Task {task_id[:8]}...: {status}")

                    if status == "succeed":
                        return result
                    elif status == "failed":
                        msg = result.get("task_status_msg", "Unknown error")
                        raise KlingAPIError(500, f"Task failed: {msg}", False)

                    # submitted or processing
                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval

                except KlingAPIError as e:
                    if e.retryable:
                        await asyncio.sleep(poll_interval)
                        elapsed += poll_interval
                    else:
                        raise

        raise TimeoutError(f"Task {task_id} timeout after {max_wait}s")

    async def video_to_audio(
        self,
        video_id: str,
        sound_effect_prompt: str = "",
        background_music_prompt: str = "",
        asmr_mode: bool = False,
        callback_url: Optional[str] = None,
    ) -> str:
        """
        비디오-투-오디오(V2A) 태스크 생성

        기존 비디오에 AI 생성 오디오(효과음 + BGM)를 추가한다.

        Args:
            video_id: I2V/T2V로 생성된 비디오의 task_id
            sound_effect_prompt: 효과음 프롬프트 (영어)
            background_music_prompt: 배경음악 프롬프트 (영어)
            asmr_mode: ASMR 모드 (True면 asmr_mode=1)
            callback_url: 완료 시 웹훅 URL

        Returns:
            str: V2A 태스크 ID
        """
        body = {"video_id": video_id}
        if sound_effect_prompt:
            body["sound_effect_prompt"] = sound_effect_prompt
        if background_music_prompt:
            body["background_music_prompt"] = background_music_prompt
        if asmr_mode:
            body["asmr_mode"] = 1
        if callback_url:
            body["callback_url"] = callback_url

        return await self._submit_task(
            f"{KLING_API_BASE}/v1/audio/video-to-audio", body
        )

    async def poll_v2a_task(
        self,
        task_id: str,
        max_wait: int = 300,
        poll_interval: int = 5,
    ) -> dict:
        """
        V2A 태스크 상태 폴링

        Args:
            task_id: V2A 태스크 ID
            max_wait: 최대 대기 시간 (초, 기본 5분)
            poll_interval: 폴링 간격 (초, 기본 5초)

        Returns:
            dict: 완료된 태스크 결과

        Raises:
            KlingAPIError: API 에러 발생 시
            TimeoutError: 타임아웃 발생 시
        """
        url = f"{KLING_API_BASE}/v1/audio/video-to-audio/{task_id}"
        elapsed = 0
        attempt = 0

        async with httpx.AsyncClient(timeout=30.0) as client:
            while elapsed < max_wait:
                try:
                    attempt += 1
                    response = await client.get(url, headers=self._get_headers())
                    result = await self._handle_response(response)

                    status = result.get("task_status")
                    print(f"[KlingAI V2A] [{attempt}] Task {task_id[:8]}...: {status}")

                    if status == "succeed":
                        return result
                    elif status == "failed":
                        msg = result.get("task_status_msg", "Unknown error")
                        raise KlingAPIError(500, f"V2A task failed: {msg}", False)

                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval

                except KlingAPIError as e:
                    if e.retryable:
                        await asyncio.sleep(poll_interval)
                        elapsed += poll_interval
                    else:
                        raise

        raise TimeoutError(f"V2A task {task_id} timeout after {max_wait}s")

    async def download_video(self, video_url: str, output_path: str) -> str:
        """
        비디오 파일 다운로드

        CDN URL은 ~30일 후 만료되므로 즉시 다운로드 필수.

        Args:
            video_url: CDN 비디오 URL
            output_path: 저장 경로

        Returns:
            str: 저장된 파일 경로

        Raises:
            KlingAPIError: 다운로드 실패 시
        """
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(video_url)
            if response.status_code != 200:
                raise KlingAPIError(
                    response.status_code,
                    f"Video download failed: {response.text}",
                    False,
                )
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(response.content)
        return output_path
