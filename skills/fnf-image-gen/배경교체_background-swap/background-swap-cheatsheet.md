# 배경교체 프롬프트 치트시트

> v1.0.0 | 최종 업데이트: 2026-02-11

---

## 핵심 개념

### ONE UNIT 원칙

인물 + 차량 + 오브젝트 = **하나의 단위**로 취급

```
WRONG: "인물 보존" + "차량 보존" (개별 지시)
RIGHT: "FOREGROUND SUBJECT = 인물+차량+오브젝트" (단일 단위)
```

### 보존 우선순위

| 순위 | 항목 | 비고 |
|------|------|------|
| 1 | 인물 크기 | 1:1 유지 (축소 절대 금지) |
| 2 | 얼굴 동일성 | 같은 사람 |
| 3 | 착장 | 색상/로고/디테일 |
| 4 | 차량/소품 | 있으면 그대로 |
| 5 | 포즈/자세 | 관절 위치 |

---

## 배경 스타일 프리셋

### 콘크리트 (4종)

| ID | 한글 | Prompt |
|----|------|--------|
| `1_raw` | 로우콘크리트 | `Raw exposed concrete wall with visible texture and form marks. Industrial, authentic, slightly weathered. Like a construction site or parking garage.` |
| `2_smooth` | 스무스콘크리트 | `Smooth polished concrete wall, minimalist and clean. Modern architectural finish, subtle gray tones. Like a contemporary museum exterior.` |
| `3_metal` | 메탈믹스 | `Concrete wall with metal elements - steel beams, industrial fixtures. Urban industrial aesthetic, mixed materials. Like a modern warehouse district.` |
| `4_brutalist` | 브루탈리즘 | `Brutalist architecture style - massive concrete forms, geometric shapes. Bold, monumental, dramatic shadows. Like a 70s government building or university.` |

### 도시 (7종)

| ID | 한글 | Prompt |
|----|------|--------|
| `california_affluent` | 캘리포니아부촌 | `Sunny California affluent neighborhood. Warm golden light, palm trees, clean sidewalks, upscale residential area. Beverly Hills / Malibu / Bel Air aesthetic.` |
| `california_retro` | 캘리포니아레트로 | `1970s California retro aesthetic. Warm film tones, vintage signage, retro architecture. Palm Springs / Venice Beach vintage vibe.` |
| `london_affluent` | 런던부촌 | `Upscale London neighborhood. Classic Georgian townhouses, brick facades, manicured gardens. Mayfair / Kensington / Chelsea aesthetic.` |
| `london_mayfair` | 런던메이페어 | `London Mayfair district. Elegant storefronts, wrought iron railings, cobblestone details. Luxury retail and residential mix.` |
| `hollywood_simple` | 할리우드심플 | `Clean Hollywood urban setting. Modern American commercial buildings, clean lines. Subtle urban backdrop, not distracting.` |
| `tokyo_shibuya` | 도쿄시부야 | `Tokyo Shibuya crossing area. Neon lights, dense urban, modern Japanese architecture. Dynamic, energetic atmosphere.` |
| `paris_marais` | 파리마레 | `Paris Le Marais district. Historic stone buildings, ornate balconies, charming streets. Artistic, bohemian atmosphere.` |

### 스튜디오 (4종)

| ID | 한글 | Prompt |
|----|------|--------|
| `white_cyclorama` | 화이트싸이 | `Pure white studio cyclorama background. Seamless white curve, soft even lighting. Clean, professional fashion photography setup.` |
| `gray_seamless` | 그레이시폼 | `Medium gray seamless paper background. Neutral, versatile, professional. Classic editorial photography setup.` |
| `black_dramatic` | 블랙드라마틱 | `Black studio background with dramatic lighting. High contrast, moody, editorial. Fashion magazine cover aesthetic.` |
| `natural_window` | 내추럴윈도우 | `Studio with large natural window light. Soft directional light, subtle shadows. Bright, airy, lifestyle photography feel.` |

---

## VFX 물리 분석 (6대 영역)

배경 생성 전 원본 이미지에서 추출하는 물리 제약. 프롬프트 조립 시 참조.

| 영역 | 추출값 | 프롬프트 활용 |
|------|--------|--------------|
| **Camera Geometry** | horizon_y (0~1), perspective, focal_length_vibe | 원근/소실점 매칭 |
| **Lighting Physics** | direction_clock (1~12시), elevation, softness, color_temp | 조명 방향/강도 매칭 |
| **Pose Dependency** | pose_type, support_required, support_direction | 지지대 필요 여부 |
| **Installation Logic** | prop_detected, is_fixed_prop, forbidden_contexts | 소품 배치 규칙 |
| **Physics Anchors** | contact_points [x,y], shadow_casting_direction | 접지/그림자 정합 |
| **Semantic Style** | vibe, recommended_locations | 분위기 매칭 |

### Pose Dependency 상세

| pose_type | support_required | support_type 예시 |
|-----------|------------------|-------------------|
| standing | false | - |
| sitting | true | chair, bench, ground |
| leaning | true | wall, pillar, railing |
| crouching | false | - |
| lying | true | ground, bed |

---

## ONE UNIT 보존 레벨

| 레벨 | 사용 시점 | 프롬프트 상세도 |
|------|----------|----------------|
| `BASIC` | 인물만 있을 때 | 기본 보존 |
| `DETAILED` | 차량 감지 시 (자동 업그레이드) | 차량+인물 ONE UNIT |
| `FULL` | 복잡한 소품/다중 오브젝트 | 최대 보존 |

---

## 참조 이미지 유형 (reference_type)

| 유형 | 용도 | 프롬프트에 추출하는 요소 |
|------|------|-------------------------|
| `style` | 조명/분위기 참조 | lighting style, color palette, mood |
| `pose` | 포즈/구도 참조 | pose, framing, camera angle |
| `background` | 배경 환경 참조 | environment, depth, ambient lighting |
| `clothing` | 착장 보존 (가장 상세) | garment shape, colors, logo, texture, fit |
| `all` | 전체 참조 | lighting + colors + composition + mood + style |

---

## 금지 조합

| # | 조합 | 이유 | 대안 |
|---|------|------|------|
| 1 | sitting 포즈 + 지지대 없는 배경 | 앉을 곳 없음 | standing 또는 배경 변경 |
| 2 | leaning 포즈 + 열린 공간 배경 | 기댈 곳 없음 | 벽/기둥 있는 배경 |
| 3 | 야외 배경 + 스튜디오 조명 | 조명 불일치 | 자연광 또는 배경 변경 |
| 4 | 차량 포함 + 차량 없는 배경 | ONE UNIT 깨짐 | 배경에 주차 공간 포함 |
| 5 | 골든아워 + 쿨톤 인물 | 색온도 충돌 | 조명 일치 필요 |

---

## 네거티브 프롬프트

### 기본 (항상 적용)

```
shrinking person, zooming out, different face, changed clothing
```

### 조건부 추가

| 조건 | 추가 네거티브 |
|------|--------------|
| 차량 있음 | `removing car, hiding vehicle, different car color` |
| sitting 포즈 | `standing up, different pose` |
| leaning 포즈 | `standing straight, no support` |

---

**데이터 소스:** core/background_swap/presets.py + templates.py (2026-02-11)
