---
name: shoes-3d
description: 신발 3D 모델 생성 - 이미지/CAD → 3D 렌더링
user-invocable: true
trigger-keywords: ["슈즈3D", "신발3D", "3D신발", "슈즈렌더링", "3D렌더"]
---

# 슈즈 3D (Shoes 3D)

**목적**: 신발 이미지 또는 CAD 파일을 3D 모델로 변환하여 다각도 렌더링 제공

**용도**:
- 온라인 스토어용 360도 제품 뷰
- 마케팅 캠페인용 고품질 3D 렌더링
- AR 시연용 3D 모델 생성
- 제품 디자인 프로토타입 시각화

---

## 파이프라인 (5단계)

### Stage 1: 입력 분석 (Input Analysis)

**입력**:
- 신발 이미지 (정면/측면/후면 뷰 선호)
- 또는 CAD 파일 (.obj, .fbx, .stl)

**VLM 프롬프트** (Gemini Flash):
```
Analyze this shoe image and extract:
1. Shoe type (sneaker, boot, sandal, heel, etc.)
2. Material types visible (leather, mesh, rubber, canvas, etc.)
3. Dominant colors (hex codes if possible)
4. Key structural features (laces, buckles, straps, logo placement)
5. Overall silhouette shape (low-top, mid-top, high-top)
6. Texture patterns (smooth, perforated, woven, etc.)

Return structured JSON with these fields.
```

**출력**:
```json
{
  "shoe_type": "sneaker",
  "materials": ["mesh", "synthetic_leather", "rubber"],
  "colors": ["#FFFFFF", "#000000", "#FF0000"],
  "features": ["laces", "nike_swoosh", "air_bubble"],
  "silhouette": "low-top",
  "textures": ["smooth", "perforated_mesh"]
}
```

---

### Stage 2: 메쉬 최적화 참조 생성 (Silhouette Generation)

**목적**: Tripo API가 정확한 형태를 생성하도록 실루엣 가이드 이미지 생성

**Gemini Imagen 3 프롬프트**:
```
High-quality product photography of {shoe_type}, clean white background,
studio lighting, {silhouette} design, showing {features},
shot from {angle} view, professional e-commerce style, 8K resolution
```

**각도별 생성**:
- front_view: 정면 (로고, 레이싱 시스템 강조)
- side_view: 측면 (전체 프로필, 밑창 높이)
- back_view: 후면 (힐 탭, 브랜딩)
- top_view: 윗면 (깔창, 개구부)

**설정** (`core/config.py`):
```python
IMAGE_MODEL = "gemini-3-pro-image-preview"
VISION_MODEL = "gemini-3-flash-preview"
```

---

### Stage 3: 3D 모델 생성 (Tripo 3D API)

**API 통합**:

```python
from core.config import TRIPO_API_BASE, TRIPO_API_KEY, TRIPO_POLL_TIMEOUT
from core.tripo_client import Tripo3DClient

client = Tripo3DClient(
    api_base=TRIPO_API_BASE,
    api_key=TRIPO_API_KEY
)
```

#### 3.1. 이미지 → 3D 변환 (Image-to-3D)

```python
# Upload reference images
upload_results = await client.upload_images([
    front_view_path,
    side_view_path,
    back_view_path
])

# Start 3D generation task
task_id = await client.create_task(
    type="image_to_model",
    images=upload_results,
    mode="refine",  # 고품질 모드
    quad_mesh=True  # 쿼드 메쉬 (리토폴로지 최적화)
)

# Poll until completion (max 300s)
model = await client.poll_task(
    task_id=task_id,
    timeout=TRIPO_POLL_TIMEOUT
)
```

#### 3.2. 메쉬 최적화 옵션

```python
optimization = {
    "target_faces": 50000,      # 폴리곤 수 제한
    "preserve_edges": True,     # 날카로운 엣지 보존
    "quad_dominant": True,      # 쿼드 메쉬 우선
    "uv_unwrap": "smart_uv"     # 텍스처 매핑용 UV
}
```

---

### Stage 4: 소재 매핑 (Material Mapping)

**목적**: VLM 분석 결과를 PBR 소재로 변환

**매핑 룰**:

| VLM 감지 소재 | PBR 파라미터 |
|--------------|-------------|
| `leather` | Roughness: 0.4, Metallic: 0.0, Specular: 0.5 |
| `mesh` | Roughness: 0.8, Metallic: 0.0, Opacity: 0.9 |
| `rubber` | Roughness: 0.6, Metallic: 0.0, Bump: 0.2 |
| `canvas` | Roughness: 0.7, Metallic: 0.0, Normal: fabric_pattern |
| `synthetic_leather` | Roughness: 0.3, Metallic: 0.1, Specular: 0.6 |
| `suede` | Roughness: 0.9, Metallic: 0.0, Fuzz: 0.3 |

**Tripo Texture Baking API**:
```python
# Generate PBR textures
textures = await client.bake_textures(
    model_id=model.id,
    resolution=2048,  # 2K 텍스처
    maps=["albedo", "normal", "roughness", "metallic"]
)
```

---

### Stage 5: 렌더링 (Multi-angle Rendering)

**7개 렌더링 각도**:

| Angle | Camera Position | Use Case |
|-------|----------------|----------|
| `front` | (0°, 0°, 0°) | 정면 - 메인 제품 이미지 |
| `back` | (180°, 0°, 0°) | 후면 - 힐 디테일 |
| `left` | (90°, 0°, 0°) | 좌측면 - 프로필 뷰 |
| `right` | (270°, 0°, 0°) | 우측면 - 반대 프로필 |
| `top` | (0°, 90°, 0°) | 윗면 - 깔창 뷰 |
| `bottom` | (0°, -90°, 0°) | 밑창 - 아웃솔 디테일 |
| `three_quarter` | (45°, 30°, 0°) | 3/4 뷰 - 마케팅 이미지 |

**렌더링 설정**:
```python
render_config = {
    "resolution": [1920, 1080],
    "samples": 128,  # 레이트레이싱 샘플
    "hdri": "studio_neutral_4k",
    "background": "transparent",
    "format": "png"
}
```

**Tripo Render API**:
```python
renders = []
for angle in RENDER_ANGLES:
    image = await client.render_view(
        model_id=model.id,
        camera_angle=angle,
        lighting="studio_3point",
        **render_config
    )
    renders.append(image)
```

---

## 에러 처리 (Tripo Error Codes)

```python
from core.tripo_client import TripoErrorCode

try:
    model = await client.create_task(...)
except TripoAPIError as e:
    if e.code == TripoErrorCode.INVALID_REQUEST:  # 400
        # 이미지 형식/크기 문제
        logger.error(f"Invalid input: {e.message}")

    elif e.code == TripoErrorCode.UNAUTHORIZED:  # 401
        # API 키 누락/만료
        logger.error("Check TRIPO_API_KEY in .env")

    elif e.code == TripoErrorCode.INSUFFICIENT_CREDITS:  # 402
        # 크레딧 부족
        logger.error("Tripo credits depleted")

    elif e.code == TripoErrorCode.FORBIDDEN:  # 403
        # 권한 없음 (플랜 제한)
        logger.error("Feature not available in current plan")

    elif e.code == TripoErrorCode.NOT_FOUND:  # 404
        # 작업 ID 없음
        logger.error(f"Task {task_id} not found")

    elif e.code == TripoErrorCode.RATE_LIMIT:  # 429
        # Rate limit 초과 → 재시도
        await asyncio.sleep(60)
        return await retry_with_backoff(...)

    elif e.code == TripoErrorCode.SERVER_ERROR:  # 500
        # Tripo 서버 에러 → 재시도
        await asyncio.sleep(30)
        return await retry_with_backoff(...)

    elif e.code == TripoErrorCode.SERVICE_UNAVAILABLE:  # 503
        # 서비스 점검 중
        logger.error("Tripo service temporarily unavailable")
```

**재시도 로직** (Exponential Backoff):
```python
async def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await func()
        except TripoAPIError as e:
            if e.code in [429, 500, 503]:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                await asyncio.sleep(wait_time)
            else:
                raise
    raise Exception("Max retries exceeded")
```

---

## 검증 기준 (Validation)

**VLM 품질 평가 프롬프트** (Gemini Flash):
```
Compare the generated 3D render with the original shoe image.
Rate these aspects from 0-100:

1. shape_accuracy: How well does the 3D model match the original silhouette?
2. material_fidelity: Are textures (leather, mesh, rubber) realistic?
3. color_match: Do colors match the reference image?
4. detail_preservation: Are logos, stitching, perforations visible?
5. lighting_quality: Is the render professionally lit?

Return JSON with scores.
```

**합격 기준**:
- `shape_accuracy >= 80` (필수)
- `material_fidelity >= 70`
- `color_match >= 75`
- `detail_preservation >= 65`

**재생성 트리거**:
```python
if validation["shape_accuracy"] < 80:
    # Stage 2로 돌아가 더 나은 참조 이미지 생성
    await regenerate_silhouette(
        emphasize=validation["weak_points"]
    )
```

---

## 대화 플로우

### 1. 입력 수집

```json
{
  "question": "신발 이미지를 업로드해주세요. (여러 각도 사진일수록 좋습니다)",
  "type": "file_upload",
  "accept": ["image/jpeg", "image/png", "model/obj", "model/fbx"],
  "multiple": true
}
```

### 2. 품질 선택

```json
{
  "question": "3D 모델 품질을 선택하세요:",
  "type": "choice",
  "options": [
    {
      "label": "빠른 프리뷰 (1분, 20K 폴리곤)",
      "value": "draft",
      "details": "간단한 확인용"
    },
    {
      "label": "표준 품질 (3분, 50K 폴리곤)",
      "value": "standard",
      "details": "일반 제품 페이지용"
    },
    {
      "label": "프리미엄 (5분, 100K 폴리곤 + PBR)",
      "value": "premium",
      "details": "마케팅 캠페인용"
    }
  ],
  "default": "standard"
}
```

### 3. 렌더링 각도 선택

```json
{
  "question": "렌더링할 각도를 선택하세요 (다중 선택 가능):",
  "type": "multi_select",
  "options": [
    "정면 (Front)",
    "측면 (Side)",
    "후면 (Back)",
    "윗면 (Top)",
    "밑창 (Bottom)",
    "3/4 뷰 (Three-quarter)",
    "전체 7각도"
  ],
  "default": ["정면 (Front)", "측면 (Side)", "3/4 뷰 (Three-quarter)"]
}
```

### 4. 배경 옵션

```json
{
  "question": "배경 스타일:",
  "type": "choice",
  "options": [
    {
      "label": "투명 배경 (PNG)",
      "value": "transparent"
    },
    {
      "label": "순백 스튜디오",
      "value": "white_studio"
    },
    {
      "label": "그라데이션 배경",
      "value": "gradient"
    },
    {
      "label": "실내 환경 (HDRI)",
      "value": "indoor_hdri"
    }
  ],
  "default": "white_studio"
}
```

---

## 출력 파일 구조

```
outputs/shoes_3d_{timestamp}/
├── input_analysis.json          # Stage 1 분석 결과
├── reference_images/
│   ├── front_view.png          # Stage 2 참조 이미지
│   ├── side_view.png
│   ├── back_view.png
│   └── top_view.png
├── model/
│   ├── shoe_model.glb          # Optimized 3D model
│   ├── shoe_model.obj          # Universal format
│   └── textures/
│       ├── albedo_2k.png
│       ├── normal_2k.png
│       ├── roughness_2k.png
│       └── metallic_2k.png
├── renders/
│   ├── front.png               # 7개 렌더링
│   ├── back.png
│   ├── left.png
│   ├── right.png
│   ├── top.png
│   ├── bottom.png
│   └── three_quarter.png
├── validation_report.json       # VLM 품질 평가
└── metadata.json               # 전체 파이프라인 메타데이터
```

---

## 설정 파일 참조 (`core/config.py`)

```python
# Tripo 3D API
TRIPO_API_BASE = "https://api.tripo3d.ai/v2/openapi"
TRIPO_API_KEY = os.getenv("TRIPO_API_KEY")
TRIPO_POLL_TIMEOUT = 300  # 5분

# Gemini Models (이미지 생성 및 VLM)
IMAGE_MODEL = "gemini-3-pro-image-preview"
VISION_MODEL = "gemini-3-flash-preview"

# 3D 품질 프리셋
TRIPO_QUALITY_PRESETS = {
    "draft": {"faces": 20000, "samples": 64},
    "standard": {"faces": 50000, "samples": 128},
    "premium": {"faces": 100000, "samples": 256}
}
```

---

## 사용 예시

### CLI 명령어
```bash
# 기본 실행 (표준 품질, 3각도 렌더링)
python -m skills.shoes_3d --input sneaker.jpg

# 프리미엄 품질, 전체 7각도
python -m skills.shoes_3d --input boot.png \
  --quality premium \
  --angles all \
  --background transparent

# 다중 입력 이미지 (360도 촬영본)
python -m skills.shoes_3d \
  --input front.jpg side.jpg back.jpg \
  --quality standard
```

### Python API
```python
from skills.shoes_3d import Shoes3DPipeline
from core.config import IMAGE_MODEL, VISION_MODEL, TRIPO_API_KEY

pipeline = Shoes3DPipeline(
    image_model=IMAGE_MODEL,
    vision_model=VISION_MODEL,
    tripo_api_key=TRIPO_API_KEY
)

result = await pipeline.run(
    input_images=["sneaker_front.jpg", "sneaker_side.jpg"],
    quality="premium",
    render_angles=["front", "side", "three_quarter"],
    background="white_studio"
)

print(f"✅ 3D 모델 생성 완료: {result.model_path}")
print(f"📸 렌더링 {len(result.renders)}개 저장됨")
print(f"🎯 형태 정확도: {result.validation['shape_accuracy']}%")
```

---

## 주의사항

1. **API 크레딧 소모**: Tripo API는 크레딧 기반 과금. `premium` 모드는 `draft`보다 3배 많은 크레딧 사용
2. **타임아웃 설정**: 복잡한 모델은 5분 이상 소요 가능. `TRIPO_POLL_TIMEOUT` 조정 필요
3. **이미지 품질**: 입력 이미지가 흐릿하거나 각도가 부족하면 3D 모델 품질 저하
4. **재질 제약**: Tripo는 PBR 소재만 지원. 특수 효과(홀로그램, 발광) 불가능
5. **파일 크기**: 프리미엄 모델은 텍스처 포함 시 50MB+ 가능. 웹 사용 시 압축 필요

---

## 트러블슈팅

| 문제 | 원인 | 해결 방법 |
|------|------|----------|
| `shape_accuracy < 50` | 입력 이미지 각도 부족 | 최소 3개 각도 (정면/측면/후면) 제공 |
| `Task timeout after 300s` | 모델 복잡도 초과 | `TRIPO_POLL_TIMEOUT` 늘리기 또는 품질 낮추기 |
| `402 Insufficient Credits` | Tripo 크레딧 고갈 | 대시보드에서 크레딧 충전 |
| `Texture seams visible` | UV unwrap 실패 | `uv_unwrap: "smart_uv"` → `"angle_based"` 변경 |
| `Render too dark` | HDRI 조명 부족 | `lighting: "studio_3point"` 사용 |

---

## 고급 기능 (향후 확장)

- **애니메이션**: 회전 360도 애니메이션 GIF/MP4 생성
- **AR 내보내기**: USDZ/GLB 포맷으로 iOS/Android AR 지원
- **배치 처리**: 여러 신발 모델 동시 생성
- **스타일 전이**: 특정 브랜드 스타일 (Nike, Adidas) 학습 적용
- **커스터마이징**: 사용자가 색상/소재 실시간 변경

---

## 레퍼런스

- [Tripo 3D API 문서](https://platform.tripo3d.ai/docs)
- [Gemini Imagen 3 가이드](https://ai.google.dev/gemini-api/docs/imagen)
- [PBR 소재 가이드](https://marmoset.co/posts/basic-theory-of-physically-based-rendering/)
- `core/config.py` - 프로젝트 설정 파일
- `core/tripo_client.py` - Tripo API 클라이언트 구현
