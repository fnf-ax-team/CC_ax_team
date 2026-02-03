---
name: 비디오처리_video-processing
description: 비디오 처리 스킬. 비디오 분석, 편집, 생성 시 사용. 프레임 추출, 비디오 분석, 샷 분할, 비디오 생성, 비디오 병합 패턴을 제공합니다.
---

## 개요

FNF Studio의 **비디오 처리 스킬**입니다.
비디오 분석, 편집, 생성에 필요한 패턴을 제공합니다.

## 역할

- 비디오 프레임 추출 및 처리
- 비디오 분석 (VLM 기반)
- 샷 분할 (shot splitting)
- 비디오 생성 (I2V, T2V)
- 비디오 병합 및 후처리

## 사용 시점

다음 상황에서 이 스킬을 사용하세요:

- 비디오를 분석할 때
- 비디오에서 프레임을 추출할 때
- 이미지에서 비디오를 생성할 때 (I2V)
- 여러 비디오를 병합할 때
- 비디오 편집이 필요할 때

## 핵심 패턴

### 1. 프레임 추출

```python
import cv2
import numpy as np
from typing import List, Tuple

def extract_frames(
    video_path: str,
    fps: float = None,
    max_frames: int = None
) -> Tuple[List[np.ndarray], float]:
    """비디오에서 프레임 추출"""

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"비디오를 열 수 없습니다: {video_path}")

    # 비디오 정보
    original_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # 샘플링 간격 계산
    if fps and fps < original_fps:
        sample_interval = int(original_fps / fps)
    else:
        sample_interval = 1
        fps = original_fps

    frames = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % sample_interval == 0:
            # BGR -> RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(frame_rgb)

            if max_frames and len(frames) >= max_frames:
                break

        frame_idx += 1

    cap.release()
    print(f"[Video] {len(frames)}개 프레임 추출 (원본: {total_frames}, 간격: {sample_interval})")

    return frames, fps

# 사용
frames, fps = extract_frames("input.mp4", fps=10, max_frames=100)
```

### 2. 비디오 분석 (VLM)

```python
from google import genai
from google.genai import types
from PIL import Image
import json

async def analyze_video(
    frames: List[np.ndarray],
    client,
    model: str = "gemini-2.5-flash",
    sample_count: int = 5
) -> dict:
    """VLM 기반 비디오 분석"""

    # 대표 프레임 샘플링
    if len(frames) > sample_count:
        indices = np.linspace(0, len(frames) - 1, sample_count, dtype=int)
        sampled_frames = [frames[i] for i in indices]
    else:
        sampled_frames = frames

    # 프레임을 Part로 변환
    frame_parts = []
    for frame in sampled_frames:
        pil = Image.fromarray(frame)
        buf = BytesIO()
        pil.save(buf, format="JPEG", quality=85)
        part = types.Part(
            inline_data=types.Blob(
                mime_type="image/jpeg",
                data=buf.getvalue()
            )
        )
        frame_parts.append(part)

    # 분석 프롬프트
    prompt = """Analyze this video sequence (representative frames shown).

ANALYZE:
1. scene_type: What kind of scene is this?
2. subjects: Who/what is in the video?
3. actions: What actions are happening?
4. mood: What is the overall mood/tone?
5. camera_movement: Is the camera moving?
6. shot_types: What shot types are used?
7. transitions: Any noticeable transitions?

RESPOND IN JSON:
{
  "scene_type": "<description>",
  "subjects": ["<subject1>", "<subject2>"],
  "actions": ["<action1>", "<action2>"],
  "mood": "<mood description>",
  "camera_movement": "<static|pan|tilt|zoom|tracking>",
  "shot_types": ["<wide|medium|close-up|extreme close-up>"],
  "transitions": ["<cut|fade|dissolve|wipe>"],
  "summary": "<1-2 sentence summary>"
}
"""

    gen_config = types.GenerateContentConfig(
        response_mime_type="application/json"
    )

    contents = [types.Part(text=prompt)] + frame_parts

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=gen_config
    )

    return json.loads(response.text)

# 사용
frames, fps = extract_frames("video.mp4", fps=1)
analysis = await analyze_video(frames, client, sample_count=5)
print(f"Scene: {analysis['scene_type']}")
```

### 3. 샷 분할 (Shot Splitting)

```python
import cv2
import numpy as np
from typing import List, Tuple

def detect_shot_boundaries(
    frames: List[np.ndarray],
    threshold: float = 30.0,
    min_shot_length: int = 15
) -> List[Tuple[int, int]]:
    """히스토그램 차이로 샷 경계 감지"""

    if len(frames) < 2:
        return [(0, len(frames) - 1)]

    # 히스토그램 계산
    def calc_histogram(frame):
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
        return cv2.normalize(hist, hist).flatten()

    # 프레임 간 차이 계산
    diffs = []
    prev_hist = calc_histogram(frames[0])

    for i in range(1, len(frames)):
        curr_hist = calc_histogram(frames[i])
        diff = cv2.compareHist(prev_hist, curr_hist, cv2.HISTCMP_BHATTACHARYYA)
        diffs.append(diff * 100)
        prev_hist = curr_hist

    # 샷 경계 감지
    boundaries = [0]
    for i, diff in enumerate(diffs):
        if diff > threshold:
            # 최소 샷 길이 확인
            if (i + 1) - boundaries[-1] >= min_shot_length:
                boundaries.append(i + 1)

    # 마지막 프레임 추가
    if boundaries[-1] != len(frames) - 1:
        boundaries.append(len(frames) - 1)

    # 샷 구간 생성
    shots = []
    for i in range(len(boundaries) - 1):
        shots.append((boundaries[i], boundaries[i + 1]))

    print(f"[Video] {len(shots)}개 샷 감지")
    return shots

# 사용
frames, fps = extract_frames("video.mp4")
shots = detect_shot_boundaries(frames, threshold=30.0)
for i, (start, end) in enumerate(shots):
    print(f"Shot {i + 1}: {start}-{end} ({end - start + 1} frames)")
```

### 4. 비디오 생성 (I2V)

```python
import torch
from PIL import Image

class VideoGenerator:
    """이미지에서 비디오 생성"""

    async def generate_from_image(
        self,
        image: Image.Image,
        prompt: str,
        duration: int = 5,
        resolution: str = "480P"
    ) -> torch.Tensor:
        """I2V 비디오 생성"""

        # Wan API 사용 예시
        from comfy_api_nodes.nodes_wan import WanImageToVideoApi

        wan_node = WanImageToVideoApi()

        # 이미지를 텐서로 변환
        img_tensor = self.pil_to_tensor(image)

        # 비디오 생성
        result = await wan_node.execute(
            image=img_tensor,
            audio=None,
            model="wan2.5-i2v-preview",
            prompt=prompt,
            negative_prompt="",
            resolution=resolution,
            duration=duration,
            seed=random.randint(0, 2**31 - 1),
            prompt_extend=True,
            watermark=True
        )

        return result[0]  # VIDEO tensor

    def pil_to_tensor(self, img):
        return torch.from_numpy(
            np.array(img.convert("RGB")).astype(np.float32) / 255.0
        ).unsqueeze(0)

# 사용
generator = VideoGenerator()
video = await generator.generate_from_image(
    image=pil_image,
    prompt="A person walking gracefully",
    duration=5,
    resolution="720P"
)
```

### 5. 비디오 병합

```python
import cv2
import torch
import numpy as np
from typing import List

def merge_videos(
    videos: List[torch.Tensor],
    fps: float = 30.0,
    output_path: str = None
) -> torch.Tensor:
    """여러 비디오를 순차적으로 병합"""

    all_frames = []

    for i, video in enumerate(videos):
        if video is None:
            continue

        # 텐서를 프레임 리스트로 변환
        if isinstance(video, torch.Tensor):
            # [T, H, W, C] 또는 [T, C, H, W]
            if video.dim() == 4:
                if video.shape[-1] in [3, 4]:  # [T, H, W, C]
                    frames = video.cpu().numpy()
                else:  # [T, C, H, W]
                    frames = video.permute(0, 2, 3, 1).cpu().numpy()
            else:
                print(f"[Merge] 알 수 없는 비디오 shape: {video.shape}")
                continue

            # 0-1 범위면 0-255로 변환
            if frames.max() <= 1.0:
                frames = (frames * 255).astype(np.uint8)

            all_frames.extend(list(frames))

    if not all_frames:
        print("[Merge] 병합할 프레임이 없습니다")
        return torch.zeros((1, 512, 512, 3))

    # 결과 텐서 생성
    result = np.stack(all_frames, axis=0)  # [T, H, W, C]
    result_tensor = torch.from_numpy(result.astype(np.float32) / 255.0)

    # 파일 저장 (옵션)
    if output_path:
        save_video(all_frames, output_path, fps)

    print(f"[Merge] {len(all_frames)} 프레임 병합 완료")
    return result_tensor

def save_video(frames: List[np.ndarray], output_path: str, fps: float = 30.0):
    """프레임을 비디오 파일로 저장"""

    if not frames:
        return

    height, width = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    for frame in frames:
        # RGB -> BGR
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        out.write(frame_bgr)

    out.release()
    print(f"[Video] 저장 완료: {output_path}")

# 사용
merged = merge_videos([video1, video2, video3], fps=30.0, output_path="merged.mp4")
```

## 코드 예제

### 예제 1: 비디오 참조 추출 (Reference Extractor)

```python
# Linn_video_reference_extractor.py 참조
class Linn_VideoReferenceExtractor:
    """비디오에서 대표 프레임 추출"""

    def extract(self, video_path: str, num_frames: int = 5):
        # 프레임 추출
        frames, fps = extract_frames(video_path)

        # 균등 간격 샘플링
        if len(frames) > num_frames:
            indices = np.linspace(0, len(frames) - 1, num_frames, dtype=int)
            sampled = [frames[i] for i in indices]
        else:
            sampled = frames

        # 텐서로 변환
        tensors = [self.frame_to_tensor(f) for f in sampled]
        combined = torch.cat(tensors, dim=0)

        return (combined,)
```

### 예제 2: 비디오 샷 분할기 (Shot Splitter)

```python
# Linn_video_shot_splitter.py 참조
class Linn_VideoShotSplitter:
    """비디오를 개별 샷으로 분할"""

    def split(self, video_path: str, threshold: float = 30.0):
        # 프레임 추출
        frames, fps = extract_frames(video_path)

        # 샷 경계 감지
        shots = detect_shot_boundaries(frames, threshold)

        # 각 샷을 개별 비디오로
        shot_videos = []
        shot_infos = []

        for i, (start, end) in enumerate(shots):
            shot_frames = frames[start:end+1]

            # 텐서로 변환
            shot_tensor = self.frames_to_video_tensor(shot_frames)
            shot_videos.append(shot_tensor)

            shot_infos.append({
                "index": i,
                "start_frame": start,
                "end_frame": end,
                "duration_sec": (end - start + 1) / fps
            })

        return (shot_videos, json.dumps(shot_infos))
```

### 예제 3: 배치 비디오 생성 (Batch I2V)

```python
# Linn_video_TextToVideo.py 참조
class Linn_WanI2VBatchProcessor:
    """여러 이미지를 각각 I2V로 처리"""

    async def process(self, images: List[torch.Tensor], prompts: List[str]):
        videos = []

        for i, (img, prompt) in enumerate(zip(images, prompts)):
            print(f"[I2V] {i + 1}/{len(images)} 처리 중...")

            try:
                video = await self._generate_single(img, prompt)
                videos.append(video)
            except Exception as e:
                print(f"[I2V] {i} 실패: {e}")
                continue

        return (videos,)

    async def _generate_single(self, image, prompt):
        from comfy_api_nodes.nodes_wan import WanImageToVideoApi
        wan_node = WanImageToVideoApi()

        result = await wan_node.execute(
            image=image,
            model="wan2.5-i2v-preview",
            prompt=prompt,
            resolution="480P",
            duration=5
        )

        return result[0]
```

## DO/DON'T

### DO

- **프레임 샘플링** (전체 프레임 처리 비효율)
- **메모리 관리** (프레임은 큰 메모리 사용)
- **async 처리** (API 호출은 비동기로)
- **BGR/RGB 변환 주의** (OpenCV는 BGR, PIL은 RGB)
- **codec 지원 확인** (mp4v, h264 등)
- **해상도 일관성** (병합 시 동일 해상도)

### DON'T

- **전체 프레임 메모리 로드 금지** (스트리밍/청크)
- **무한 비디오 생성 금지** (duration 제한)
- **동기 API 블로킹 금지** (await 사용)
- **원본 비디오 수정 금지** (복사본 작업)
- **저품질 압축 금지** (codec 품질 설정)

## 비디오 처리 가이드라인

### 해상도별 권장 설정

| 해상도 | 프레임 샘플링 | 분석 프레임 | 메모리 |
|--------|--------------|-------------|--------|
| 480P | 1 FPS | 5-10 | ~500MB |
| 720P | 0.5 FPS | 5 | ~1GB |
| 1080P | 0.5 FPS | 3-5 | ~2GB |
| 4K | 0.25 FPS | 3 | ~4GB |

### 비디오 생성 모델

| 모델 | 입력 | 해상도 | 시간 | 비고 |
|------|------|--------|------|------|
| wan2.5-i2v-preview | 이미지 | 480P-1080P | 5-10초 | I2V |
| Veo | 텍스트/이미지 | 720P | 8초 | T2V/I2V |

### 코덱 설정

```python
# 고품질 설정
fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # MP4 컨테이너

# H.264 (더 나은 압축)
fourcc = cv2.VideoWriter_fourcc(*'avc1')

# 무손실 (편집용)
fourcc = cv2.VideoWriter_fourcc(*'FFV1')
```

## 관련 스킬

- **배치처리_batch-processing**: 프레임 배치 처리
- **병렬처리_parallel-processing**: 프레임 병렬 처리
- **이미지분석기본_image-analysis-base**: 프레임 분석

## 참고 파일

- **비디오 노드 예제**:
  - `Linn_node/Linn_video_reference_extractor.py`
  - `Linn_node/Linn_video_shot_splitter.py`
  - `Linn_node/Linn_video_TextToVideo.py`
  - `Linn_node/Linn_video_VideoFiltering.py`
  - `Linn_node/Linn_video_VideoAnalysis.py`
  - `Linn_node/Linn_video_analyzer_unified.py`
  - `Linn_node/Linn_video_marketing_analyzer.py`

---

**작성일**: 2026-01-21
**버전**: 1.0
**관련 스킬**: 배치처리_batch-processing, 이미지분석기본_image-analysis-base
