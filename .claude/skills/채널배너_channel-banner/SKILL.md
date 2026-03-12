---
name: channel-banner
description: 채널별 광고 배너 자동 생성 - Figma MCP 기반 전 채널 지원
user-invocable: true
trigger-keywords: ["배너", "채널배너", "banner", "구글배너", "네이버배너", "카카오배너", "메타배너", "유튜브배너", "광고배너", "GDN"]
---

# 채널 배너 자동 생성

> 채널명만 말하면 해당 채널의 모든 배너 사이즈를 Figma에 자동 생성

---

## 핵심 컨셉

사용자가 "네이버 배너 만들어"라고 하면:
1. 채널 스펙 DB에서 네이버 배너 사이즈 전체 로드
2. 각 사이즈에 맞는 레이아웃 패턴 자동 선택
3. Figma MCP로 배너 프레임 + 이미지 + 텍스트 자동 생성

---

## 지원 채널 & 배너 사이즈

### 네이버 (7 sizes)

| ID | 사이즈 | 라벨 | 레이아웃 |
|----|--------|------|----------|
| shopping_main | 800x800 | 쇼핑 메인 | 정방형 |
| shopping_banner | 1200x630 | 쇼핑 배너 | 가로 |
| gfa_feed | 1200x628 | GFA 피드 | 가로 |
| gfa_square | 800x800 | GFA 정방형 | 정방형 |
| gfa_native | 600x500 | GFA 네이티브 | 가로 |
| brand_search | 750x200 | 브랜드검색 | 극가로 |
| mobile_banner | 320x100 | 모바일 배너 | 극가로 |

### 구글 GDN (8 sizes)

| ID | 사이즈 | 라벨 | 레이아웃 |
|----|--------|------|----------|
| leaderboard | 728x90 | 리더보드 | 극가로 |
| medium_rect | 300x250 | 미디엄 렉탱글 | 가로 |
| large_rect | 336x280 | 라지 렉탱글 | 가로 |
| skyscraper | 160x600 | 스카이스크래퍼 | 세로 |
| half_page | 300x600 | 하프페이지 | 세로 |
| mobile | 320x50 | 모바일 배너 | 극가로 |
| large_leader | 970x90 | 라지 리더보드 | 극가로 |
| responsive | 1200x628 | 반응형 디스플레이 | 가로 |

### 카카오 (5 sizes)

| ID | 사이즈 | 라벨 | 레이아웃 |
|----|--------|------|----------|
| moment_square | 1080x1080 | 모먼트 정방형 | 정방형 |
| moment_feed | 1200x628 | 모먼트 피드 | 가로 |
| bizboard | 1029x258 | 비즈보드 | 극가로 |
| bizboard_wide | 1029x516 | 비즈보드 와이드 | 가로 |
| talk_channel | 720x720 | 톡채널 | 정방형 |

### 메타 - 인스타/페북 (5 sizes)

| ID | 사이즈 | 라벨 | 레이아웃 |
|----|--------|------|----------|
| feed_square | 1080x1080 | 피드 정방형 (1:1) | 정방형 |
| feed_portrait | 1080x1350 | 피드 세로 (4:5) | 세로 |
| story | 1080x1920 | 스토리/릴스 (9:16) | 극세로 |
| carousel | 1080x1080 | 카루셀 (1:1) | 정방형 |
| link_cover | 1200x628 | 링크 커버 | 가로 |

### 유튜브 (5 sizes)

| ID | 사이즈 | 라벨 | 레이아웃 |
|----|--------|------|----------|
| display | 300x250 | 디스플레이 광고 | 가로 |
| overlay | 480x70 | 오버레이 | 극가로 |
| thumbnail | 1280x720 | 썸네일 (16:9) | 가로 |
| channel_banner | 2560x1440 | 채널 배너 | 가로 |
| shorts_cover | 1080x1920 | Shorts 커버 (9:16) | 극세로 |

---

## 레이아웃 패턴 (자동 선택)

| 카테고리 | 적용 조건 | 패턴 |
|----------|----------|------|
| 극가로 (ultra_wide) | 비율 4:1 이상 | [로고][텍스트][CTA] 수평 |
| 가로 (landscape) | 비율 1.2:1~4:1 | [이미지 60%][텍스트+CTA 40%] |
| 정방형 (square) | 비율 ~1:1 | [이미지 65%][텍스트+CTA 하단] |
| 세로 (portrait) | 비율 1:1.5~2.5 | [이미지 55%][텍스트 30%][CTA 15%] |
| 극세로 (full_portrait) | 비율 9:16 | [풀이미지][하단 오버레이] |

---

## 워크플로

```
1. 사용자: "네이버 배너 만들어" (또는 "전 채널 배너")
   |
   v
2. Claude: 채널 스펙 로드 (db/channel_specs.json)
   |
   v
3. Claude: [AskUserQuestion] 필수 정보 수집
   - 제품 이미지 (경로 또는 URL)
   - 상품명
   - 가격 (선택)
   - CTA 텍스트 (기본: "자세히 보기")
   - 할인율 (선택)
   |
   v
4. Claude: BannerFigmaBuilder로 빌드 시퀀스 생성
   |
   v
5. Claude: Figma MCP 도구 순차 호출
   - join_channel  → Figma 연결
   - create_frame  → 배너 프레임
   - set_node_image_fill → 제품 이미지
   - create_text   → 상품명/가격/CTA
   |
   v
6. 결과: Figma에 해당 채널 모든 배너 사이즈 생성 완료
```

---

## 필수 입력

| 입력 | 필수 | 설명 |
|------|------|------|
| 채널 | O | naver/google/kakao/meta/youtube/all |
| 제품 이미지 | O | 배너에 사용할 제품/모델 이미지 경로 |
| 상품명 | O | 배너에 표시할 상품명 |
| 가격 | X | 가격 표시 (예: "59,000원") |
| CTA | X | 버튼 텍스트 (기본: "자세히 보기") |
| 할인율 | X | 할인 뱃지 (예: "30%") |

---

## 코드 모듈

| 파일 | 역할 |
|------|------|
| `db/channel_specs.json` | 채널별 배너 사이즈 DB |
| `db/banner_templates.json` | 레이아웃 패턴 + 영역 정의 |
| `core/banner/layout_engine.py` | 레이아웃 계산 엔진 |
| `core/banner/figma_banner_builder.py` | Figma MCP 시퀀스 생성기 |

---

## 채널별 배너 수

| 채널 | 배너 수 |
|------|--------|
| 네이버 | 7종 |
| 구글 GDN | 8종 |
| 카카오 | 5종 |
| 메타 | 5종 |
| 유튜브 | 5종 |
| **전 채널 (all)** | **30종** |

---

## 사용 예시

```
사용자: "네이버 배너 만들어"
Claude:
  1. 채널 스펙 로드 → 네이버 7종 배너
  2. 필수 정보 질문 (상품명, 이미지 등)
  3. Figma 연결 확인
  4. 7종 배너 자동 생성
  5. 결과 안내

사용자: "전 채널 배너 만들어"
Claude:
  1. 5개 채널 전체 로드 (30종 배너)
  2. 필수 정보 질문
  3. Figma 연결 확인
  4. 30종 배너 자동 생성
  5. 채널별 결과 안내
```

---

## Figma MCP 빌드 시퀀스

각 배너 사이즈에 대해 다음 순서로 호출:

```python
# 1. 배너 프레임 생성
create_frame(x, y, width, height, name="{채널}_{배너ID}")

# 2. 배경 설정
set_fill_color(frame_id, r, g, b)  # 브랜드 배경색

# 3. 이미지 영역 생성
create_rectangle(x, y, img_width, img_height, parent=frame_id)
set_node_image_fill(rect_id, imageUrl=product_image_url)

# 4. 텍스트 레이어 생성
create_text(x, y, text=product_name, fontSize, fontWeight=700)
create_text(x, y, text=price, fontSize)       # 가격 (선택)
create_text(x, y, text=cta_text, fontSize)    # CTA

# 5. 할인 뱃지 (선택)
create_frame(x, y, badge_w, badge_h)          # 뱃지 프레임
set_fill_color(badge_id, r=0.77, g=0.12, b=0.23)  # MLB 레드
create_text(x, y, text=discount_text)
```

---

## 브랜드 색상 (db/channel_specs.json 참조)

| 브랜드 | Primary | Secondary | Accent |
|--------|---------|-----------|--------|
| MLB | #000000 | #FFFFFF | #C41E3A |

---

**버전**: 1.0.0
**작성일**: 2026-03-04
**관련 DB**: `db/channel_specs.json`
