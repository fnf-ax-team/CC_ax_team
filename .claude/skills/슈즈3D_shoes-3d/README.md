# 슈즈 3D (Shoes 3D)

신발 이미지 또는 CAD 파일을 3D 모델로 변환하여 다각도 렌더링 제공

## 📁 파일 구조

```
슈즈3D_shoes-3d/
├── SKILL.md                    # 스킬 명세서 (전체 문서)
├── README.md                   # 이 파일
├── __init__.py                 # 패키지 초기화
├── generate.py                 # 메인 실행 스크립트 (대화형)
├── pipeline.py                 # 5단계 파이프라인 통합
├── shoe_analyzer.py            # VLM 신발 분석기
├── silhouette_generator.py     # 실루엣 참조 이미지 생성
├── material_mapper.py          # 소재 → PBR 파라미터 매핑
└── renderer.py                 # 렌더링 엔진 및 품질 검증
```

## 🚀 사용 방법

### 1. CLI 실행 (대화형)

```bash
cd D:/FNF_Studio_TEST/New-fnf-studio
python -m .claude.skills.슈즈3D_shoes-3d.generate
```

### 2. Python API

```python
import asyncio
from pathlib import Path
import sys

# 스킬 경로 추가
skill_path = Path(".claude/skills/슈즈3D_shoes-3d")
sys.path.insert(0, str(skill_path))

from pipeline import Shoes3DPipeline

async def main():
    pipeline = Shoes3DPipeline(
        gemini_api_key="your_gemini_api_key",
        tripo_api_key="your_tripo_api_key"
    )

    result = await pipeline.run(
        input_images=["sneaker_front.jpg", "sneaker_side.jpg"],
        quality="standard",
        render_angles=["front", "side", "three_quarter"],
        background="white_studio"
    )

    print(f"✅ 3D 모델: {result.model_path}")
    print(f"📸 렌더링: {len(result.renders)}개")
    print(f"⭐ 총점: {result.validation['overall_score']:.1f}%")

asyncio.run(main())
```

## 📊 5단계 파이프라인

1. **입력 분석** (VLM) - 신발 타입, 소재, 색상, 특징 추출
2. **실루엣 생성** - Tripo API용 참조 이미지 생성 (4개 각도)
3. **3D 모델 생성** - Tripo API로 3D 변환
4. **소재 매핑** - VLM 소재 → PBR 파라미터 변환
5. **렌더링** - 7개 각도 렌더링 및 품질 검증

## 🎨 품질 옵션

| 품질 | 폴리곤 수 | 소요 시간 | 용도 |
|------|----------|----------|------|
| draft | 20K | 1분 | 빠른 프리뷰 |
| standard | 50K | 3분 | 일반 제품 페이지 |
| premium | 100K | 5분 | 마케팅 캠페인 |

## 📐 렌더링 각도 (7개)

- front (정면)
- back (후면)
- left (좌측면)
- right (우측면)
- top (윗면)
- bottom (밑창)
- three_quarter (3/4 뷰)

## ✅ 품질 검증 기준

| 항목 | 임계값 | 설명 |
|------|--------|------|
| shape_accuracy | ≥ 80 | 형태 정확도 (필수) |
| material_fidelity | ≥ 70 | 소재 충실도 |
| color_match | ≥ 75 | 색상 일치도 |
| detail_preservation | ≥ 65 | 디테일 보존도 |

## 🧪 PBR 소재 지원 (9종)

- leather (가죽)
- mesh (메쉬)
- rubber (고무)
- canvas (캔버스)
- synthetic_leather (합성 가죽)
- suede (스웨이드)
- patent_leather (에나멜)
- nylon (나일론)
- foam (폼)

## 📦 출력 파일 구조

```
outputs/shoes_3d_20260211_153000/
├── input_analysis.json         # Stage 1 분석 결과
├── reference_images/
│   ├── front_view.png          # Stage 2 참조 이미지
│   ├── side_view.png
│   ├── back_view.png
│   └── top_view.png
├── model/
│   ├── shoe_model.glb          # 3D 모델
│   └── pbr_materials.json      # PBR 파라미터
├── renders/
│   ├── front.png               # 7개 렌더링
│   ├── back.png
│   ├── left.png
│   ├── right.png
│   ├── top.png
│   ├── bottom.png
│   └── three_quarter.png
├── validation_report.json      # VLM 품질 평가
└── metadata.json               # 전체 메타데이터
```

## ⚙️ 설정 (.env)

```bash
GEMINI_API_KEY=your_gemini_api_key
TRIPO_API_KEY=your_tripo_api_key
```

## ⚠️ 주의사항

1. **API 크레딧 소모**: Tripo API는 크레딧 기반 과금. premium 모드는 draft보다 3배 많은 크레딧 사용
2. **타임아웃 설정**: 복잡한 모델은 5분 이상 소요 가능. TRIPO_POLL_TIMEOUT 조정 필요
3. **이미지 품질**: 입력 이미지가 흐릿하거나 각도가 부족하면 3D 모델 품질 저하
4. **파일 크기**: 프리미엄 모델은 텍스처 포함 시 50MB+ 가능

## 🔧 트러블슈팅

| 문제 | 원인 | 해결 방법 |
|------|------|----------|
| shape_accuracy < 50 | 입력 이미지 각도 부족 | 최소 3개 각도 제공 |
| Task timeout | 모델 복잡도 초과 | TRIPO_POLL_TIMEOUT 늘리기 |
| 402 Insufficient Credits | Tripo 크레딧 고갈 | 대시보드에서 크레딧 충전 |
| Texture seams visible | UV unwrap 실패 | uv_unwrap: "angle_based" 변경 |

## 📚 참고 자료

- [Tripo 3D API 문서](https://platform.tripo3d.ai/docs)
- [Gemini Imagen 3 가이드](https://ai.google.dev/gemini-api/docs/imagen)
- [PBR 소재 가이드](https://marmoset.co/posts/basic-theory-of-physically-based-rendering/)
