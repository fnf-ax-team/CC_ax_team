# MLB 브랜드컷 생성 스킬

> 모델 얼굴 + 착장 이미지 → AI 화보 이미지 생성

## 개요

MLB 브랜드의 "Young & Rich" 컨셉에 맞는 고급스러운 패션 화보 이미지를 AI로 생성합니다.

### 핵심 기능

- **얼굴 보존**: 참조 얼굴 이미지와 동일 인물 생성
- **착장 재현**: 모든 착장 아이템 정확하게 반영
- **브랜드 톤앤매너**: MLB 스타일 가이드 준수 (쿨톤, 모던, 럭셔리)
- **VLM 분석**: 착장 디테일 자동 분석 및 프롬프트 반영

## 설치

```bash
pip install google-genai pillow python-dotenv
```

## 환경 변수

```bash
# .env
GEMINI_API_KEY=your_api_key_here
```

## 사용법

### Python API

```python
from generate_brandcut import generate_brandcut_batch

results = generate_brandcut_batch(
    face_folder="./faces",
    outfit_folder="./outfits",
    output_folder="./output",
    concept_image_path="./concept.jpg",  # 선택
    num_images=3,
    has_vehicle=False,
    aspect_ratio="3:4",
    image_size="2K"
)
```

### CLI

```bash
python generate_brandcut.py \
    --face ./faces \
    --outfit ./outfits \
    --output ./output \
    --concept ./concept.jpg \
    --num 3 \
    --ratio 3:4 \
    --quality 2K
```

### Claude Code 스킬

```
/브랜드컷
```

대화형으로 입력을 수집하고 자동 생성합니다.

## 입력 요구사항

### 얼굴 이미지
- 다양한 각도의 얼굴 사진 (1-5장)
- 고해상도 권장
- 정면/측면 포함 시 결과 향상

### 착장 이미지
- 각 아이템별 개별 이미지 권장
- 아우터, 상의, 하의, 헤드웨어, 가방, 액세서리
- 로고/디테일이 잘 보이는 이미지

### 컨셉 레퍼런스 (선택)
- 원하는 무드/포즈/앵글의 참고 이미지
- MLB 기존 화보 등

## 설정 옵션

| 옵션 | 값 | 설명 |
|------|-----|------|
| `aspect_ratio` | 3:4, 4:5, 9:16, 1:1, 16:9 | 이미지 비율 |
| `image_size` | 1K, 2K, 4K | 해상도 |
| `has_vehicle` | True/False | 배경에 럭셔리 차량 포함 |
| `num_images` | 1-10 | 생성 장수 |

## 비용

| 화질 | 해상도 | 비용/장 |
|------|--------|---------|
| 1K | 1024px | ~190원 |
| 2K | 2048px | ~190원 |
| 4K | 4096px | ~380원 |

## 파일 구조

```
브랜드컷_brand-cut/
├── SKILL.md              # 스킬 상세 문서
├── README.md             # 이 문서
└── generate_brandcut.py  # 생성 모듈

brand-dna/
└── mlb-prompt-cheatsheet.md  # MLB 프롬프트 치트시트
```

## 품질 검증 기준

| 항목 | 기준 |
|------|------|
| 얼굴 동일성 | ≥ 90 |
| 착장 재현도 | ≥ 85 |
| 해부학 정확성 | ≥ 90 |
| 포토리얼리즘 | ≥ 85 |

### Auto-Fail 조건
- 손가락 6개 이상
- 얼굴 다른 사람
- 착장 색상/로고 불일치
- 누런 톤 (골든아워 금지)

## MLB 브랜드 지침

### DO
- 쿨톤 색감 (뉴트럴, 블루 쉐도우)
- 모던/미니멀 배경
- 자신감 있는 포즈
- 럭셔리 SUV (차량 배경 시)

### DON'T
- 골든아워/웜톤
- 밝은 미소/치아 노출
- 복잡한 배경
- 일반 세단/경차

## 버전 히스토리

- **v1.0.0** (2026-02-10): 초기 릴리즈
  - 기본 브랜드컷 생성
  - VLM 착장 분석
  - 품질 검증

## 라이센스

F&F Internal Use Only
