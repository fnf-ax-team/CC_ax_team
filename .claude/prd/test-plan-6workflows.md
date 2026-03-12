# 6개 워크플로 종합 테스트 계획

> 작성일: 2026-02-19
> 버전: v1.0
> 대상: face_swap, multi_face_swap, pose_change, pose_copy, outfit_swap, ecommerce

---

## 1. 개요

### 1.1 테스트 목적

| 목적 | 상세 |
|------|------|
| 기능 정확성 검증 | 각 워크플로의 핵심 기능이 명세대로 동작하는지 확인 |
| 검수 로직 신뢰성 | VLM 기반 검증기가 합격/불합격을 올바르게 판별하는지 확인 |
| Auto-Fail 동작 확인 | 탈락 조건에서 즉시 재생성 루프가 작동하는지 확인 |
| 엣지 케이스 안전성 | 비정상 입력(다중 얼굴, 극단적 포즈 등)에서 안전하게 처리되는지 확인 |
| 품질 기준 적합성 | 실제 생성 이미지가 브랜드 납품 기준을 충족하는지 확인 |

### 1.2 테스트 범위 (6개 워크플로)

| 워크플로 | 모듈 경로 | 검증기 | 상태 |
|---------|-----------|--------|------|
| 얼굴 교체 | `core/face_swap/` | `FaceSwapValidator` | 구현 완료 |
| 다중 얼굴 교체 | `core/multi_face_swap/` | `MultiFaceSwapValidator` | 구현 완료 |
| 포즈 변경 | `core/pose_change/` | `PoseChangeValidator` | 구현 완료 |
| 포즈 따라하기 | `core/pose_copy/` | `PoseCopyValidator` | 구현 완료 |
| 착장 스왑 | `core/outfit_swap/` | `OutfitSwapValidator` | 구현 완료 |
| 이커머스 | `core/ecommerce/` | `EcommerceValidator` | 구현 완료 |

### 1.3 테스트 환경

| 항목 | 내용 |
|------|------|
| Python | 3.10+ |
| API | Gemini API (IMAGE_MODEL, VISION_MODEL) |
| 키 관리 | `get_next_api_key()` 로테이션 (`.env` 파일) |
| 출력 경로 | `Fnf_studio_outputs/{workflow}/{timestamp}/` |
| 테스트 파일 위치 | `tests/{workflow}/` |
| 기본 해상도 | 2K (테스트 시 1K 권장) |

---

## 2. 테스트 레벨

### 2.1 Unit Test

개별 함수 단위 테스트. API 호출 없이 Mock으로 검증.

| 대상 | 테스트 내용 |
|------|------------|
| 검증기 점수 계산 | `total_score` 가중 평균 계산 정확성 |
| Auto-Fail 판정 로직 | 임계값 미달 시 `auto_fail=True` 반환 여부 |
| `format_korean()` 출력 | 검수 결과 표 형식 일관성 |
| 프리셋 데이터 | `get_pose_description()`, `list_presets()` 반환값 |
| 이미지 로드 헬퍼 | `_load_image()` 경로/PIL 모두 처리 여부 |

### 2.2 Integration Test

모듈 간 연동 테스트. API 호출 포함 (1K 해상도).

| 대상 | 테스트 내용 |
|------|------------|
| VLM 검수 응답 파싱 | JSON 응답이 `CommonValidationResult`로 정상 변환되는지 |
| 재시도 루프 | 탈락 시 `max_retries=2` 루프 작동 여부 |
| 강화 규칙 주입 | `get_enhancement_rules()` 결과가 프롬프트에 반영되는지 |
| `ValidatorRegistry` | `WorkflowType`으로 검증기 조회 가능 여부 |

### 2.3 E2E Test

전체 파이프라인 테스트. 실제 이미지 생성 + 검수 + 저장.

| 대상 | 테스트 내용 |
|------|------------|
| 분석 -> 생성 -> 검수 -> 저장 | 4단계 파이프라인 완전 실행 |
| `generate_with_validation()` | 합격 이미지 저장, 불합격 재생성 여부 |
| 출력 경로 생성 | `Fnf_studio_outputs/` 하위 타임스탬프 폴더 자동 생성 |

### 2.4 Visual Test

생성 이미지의 품질을 사람이 직접 검수하는 테스트.

| 대상 | 테스트 내용 |
|------|------------|
| 얼굴 동일성 | 레퍼런스 대비 인물 일치 여부 육안 확인 |
| 착장 정확도 | 색상/로고/디테일 일치 여부 육안 확인 |
| 자연스러움 | 포즈/조명/경계의 어색함 여부 육안 확인 |
| 브랜드 톤 | MLB 브랜드 가이드라인 준수 여부 확인 |

---

## 3. 워크플로별 테스트 케이스

### 3.1 face_swap (얼굴 교체)

**검증 기준 요약:**
- face_identity 40%, pose_preservation 25%, outfit_preservation 20%, lighting_consistency 10%, edge_quality 5%
- Pass: total_score >= 95, Auto-Fail: face_identity < 80

| # | 케이스 | 입력 | 예상 결과 | 우선순위 |
|---|--------|------|----------|---------|
| 1 | 기본 케이스 | 소스 이미지 + 얼굴 1장 | 얼굴만 교체, 포즈/착장/배경 완전 보존 | P0 |
| 2 | 다중 얼굴 이미지 제공 | 소스 + 얼굴 5장 | 첫 번째 얼굴 사용, 나머지 무시 또는 경고 | P1 |
| 3 | 측면 얼굴 소스 | 소스(측면 포즈) + 정면 얼굴 | 각도 불일치 경고, 최선 결과 생성 또는 재시도 | P2 |
| 4 | 얼굴 가림 케이스 | 소스(손으로 얼굴 일부 가림) + 얼굴 | VLM이 partial occlusion 경고, edge_quality 감점 | P2 |
| 5 | 얼굴 없는 소스 | 배경만 있는 이미지 + 얼굴 | 오류 반환 또는 탈락 | P1 |
| 6 | 착장 색상 확인 | 빨간 착장 소스 + 다른 얼굴 | 착장 색상 동일 유지 확인 | P0 |
| 7 | Auto-Fail 유발 | 의도적으로 다른 인종 얼굴 | face_identity < 80 -> Auto-Fail 반환 | P0 |
| 8 | 재시도 루프 | 낮은 품질 입력 | max_retries=2 소진 후 최선 결과 반환 | P1 |

**검증 항목별 임계값:**

| 항목 | 가중치 | 통과 임계값 | Auto-Fail 임계값 |
|------|--------|------------|----------------|
| 얼굴 동일성 | 40% | >= 95 | < 80 |
| 포즈 유지 | 25% | >= 95 | - |
| 착장 유지 | 20% | >= 95 | - |
| 조명 일관성 | 10% | >= 80 | - |
| 경계 품질 | 5% | >= 80 | - |

---

### 3.2 multi_face_swap (다중 얼굴 교체)

**검증 기준 요약:**
- all_faces_identity 40%, face_consistency 20%, pose_preservation 20%, outfit_preservation 15%, edge_quality 5%
- Pass: total_score >= 92, Auto-Fail: 인물 수 불일치 / 얼굴 동일성 < 80 (한 명이라도)

| # | 케이스 | 입력 | 예상 결과 | 우선순위 |
|---|--------|------|----------|---------|
| 1 | 2인 그룹 기본 | 2인 소스 + 얼굴 2장 | 두 얼굴 각각 교체, 포즈/착장 보존 | P0 |
| 2 | 5인 그룹 | 5인 소스 + 얼굴 5장 | 5개 얼굴 모두 교체 (face_1~face_5) | P0 |
| 3 | 10인 그룹 | 10인 소스 + 얼굴 10장 | 10개 교체, 경계 품질 특히 확인 | P1 |
| 4 | 10인 초과 요청 | 15인 소스 | 거부 또는 10명 제한 경고 | P1 |
| 5 | 얼굴 겹침 케이스 | 인물들이 겹쳐 있는 소스 | 가능한 범위 내 처리, edge_quality 감점 | P2 |
| 6 | 얼굴 수 불일치 | 3인 소스 + 얼굴 2장 | Auto-Fail (인물 수 불일치) 또는 가능 인원만 처리 | P1 |
| 7 | 위치 보존 확인 | 5인 그룹 | 결과에서 각 인물 위치가 소스와 동일한지 확인 | P0 |
| 8 | 조명 일관성 | 다양한 조명 소스 | 모든 교체 얼굴에 일관된 조명 적용 | P2 |

**검증 항목별 임계값:**

| 항목 | 가중치 | 통과 임계값 | Auto-Fail 조건 |
|------|--------|------------|---------------|
| 전체 얼굴 동일성 | 40% | >= 90 | 한 명이라도 < 80 |
| 얼굴 일관성 | 20% | >= 85 | - |
| 포즈 보존 | 20% | >= 95 | - |
| 착장 보존 | 15% | >= 95 | - |
| 경계 품질 | 5% | >= 80 | - |

---

### 3.3 pose_change (포즈 변경)

**검증 기준 요약:**
- face_identity 30%, outfit_preservation 25%, pose_correctness 25%, physics_plausibility 15%, lighting_consistency 5%
- Pass: total_score >= 88, Auto-Fail: face_identity < 80 / outfit_preservation < 70 / physics_plausibility < 50

**7종 프리셋:**

| 프리셋 키 | 한국어 라벨 | 설명 |
|----------|------------|------|
| `sit_floor` | 앉기 (바닥) | 바닥에 앉아 다리 교차, 편안한 자세 |
| `sit_chair` | 앉기 (의자) | 의자에 앉아 다리 교차, 캐주얼 |
| `lean_wall` | 기대기 (벽) | 벽에 기대어 한쪽 발 올림 |
| `walking` | 걷는 중 | 자연스럽게 걷는 동작 |
| `back_turn` | 뒤돌기 | 카메라 반대로 돌아 어깨 너머 시선 |
| `arms_crossed` | 팔 꼬고 서기 | 팔짱 끼고 자신감 있는 자세 |
| `hand_pocket` | 주머니에 손 | 한 손을 주머니에, 편안한 자세 |

| # | 케이스 | 입력 | 예상 결과 | 우선순위 |
|---|--------|------|----------|---------|
| 1 | 프리셋: sit_floor | 서 있는 소스 + sit_floor | 바닥 앉기 포즈로 변경, 얼굴/착장 보존 | P0 |
| 2 | 프리셋: sit_chair | 서 있는 소스 + sit_chair | 의자 앉기, 의자가 자연스럽게 생성 | P0 |
| 3 | 프리셋: lean_wall | 소스 + lean_wall | 벽 기대기, 물리적으로 자연스러운 자세 | P0 |
| 4 | 프리셋: walking | 서 있는 소스 + walking | 걷는 동작, 자연스러운 팔/다리 움직임 | P0 |
| 5 | 프리셋: back_turn | 정면 소스 + back_turn | 뒤돌아 어깨 너머 시선 | P1 |
| 6 | 프리셋: arms_crossed | 소스 + arms_crossed | 팔짱 끼기, 착장 로고 가림 여부 확인 | P1 |
| 7 | 프리셋: hand_pocket | 소스 + hand_pocket | 주머니에 손, 손가락 자연스러움 확인 | P1 |
| 8 | 커스텀 포즈 (물리 가능) | 소스 + "standing on one leg, arms outstretched" | 물리 가능 포즈 생성, physics >= 80 | P1 |
| 9 | 커스텀 포즈 (물리 불가능) | 소스 + "floating horizontally in the air" | physics_plausibility < 50 -> Auto-Fail 또는 거부 | P2 |
| 10 | Auto-Fail: 얼굴 변경 | 소스 + 어떤 포즈 | 포즈 변경 시 얼굴 동일성 95% 이상 유지 확인 | P0 |

**검증 항목별 임계값:**

| 항목 | 가중치 | 통과 임계값 | Auto-Fail 임계값 |
|------|--------|------------|----------------|
| 얼굴 동일성 | 30% | >= 90 | < 80 |
| 착장 보존 | 25% | >= 90 | < 70 |
| 포즈 정확도 | 25% | >= 85 | - |
| 물리 타당성 | 15% | >= 80 | < 50 |
| 조명 일관성 | 5% | >= 75 | - |

---

### 3.4 pose_copy (포즈 따라하기)

**검증 기준 요약:**
- pose_similarity 50%, face_preservation 20%, outfit_preservation 20%, composition_match 10%
- Pass: total_score >= 92, Auto-Fail: pose_similarity < 70 / face_preservation < 80 / outfit_preservation < 80

| # | 케이스 | 입력 | 예상 결과 | 우선순위 |
|---|--------|------|----------|---------|
| 1 | 기본 레퍼런스 복제 | 소스 인물 + 레퍼런스(전신 서기) | 레퍼런스 포즈 그대로 복제, 얼굴/착장 소스 유지 | P0 |
| 2 | 앉은 자세 복제 | 소스(서 있음) + 레퍼런스(앉은 자세) | 앉은 포즈로 변경, 자연스러운 드레이핑 | P0 |
| 3 | 극단적 포즈 차이 | 소스(서 있음) + 레퍼런스(누운 자세) | pose_similarity 최대화 시도, 탈락 시 재시도 | P1 |
| 4 | 구도 일치 확인 | 소스 + 레퍼런스(로우앵글 전신) | 생성 결과 앵글/프레이밍 레퍼런스와 일치 여부 | P0 |
| 5 | 배경 보존 옵션 | 소스(배경 있음) + 레퍼런스 | 배경 소스 것 유지 (composition_match 기준) | P1 |
| 6 | 배경 변경 옵션 | 소스 + 레퍼런스(다른 배경) | 레퍼런스 배경 분위기 반영 (지시 따라) | P2 |
| 7 | 로고 착장 포함 | MLB 로고 착장 소스 + 레퍼런스 | 포즈 변경 후에도 로고 정확도 유지 | P0 |
| 8 | 구도 불일치 케이스 | 소스(세로 프레임) + 레퍼런스(가로 프레임) | composition_match 감점 예상, 경고 출력 | P2 |

**검증 항목별 임계값:**

| 항목 | 가중치 | 통과 임계값 | Auto-Fail 임계값 |
|------|--------|------------|----------------|
| 포즈 유사도 | 50% | >= 85 | < 70 |
| 얼굴 보존 | 20% | >= 90 | < 80 |
| 착장 보존 | 20% | >= 90 | < 80 |
| 구도 일치 | 10% | >= 80 | - |

---

### 3.5 outfit_swap (착장 스왑)

**검증 기준 요약:**
- outfit_accuracy 35%, face_identity 25%, pose_preservation 25%, outfit_draping 10%, background_preservation 5%
- Pass: total_score >= 92, Auto-Fail: face_identity < 80 / pose_preservation < 90 / outfit_accuracy < 70

| # | 케이스 | 입력 | 예상 결과 | 우선순위 |
|---|--------|------|----------|---------|
| 1 | 전신샷 착장 교체 | 소스(전신) + 착장(전신) | 착장만 교체, 얼굴/포즈/배경 보존 | P0 |
| 2 | 반신샷 착장 교체 | 소스(반신) + 착장(상의+하의) | 보이는 부분만 교체, 자연스러운 하단 처리 | P1 |
| 3 | 상반신만 착장 교체 | 소스(전신) + 착장(상의만) | 상의만 교체, 하의는 소스 그대로 유지 | P1 |
| 4 | 누끼 이미지 착장 입력 | 소스 + 착장(누끼/흰배경) | 착장 색상/로고 정확도 집중 검수 | P0 |
| 5 | 착용샷 이미지 착장 입력 | 소스 + 착장(다른 모델 착용) | 색상/로고/디테일 추출 정확도 확인 | P0 |
| 6 | MLB 로고 정확도 | 소스 + MLB 로고 착장 | 로고 위치/크기/색상/텍스트 완전 일치 | P0 |
| 7 | 다중 착장 아이템 | 소스 + 착장(상의+팬츠+아우터) | 3개 아이템 모두 정확히 재현 | P0 |
| 8 | 착장 색상 변형 방지 | 빨간 착장 소스 | 생성 결과에서 색상 변형(핑크, 주황) 없는지 확인 | P0 |
| 9 | Auto-Fail: 착장 누락 | 3피스 착장 중 1피스 누락 | `missing_items` 탐지 -> Auto-Fail | P0 |
| 10 | 배경 유지 확인 | 배경 있는 소스 + 착장 | 배경 완전 보존 (background_preservation >= 90) | P1 |

**검증 항목별 임계값:**

| 항목 | 가중치 | 통과 임계값 | Auto-Fail 임계값 |
|------|--------|------------|----------------|
| 착장 정확도 | 35% | >= 90 | < 70 (착장 누락 포함) |
| 얼굴 동일성 | 25% | >= 95 | < 80 |
| 포즈 유지 | 25% | >= 95 | < 90 |
| 착장 자연스러움 | 10% | >= 80 | - |
| 배경 유지 | 5% | >= 90 | - |

---

### 3.6 ecommerce (이커머스)

**검증 기준 요약:**
- outfit_accuracy 40%, face_identity 20%, background_compliance 15%, pose_correctness 15%, commercial_quality 10%
- Pass: total_score >= 85, Auto-Fail: outfit_accuracy < 70 / face_identity < 40 / background_compliance < 60

**포즈 프리셋 5종:**

| 프리셋 키 | 프레이밍 | 앵글 | 설명 |
|----------|---------|------|------|
| `front_standing` | 전신 (FS) | 정면 | 자연스럽게 서기, 양팔 옆 |
| `front_casual` | 전신 (FS) | 정면 | 캐주얼 서기, 한 손 허리 |
| `side_profile` | 전신 (FS) | 측면 | 옆 프로필, 카메라 쪽 살짝 시선 |
| `back_view` | 전신 (FS) | 뒷면 | 뒷면, 착장 백 디테일 표현 |
| `detail_closeup` | 반신 (MS) | 정면 | 상반신, 착장 디테일 집중 |

**배경 프리셋 4종 (중립 배경만 허용):**

| 프리셋 키 | 설명 |
|----------|------|
| `white_studio` | 화이트 스튜디오 배경, 전문 조명 |
| `gray_studio` | 그레이 스튜디오 배경, 약간 드라마틱 |
| `minimal_indoor` | 미니멀 실내, 자연 창문 조명 |
| `outdoor_urban` | 도심 외부, 자연 데이라이트 |

| # | 케이스 | 입력 | 예상 결과 | 우선순위 |
|---|--------|------|----------|---------|
| 1 | 프리셋: front_standing | 얼굴 + 착장 + front_standing | 정면 전신 자연스러운 서기 | P0 |
| 2 | 프리셋: front_casual | 얼굴 + 착장 + front_casual | 캐주얼 자세, 한 손 허리 | P0 |
| 3 | 프리셋: side_profile | 얼굴 + 착장 + side_profile | 측면 전신, 착장 실루엣 명확 | P0 |
| 4 | 프리셋: back_view | 얼굴 + 착장 + back_view | 뒷면 전신, 백 포켓/등 디테일 | P0 |
| 5 | 프리셋: detail_closeup | 얼굴 + 착장 + detail_closeup | 반신 클로즈업, 착장 디테일 선명 | P0 |
| 6 | 배경: white_studio | 얼굴 + 착장 + white_studio | 클린 화이트 배경, 균일 조명 | P0 |
| 7 | 배경: gray_studio | 얼굴 + 착장 + gray_studio | 그레이 배경, 세련된 분위기 | P1 |
| 8 | 배경: minimal_indoor | 얼굴 + 착장 + minimal_indoor | 미니멀 실내, 라이프스타일 감성 | P1 |
| 9 | 배경: outdoor_urban | 얼굴 + 착장 + outdoor_urban | 도심 야외, 스트릿 감성 | P1 |
| 10 | 유채색 배경 거부 | 얼굴 + 착장 + "vivid blue background" | background_compliance < 60 -> Auto-Fail | P0 |
| 11 | MLB 착장 정확도 | MLB 로고 착장 + 이커머스 포즈 | 로고 color/text/position 완전 일치 | P0 |
| 12 | 브랜드 특화 배경 거부 | 착장 + "NYC alleyway graffiti wall" | background_compliance 저하, 재시도 유도 | P1 |

**검증 항목별 임계값:**

| 항목 | 가중치 | 통과 임계값 | Auto-Fail 임계값 |
|------|--------|------------|----------------|
| 착장 정확도 | 40% | >= 85 | < 70 |
| 얼굴 동일성 | 20% | >= 70 | < 40 |
| 배경 준수 | 15% | >= 90 | < 60 |
| 포즈 정확도 | 15% | >= 80 | - |
| 상업적 품질 | 10% | >= 85 | - |

---

## 4. 검증 기준 요약표

| 워크플로 | Pass 총점 조건 | 개별 기준 | Auto-Fail 조건 |
|---------|--------------|----------|---------------|
| face_swap | >= 95 | 5개 기준 모두 통과 | face_identity < 80 |
| multi_face_swap | >= 92 | 5개 기준 모두 통과 | 한 명이라도 face < 80 / 인물 수 불일치 / 위치 뒤바뀜 |
| pose_change | >= 88 | 5개 기준 모두 통과 | face < 80 / outfit < 70 / physics < 50 |
| pose_copy | >= 92 | 4개 기준 모두 통과 | pose_similarity < 70 / face < 80 / outfit < 80 |
| outfit_swap | >= 92 | 5개 기준 모두 + missing_items 없음 | face < 80 / pose < 90 / outfit < 70 / 착장 누락 |
| ecommerce | >= 85 | 5개 기준 모두 통과 | outfit < 70 / face < 40 / background < 60 |

---

## 5. 테스트 파일 구조

```
tests/
├── face_swap/
│   ├── test_basic.py              # P0 기본 케이스
│   ├── test_edge_cases.py         # 측면 얼굴, 가림, 얼굴 없는 소스
│   └── test_validation.py         # 검증기 단위 테스트 (Mock)
│
├── multi_face_swap/
│   ├── test_2person.py            # 2인 그룹 기본
│   ├── test_5person.py            # 5인 그룹
│   └── test_limits.py             # 10인 초과 거부, 얼굴 수 불일치
│
├── pose_change/
│   ├── test_presets.py            # 7종 프리셋 전체 테스트
│   ├── test_custom.py             # 커스텀 포즈 (가능/불가능)
│   └── test_physics.py            # physics_plausibility 집중 테스트
│
├── pose_copy/
│   ├── test_basic.py              # 기본 레퍼런스 복제
│   ├── test_extreme.py            # 극단적 포즈 차이 케이스
│   └── test_background.py         # 배경 보존/변경 옵션
│
├── outfit_swap/
│   ├── test_basic.py              # 전신/반신/상반신
│   ├── test_input_types.py        # 누끼/착용샷 입력
│   ├── test_mlb_logo.py           # MLB 로고 정확도
│   └── test_validation.py         # 검증기 단위 테스트
│
├── ecommerce/
│   ├── test_presets.py            # 포즈 프리셋 5종
│   ├── test_background.py         # 배경 프리셋 4종 + 유채색 거부
│   └── test_commercial.py         # 상업적 품질, MLB 착장 정확도
│
└── integration/
    ├── test_6workflows.py          # 6개 워크플로 통합 E2E 테스트
    └── test_validator_registry.py  # ValidatorRegistry 통합 테스트
```

### 테스트 파일 필수 패턴

```python
import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# .env 로드 (반드시 core 모듈 import 전에)
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# 이모지 사용 금지 (Windows cp949 이슈)
# print("[OK] 완료") - 영어 상태 메시지 사용

# 옵션은 core/options.py에서 import
from core.options import get_workflow_defaults
```

---

## 6. 실행 계획

| 단계 | 내용 | 대상 테스트 | 비고 |
|------|------|------------|------|
| 1 | Unit Test | `test_validation.py` 파일들 | Mock API, 빠른 실행 |
| 2 | Integration Test | 각 워크플로 기본 케이스 (P0) | 1K 해상도, API 키 로테이션 |
| 3 | E2E Test | `integration/test_6workflows.py` | 2K 해상도, 전체 파이프라인 |
| 4 | QA 검수 | Visual Test (P0 케이스 결과물) | 사람 직접 검수 |

### 실행 우선순위

1. **P0 케이스 우선** - 핵심 기능 및 Auto-Fail 동작 확인
2. **P1 케이스** - 엣지 케이스 및 프리셋 전체 검증
3. **P2 케이스** - 경계 조건, 예외 처리 확인

### 비용 예산 (1K 기준, 장당 190원)

| 단계 | 예상 생성 수 | 예상 비용 |
|------|------------|---------|
| Unit Test | 0장 (Mock) | 0원 |
| Integration Test | 워크플로당 5장 x 6 = 30장 | 5,700원 |
| E2E Test | 워크플로당 10장 x 6 = 60장 | 11,400원 |
| QA Visual Test | 30장 (2K) | 5,700원 |
| **합계** | **120장** | **약 22,800원** |

---

## 7. 리스크 및 대응

| 리스크 | 영향 | 발생 가능성 | 대응 방안 |
|--------|------|------------|---------|
| API Rate Limit (429) | 테스트 중단 | 높음 | `get_next_api_key()` 로테이션, `(attempt+1)*5초` 대기 |
| VLM 응답 불일치 | 오탐/미탐 | 중간 | 임계값 조정, 재시도 횟수 증가 |
| JSON 파싱 실패 | 검수 오류 | 낮음 | fallback result 반환, 에러 로깅 |
| 물리적 불가능 포즈 생성 | physics_plausibility 탈락 반복 | 중간 | 커스텀 포즈 가이드라인 제공 |
| 착장 색상 드리프트 | outfit_accuracy 탈락 | 중간 | 온도(temperature) 0.2~0.25 유지 |
| VLM 과도한 엄격함 | 합격률 저하 | 낮음 | 검수 프롬프트 step-by-step 형식 강화 |
| Windows 인코딩 이슈 | 이모지 출력 오류 | 낮음 | 테스트 코드에 이모지 사용 금지 |

---

## 8. 검수 결과 출력 표준 (참고)

모든 워크플로 검수 결과는 아래 형식을 따른다 (CLAUDE.md 기준).

```markdown
## 검수 결과

| 항목 | 점수 | 기준 | 통과 |
|------|------|------|------|
| 착장 정확도 | 92 | >=90 | O |
| 얼굴 동일성 | 95 | >=95 | O |
| 포즈 유지 | 97 | >=95 | O |
| 착장 자연스러움 | 85 | >=80 | O |
| 배경 유지 | 93 | >=90 | O |

**총점**: 93/100 | **등급**: A | **판정**: 통과
```

---

## 9. 관련 문서

| 문서 | 경로 |
|------|------|
| 프로젝트 규칙 | `.claude/CLAUDE.md` |
| 워크플로 템플릿 | `.claude/rules/workflow-template.md` |
| VLM 프롬프트 규칙 | `.claude/rules/vlm-prompt-rules.md` |
| 착장 분석 규칙 | `.claude/rules/outfit-analysis-rules.md` |
| 검증기 베이스 | `core/validators/base.py` |
| 검증기 레지스트리 | `core/validators/registry.py` |
| 통합 생성기 | `core/generators/unified.py` |
