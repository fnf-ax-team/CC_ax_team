# KlingAI 비디오 생성 참조 (T2V/I2V)

> SKILL.md에서 참조하는 서포트 파일. 단독 T2V/I2V 사용법 및 에러 핸들링 상세.
> 모든 코드: `core/beauty_video/generator.py`, `core/beauty_video/client.py`

## 단독 비디오 생성

파이프라인 없이 단독으로 T2V/I2V를 사용할 때 참조.

### 실행 흐름

```
1. 프롬프트 조립 → build_fashion_video_prompt() 또는 build_i2v_motion_prompt()
2. 태스크 제출 → KlingAI API (T2V 또는 I2V)
3. 폴링 대기 → 최대 10분 (10초 간격)
4. 비디오 다운로드 → 결과 저장 (prompt.json, prompt.txt, config.json)
```

### 모드

| 모드 | 설명 | 사용 시나리오 |
|------|------|-------------|
| T2V (Text-to-Video) | 텍스트만으로 비디오 생성 | 컨셉 비디오, 무드필름 |
| I2V (Image-to-Video) | 기존 이미지를 비디오로 | 브랜드컷/이커머스 이미지 → 동영상 변환 |

### 옵션

| 옵션 | 선택지 | 기본값 |
|------|--------|--------|
| 비율 | 16:9, 9:16, 1:1 | 16:9 |
| 길이 | 5초, 10초 | 5초 |
| 모드 | Standard, Professional | Standard |
| 모델 | kling-v1-6, kling-v2-0, kling-v2-5 | kling-v2-0 |
| CFG Scale | 0.0~1.0 | 0.5 |

### T2V 예시

```python
from core.beauty_video import (
    generate_text_to_video,
    build_fashion_video_prompt,
    DEFAULT_NEGATIVE_PROMPT,
    VideoGenerationConfig,
)

config = VideoGenerationConfig(
    model_name="kling-v2-0",
    mode="std",
    duration="5",
    aspect_ratio="9:16",
)

prompt = build_fashion_video_prompt(
    subject="MLB white tank top with NY logo",
    action="walk",
    setting="urban_street",
    camera="tracking",
    brand="MLB",
)

result = await generate_text_to_video(
    prompt=prompt,
    description="mlb_streetwear",
    config=config,
    negative_prompt=DEFAULT_NEGATIVE_PROMPT,
)
```

### I2V 예시

```python
from core.beauty_video import (
    generate_image_to_video,
    build_i2v_motion_prompt,
    DEFAULT_NEGATIVE_PROMPT,
    VideoGenerationConfig,
)

config = VideoGenerationConfig(mode="std", duration="5")

motion = build_i2v_motion_prompt(
    action="walk",
    camera="dolly_in",
)

result = await generate_image_to_video(
    image_path="path/to/brandcut_result.jpg",
    prompt=motion,
    description="brandcut_to_video",
    config=config,
    negative_prompt=DEFAULT_NEGATIVE_PROMPT,
)
```

### 단독 출력 폴더

```
Fnf_studio_outputs/video_generation/{YYYYMMDD_HHMMSS}_{description}/
    videos/
        input_source_01.jpg    (I2V: 소스 이미지)
        output_001.mp4         (생성된 비디오)
    prompt.json
    prompt.txt
    config.json
```

## 에러 핸들링

| 에러 | 재시도 | 복구 |
|------|--------|------|
| 429 Rate Limit | Yes (60초 대기) | 자동 재시도 |
| 503 Server Overloaded | Yes (exponential backoff) | 자동 재시도 |
| 500 Server Error | Yes (exponential backoff) | 자동 재시도 |
| 401 Unauthorized | No | API 키 확인 |
| Task Failed | No | 프롬프트 수정 후 재시도 |
| Timeout (10분) | No | poll_timeout 증가 |
| I2V rate limit (429) | Yes (60초 대기, 최대 3회) | 자동 재시도 |
| Gemini 이미지 실패 | No | 해당 컷 건너뛰기, 나머지 진행 |
| moviepy 연결 실패 | No | 개별 컷 MP4 보존 |
