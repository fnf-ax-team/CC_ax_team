"""
트렌드 집계 + HTML 리포트 생성 모듈

TrendAnalyzer가 생성한 개별 JSON 결과들을 집계하여
패션 트렌드 리포트를 HTML로 생성한다.

사용법:
    from core.trend_analysis.aggregator import TrendAggregator

    aggregator = TrendAggregator(results_dir="path/to/results")
    report_path = aggregator.generate_report()
"""

import json
import html as html_module
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


# ============================================================
# 상수
# ============================================================

# 컬러 스와치용 색상 매핑
COLOR_MAP = {
    "black": "#000000",
    "white": "#FFFFFF",
    "navy": "#1B2A4A",
    "beige": "#D4C5A9",
    "brown": "#8B6914",
    "grey": "#808080",
    "gray": "#808080",
    "cream": "#FFFDD0",
    "olive": "#808000",
    "burgundy": "#800020",
    "camel": "#C19A6B",
    "red": "#DC143C",
    "blue": "#2E5FCC",
    "green": "#2E8B57",
    "pink": "#FF69B4",
    "lavender": "#B57EDC",
    "purple": "#B57EDC",
    "yellow": "#FFD700",
    "orange": "#FF8C00",
    "khaki": "#C3B091",
    "denim_blue": "#4B6F95",
    "charcoal": "#36454F",
}

# 스킵 처리할 값 목록 (없는 항목 표기들)
_SKIP_VALUES = {"", "none", "없음", "null", "n/a", "not_applicable"}

# 아이템 카테고리 한국어 매핑
_CATEGORY_KR = {
    "outer": "아우터",
    "top": "상의",
    "bottom": "하의",
    "dress": "원피스",
    "shoes": "신발",
    "bag": "가방",
    "headwear": "모자",
    "accessories": "액세서리",
}

# 무드 한국어 매핑
_MOOD_KR = {
    "clean_minimal": "클린 미니멀",
    "street_casual": "스트릿 캐주얼",
    "sporty": "스포티",
    "romantic": "로맨틱",
    "gorpcore": "고프코어",
    "y2k": "Y2K",
    "preppy": "프레피",
    "grunge": "그런지",
    "classic": "클래식",
    "bohemian": "보헤미안",
    "athleisure": "애슬레저",
}

# 시즌 한국어 매핑
_SEASON_KR = {
    "spring": "봄",
    "summer": "여름",
    "fall": "가을",
    "winter": "겨울",
    "transitional": "환절기",
}


# ============================================================
# 유틸리티 함수
# ============================================================


def _is_valid_value(val: Any) -> bool:
    """유효한 값인지 확인 (빈 값, none 등 제외)"""
    if val is None:
        return False
    if isinstance(val, str):
        return val.strip().lower() not in _SKIP_VALUES
    return True


def _normalize_value(val: str) -> str:
    """값 정규화 (소문자, 공백 제거)"""
    if not isinstance(val, str):
        return str(val)
    return val.strip().lower()


def _extract_combinations(result: Dict) -> Optional[Tuple[str, ...]]:
    """
    각 이미지의 착장 아이템 조합 추출

    상의/하의/아우터/신발 조합을 정렬된 튜플로 반환.
    유효한 아이템이 2개 미만이면 None 반환.
    """
    items_data = result.get("items", {})
    items = []
    for category in ["outer", "top", "bottom", "dress", "shoes"]:
        val = items_data.get(category, "")
        if _is_valid_value(val):
            items.append(_normalize_value(val))

    if len(items) < 2:
        return None

    return tuple(sorted(items))


def _safe_percentage(count: int, total: int) -> float:
    """안전한 퍼센트 계산 (0 나누기 방지)"""
    if total <= 0:
        return 0.0
    return round(count / total * 100, 1)


# ============================================================
# TrendAggregator 클래스
# ============================================================


class TrendAggregator:
    """
    트렌드 집계 + HTML 리포트 생성기

    TrendAnalyzer의 개별 JSON 결과들을 읽어
    전체 트렌드를 집계하고 시각적 HTML 리포트를 생성한다.
    """

    def __init__(self, results_dir: str):
        """
        Args:
            results_dir: TrendAnalyzer의 results/ 폴더 경로
        """
        self.results_dir = Path(results_dir)
        if not self.results_dir.exists():
            raise FileNotFoundError(f"Results directory not found: {results_dir}")

        # 상위 output 디렉토리 (results/ 의 부모)
        self.output_dir = self.results_dir.parent

        # 로드된 결과 캐시
        self._results: List[Dict] = []
        self._aggregated: Optional[Dict] = None

    # ----------------------------------------------------------
    # 공개 메서드
    # ----------------------------------------------------------

    def load_results(self) -> List[Dict]:
        """
        모든 개별 JSON 결과 로드

        Returns:
            정상 분석된 결과 목록 (status='ok'인 것만)
        """
        self._results = []
        skipped = 0
        errors = 0

        for json_path in sorted(self.results_dir.glob("*.json")):
            # progress.json, aggregated.json 등 메타 파일 제외
            if json_path.name in ("progress.json", "aggregated.json"):
                continue

            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                errors += 1
                continue

            status = data.get("status", "")
            if status == "ok":
                self._results.append(data)
            elif status == "skip":
                skipped += 1
            else:
                errors += 1

        total_loaded = len(self._results)
        print(
            f"[LOAD] {total_loaded} results loaded "
            f"(skipped: {skipped}, errors: {errors})"
        )
        return self._results

    def aggregate(self) -> Dict[str, Any]:
        """
        전체 집계 실행

        Returns:
            집계 결과 딕셔너리
        """
        if not self._results:
            self.load_results()

        if not self._results:
            return {"summary": {"total": 0, "analyzed": 0, "skipped": 0}}

        results = self._results
        total = len(results)

        # 카테고리별 Counter
        item_counters = {cat: Counter() for cat in _CATEGORY_KR}
        color_main = Counter()
        color_sub = Counter()
        color_scheme = Counter()
        top_fit = Counter()
        bottom_fit = Counter()
        mood_primary = Counter()
        mood_secondary = Counter()
        season_counter = Counter()
        setting_counter = Counter()
        gender_counter = Counter()
        tuck_counter = Counter()
        layering_counter = Counter()
        combination_counter = Counter()

        # 인플루언서별 통계
        influencer_data: Dict[str, Dict] = {}

        for r in results:
            # --- 아이템 집계 ---
            items = r.get("items", {})
            for cat in _CATEGORY_KR:
                val = items.get(cat, "")
                if _is_valid_value(val):
                    item_counters[cat][_normalize_value(val)] += 1

            # --- 컬러 집계 ---
            colors = r.get("colors", {})
            mc = colors.get("main_color", "")
            if _is_valid_value(mc):
                color_main[_normalize_value(mc)] += 1

            sub_colors = colors.get("sub_colors", [])
            if isinstance(sub_colors, list):
                for sc in sub_colors:
                    if _is_valid_value(sc):
                        color_sub[_normalize_value(sc)] += 1

            cs = colors.get("color_scheme", "")
            if _is_valid_value(cs):
                color_scheme[_normalize_value(cs)] += 1

            # --- 실루엣 집계 ---
            sil = r.get("silhouette", {})
            tf = sil.get("top_fit", "")
            if _is_valid_value(tf):
                top_fit[_normalize_value(tf)] += 1
            bf = sil.get("bottom_fit", "")
            if _is_valid_value(bf):
                bottom_fit[_normalize_value(bf)] += 1

            # --- 무드 집계 ---
            mood = r.get("mood", {})
            mp = mood.get("primary", "")
            if _is_valid_value(mp):
                mood_primary[_normalize_value(mp)] += 1
            ms = mood.get("secondary", "")
            if _is_valid_value(ms):
                mood_secondary[_normalize_value(ms)] += 1

            # --- 시즌 집계 ---
            se = r.get("season", "")
            if _is_valid_value(se):
                season_counter[_normalize_value(se)] += 1

            # --- 세팅 집계 ---
            st = r.get("setting", "")
            if _is_valid_value(st):
                setting_counter[_normalize_value(st)] += 1

            # --- 성별 집계 ---
            gd = r.get("gender", "")
            if _is_valid_value(gd):
                gender_counter[_normalize_value(gd)] += 1

            # --- 스타일링 집계 ---
            # 스타일링 필드에서 "none"은 유효한 값 (레이어링 없음, 넣어입기 해당없음)
            # 빈 문자열/null만 제외
            styling = r.get("styling", {})
            tuck = styling.get("tuck", "")
            if tuck and isinstance(tuck, str) and tuck.strip():
                tuck_counter[_normalize_value(tuck)] += 1
            layer = styling.get("layering", "")
            if layer and isinstance(layer, str) and layer.strip():
                layering_counter[_normalize_value(layer)] += 1

            # --- 조합 집계 ---
            combo = _extract_combinations(r)
            if combo:
                combination_counter[combo] += 1

            # --- 인플루언서별 통계 ---
            inf_name = r.get("influencer", "unknown")
            if inf_name not in influencer_data:
                influencer_data[inf_name] = {
                    "count": 0,
                    "moods": Counter(),
                    "colors": Counter(),
                }
            influencer_data[inf_name]["count"] += 1
            if _is_valid_value(mp):
                influencer_data[inf_name]["moods"][_normalize_value(mp)] += 1
            if _is_valid_value(mc):
                influencer_data[inf_name]["colors"][_normalize_value(mc)] += 1

        # 인플루언서 통계 정리
        influencer_stats = {}
        for name, data in influencer_data.items():
            top_mood = data["moods"].most_common(1)
            top_color = data["colors"].most_common(1)
            influencer_stats[name] = {
                "count": data["count"],
                "top_mood": top_mood[0][0] if top_mood else "n/a",
                "top_color": top_color[0][0] if top_color else "n/a",
            }

        # 레이어링 비율 계산
        layering_total = sum(layering_counter.values())
        has_layering = sum(
            v for k, v in layering_counter.items() if k not in ("none", "")
        )
        layering_rate = _safe_percentage(has_layering, layering_total)

        # 트렌드 클러스터 생성 (무드 + 실루엣 기반)
        trend_clusters = self._build_trend_clusters(
            mood_primary, top_fit, bottom_fit, item_counters, total
        )

        # 집계 결과 조합
        self._aggregated = {
            "summary": {
                "total": total,
                "analyzed": total,
                "generated_at": datetime.now().isoformat(),
                "influencer_count": len(influencer_stats),
            },
            "items": {
                cat: dict(counter.most_common(15))
                for cat, counter in item_counters.items()
            },
            "colors": {
                "main": dict(color_main.most_common(15)),
                "sub": dict(color_sub.most_common(15)),
                "schemes": dict(color_scheme.most_common(10)),
            },
            "silhouettes": {
                "top_fit": dict(top_fit.most_common()),
                "bottom_fit": dict(bottom_fit.most_common()),
            },
            "moods": {
                "primary": dict(mood_primary.most_common()),
                "secondary": dict(mood_secondary.most_common()),
            },
            "seasons": dict(season_counter.most_common()),
            "settings": dict(setting_counter.most_common()),
            "gender": dict(gender_counter.most_common()),
            "styling": {
                "layering_rate": layering_rate,
                "layering": dict(layering_counter.most_common()),
                "tuck_types": dict(tuck_counter.most_common()),
            },
            "influencer_stats": influencer_stats,
            "top_combinations": [
                {"combo": list(combo), "count": count}
                for combo, count in combination_counter.most_common(15)
            ],
            "trend_clusters": trend_clusters,
        }

        # 집계 JSON 저장
        agg_path = self.output_dir / "aggregated.json"
        with open(agg_path, "w", encoding="utf-8") as f:
            json.dump(self._aggregated, f, ensure_ascii=False, indent=2)
        print(f"[SAVE] Aggregated data -> {agg_path}")

        return self._aggregated

    def generate_report(self, output_path: Optional[str] = None) -> str:
        """
        HTML 리포트 생성

        Args:
            output_path: 저장 경로 (기본: output_dir/trend_report.html)

        Returns:
            생성된 HTML 파일 경로 문자열
        """
        if self._aggregated is None:
            self.aggregate()

        if output_path:
            report_path = Path(output_path)
        else:
            report_path = self.output_dir / "trend_report.html"

        report_path.parent.mkdir(parents=True, exist_ok=True)

        html_content = self._build_html()

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"[REPORT] Generated -> {report_path}")
        return str(report_path)

    # ----------------------------------------------------------
    # 트렌드 클러스터 생성
    # ----------------------------------------------------------

    def _build_trend_clusters(
        self,
        mood_primary: Counter,
        top_fit: Counter,
        bottom_fit: Counter,
        item_counters: Dict[str, Counter],
        total: int,
    ) -> List[Dict]:
        """
        무드 + 실루엣 + 인기 아이템 기반으로 트렌드 클러스터 생성

        상위 3~5개의 무드를 중심으로 대표 키워드를 묶는다.
        """
        clusters = []
        for mood_name, mood_count in mood_primary.most_common(5):
            pct = _safe_percentage(mood_count, total)
            if pct < 3.0:
                continue

            # 키워드 수집: 무드명 + 상위 아이템 + 핏
            keywords = [mood_name]

            # 카테고리별 상위 아이템 추가
            for cat in ["top", "bottom", "outer", "shoes"]:
                top_items = item_counters[cat].most_common(1)
                if top_items:
                    keywords.append(top_items[0][0])

            # 상위 핏 추가
            tf = top_fit.most_common(1)
            bf = bottom_fit.most_common(1)
            if tf:
                keywords.append(f"{tf[0][0]}_top")
            if bf:
                keywords.append(f"{bf[0][0]}_bottom")

            kr_name = _MOOD_KR.get(mood_name, mood_name)
            clusters.append(
                {
                    "name": kr_name,
                    "name_en": mood_name,
                    "keywords": keywords[:6],
                    "percentage": pct,
                    "count": mood_count,
                }
            )

        return clusters

    # ----------------------------------------------------------
    # HTML 리포트 빌더
    # ----------------------------------------------------------

    def _build_html(self) -> str:
        """전체 HTML 리포트 문자열 생성"""
        agg = self._aggregated
        if not agg:
            return "<html><body><h1>No data</h1></body></html>"

        summary = agg["summary"]
        total = summary["total"]

        sections = [
            self._html_head(),
            '<body><div class="container">',
            self._section_header(summary),
            self._section_executive_summary(agg, total),
            self._section_items(agg["items"], total),
            self._section_colors(agg["colors"], total),
            self._section_silhouettes(agg["silhouettes"], total),
            self._section_moods(agg["moods"], total),
            self._section_seasons(agg.get("seasons", {}), total),
            self._section_styling(agg["styling"], total),
            self._section_influencers(agg["influencer_stats"]),
            self._section_combinations(agg["top_combinations"], total),
            self._section_mlb_actions(agg, total),
            self._html_footer(),
            "</div></body></html>",
        ]

        return "\n".join(sections)

    # ----------------------------------------------------------
    # HTML 섹션: 헤드 (CSS 포함)
    # ----------------------------------------------------------

    def _html_head(self) -> str:
        """HTML <head> + CSS 스타일"""
        return """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Fashion Trend Analysis Report</title>
<style>
/* ====== 기본 스타일 ====== */
:root {
    --bg-primary: #1a1a2e;
    --bg-secondary: #16213e;
    --bg-card: #1f2b47;
    --bg-card-hover: #263556;
    --text-primary: #e0e0e0;
    --text-secondary: #a0aec0;
    --text-muted: #718096;
    --accent-1: #e94560;
    --accent-2: #0f3460;
    --accent-3: #533483;
    --accent-4: #00b4d8;
    --border: #2d3748;
    --bar-gradient-1: linear-gradient(90deg, #e94560, #ff6b8a);
    --bar-gradient-2: linear-gradient(90deg, #0f3460, #1a5276);
    --bar-gradient-3: linear-gradient(90deg, #533483, #7c4dbd);
    --bar-gradient-4: linear-gradient(90deg, #00b4d8, #48cae4);
    --bar-gradient-5: linear-gradient(90deg, #e76f51, #f4a261);
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    line-height: 1.6;
    padding: 0;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 24px 16px;
}

/* ====== 헤더 ====== */
.report-header {
    text-align: center;
    padding: 48px 24px;
    margin-bottom: 32px;
    background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--accent-2) 100%);
    border-radius: 16px;
    border: 1px solid var(--border);
}

.report-header h1 {
    font-size: 2.2em;
    font-weight: 700;
    margin-bottom: 8px;
    background: linear-gradient(90deg, #e94560, #00b4d8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.report-header .subtitle {
    color: var(--text-secondary);
    font-size: 1em;
}

.header-stats {
    display: flex;
    justify-content: center;
    gap: 32px;
    margin-top: 24px;
    flex-wrap: wrap;
}

.header-stat {
    text-align: center;
}

.header-stat .number {
    font-size: 2em;
    font-weight: 700;
    color: var(--accent-4);
}

.header-stat .label {
    font-size: 0.85em;
    color: var(--text-muted);
}

/* ====== 섹션 ====== */
.section {
    margin-bottom: 32px;
}

.section-title {
    font-size: 1.4em;
    font-weight: 700;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 2px solid var(--accent-1);
    display: flex;
    align-items: center;
    gap: 8px;
}

.section-title .num {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    background: var(--accent-1);
    color: #fff;
    border-radius: 50%;
    font-size: 0.75em;
    flex-shrink: 0;
}

/* ====== 카드 ====== */
.card {
    background: var(--bg-card);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
    border: 1px solid var(--border);
    transition: background 0.2s;
}

.card:hover {
    background: var(--bg-card-hover);
}

.card-title {
    font-size: 1.05em;
    font-weight: 600;
    margin-bottom: 12px;
    color: var(--accent-4);
}

/* ====== 그리드 ====== */
.grid-2 {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 16px;
}

.grid-3 {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 16px;
}

/* ====== 바 차트 ====== */
.bar-chart {
    list-style: none;
    padding: 0;
}

.bar-item {
    display: flex;
    align-items: center;
    margin-bottom: 8px;
    gap: 8px;
}

.bar-label {
    min-width: 130px;
    font-size: 0.85em;
    color: var(--text-secondary);
    text-align: right;
    flex-shrink: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.bar-track {
    flex: 1;
    background: var(--bg-secondary);
    border-radius: 6px;
    height: 22px;
    overflow: hidden;
    position: relative;
}

.bar-fill {
    height: 100%;
    border-radius: 6px;
    transition: width 0.4s ease;
    min-width: 2px;
}

.bar-value {
    min-width: 60px;
    font-size: 0.8em;
    color: var(--text-muted);
    text-align: right;
    flex-shrink: 0;
}

/* 바 색상 - 카테고리별 */
.bar-fill.g1 { background: var(--bar-gradient-1); }
.bar-fill.g2 { background: var(--bar-gradient-2); }
.bar-fill.g3 { background: var(--bar-gradient-3); }
.bar-fill.g4 { background: var(--bar-gradient-4); }
.bar-fill.g5 { background: var(--bar-gradient-5); }

/* ====== 컬러 스와치 ====== */
.color-list {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    list-style: none;
    padding: 0;
}

.color-item {
    display: flex;
    align-items: center;
    gap: 8px;
    background: var(--bg-secondary);
    padding: 6px 12px;
    border-radius: 8px;
    font-size: 0.85em;
}

.color-swatch {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    border: 2px solid var(--border);
    flex-shrink: 0;
}

.color-name {
    color: var(--text-secondary);
}

.color-count {
    color: var(--text-muted);
    font-size: 0.8em;
}

/* ====== 도넛 차트 (CSS) ====== */
.donut-chart-wrapper {
    display: flex;
    align-items: center;
    gap: 24px;
    flex-wrap: wrap;
}

.donut-chart {
    width: 160px;
    height: 160px;
    border-radius: 50%;
    position: relative;
    flex-shrink: 0;
}

.donut-hole {
    position: absolute;
    width: 80px;
    height: 80px;
    background: var(--bg-card);
    border-radius: 50%;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75em;
    color: var(--text-muted);
    text-align: center;
}

.donut-legend {
    list-style: none;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.donut-legend li {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.85em;
}

.legend-dot {
    width: 12px;
    height: 12px;
    border-radius: 3px;
    flex-shrink: 0;
}

/* ====== 테이블 ====== */
.data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9em;
}

.data-table th {
    background: var(--bg-secondary);
    color: var(--text-secondary);
    padding: 10px 12px;
    text-align: left;
    font-weight: 600;
    border-bottom: 2px solid var(--border);
}

.data-table td {
    padding: 8px 12px;
    border-bottom: 1px solid var(--border);
    color: var(--text-primary);
}

.data-table tr:hover td {
    background: var(--bg-card-hover);
}

/* ====== 인사이트 카드 ====== */
.insight-box {
    background: linear-gradient(135deg, var(--accent-2), var(--accent-3));
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
    border-left: 4px solid var(--accent-1);
}

.insight-box h3 {
    color: var(--accent-4);
    margin-bottom: 8px;
    font-size: 1em;
}

.insight-box p, .insight-box li {
    color: var(--text-secondary);
    font-size: 0.9em;
    line-height: 1.7;
}

.insight-box ul {
    margin-top: 8px;
    padding-left: 20px;
}

/* ====== 조합 태그 ====== */
.combo-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 4px;
}

.combo-tag {
    background: var(--accent-2);
    color: var(--accent-4);
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.8em;
}

.combo-count {
    color: var(--text-muted);
    font-size: 0.8em;
}

/* ====== 푸터 ====== */
.report-footer {
    text-align: center;
    padding: 24px;
    margin-top: 32px;
    color: var(--text-muted);
    font-size: 0.8em;
    border-top: 1px solid var(--border);
}

/* ====== Executive Summary ====== */
.exec-summary {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid var(--accent-4);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 16px;
}

.exec-summary h3 {
    color: var(--accent-4);
    margin-bottom: 12px;
}

.exec-summary ul {
    padding-left: 20px;
}

.exec-summary li {
    margin-bottom: 6px;
    color: var(--text-secondary);
    line-height: 1.6;
}

/* ====== 반응형 ====== */
@media (max-width: 768px) {
    .container { padding: 12px 8px; }
    .report-header h1 { font-size: 1.5em; }
    .header-stats { gap: 16px; }
    .header-stat .number { font-size: 1.5em; }
    .bar-label { min-width: 90px; font-size: 0.78em; }
    .grid-2, .grid-3 { grid-template-columns: 1fr; }
    .donut-chart-wrapper { flex-direction: column; align-items: flex-start; }
}

/* ====== 인쇄 ====== */
@media print {
    body { background: #fff; color: #000; }
    .container { max-width: 100%; padding: 0; }
    .card { border: 1px solid #ddd; break-inside: avoid; }
    .report-header { background: none; border: 2px solid #333; }
    .report-header h1 { background: none; -webkit-text-fill-color: #000; color: #000; }
    .section { break-inside: avoid; }
    .bar-track { background: #eee; }
    .bar-fill { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
    .insight-box { background: #f5f5f5; border-left-color: #333; }
    .data-table th { background: #eee; }
    :root {
        --text-primary: #000;
        --text-secondary: #333;
        --text-muted: #666;
        --bg-card: #fff;
        --bg-secondary: #f5f5f5;
        --border: #ddd;
    }
}
</style>
</head>"""

    # ----------------------------------------------------------
    # HTML 섹션: 헤더
    # ----------------------------------------------------------

    def _section_header(self, summary: Dict) -> str:
        """리포트 헤더 섹션"""
        total = summary.get("total", 0)
        inf_count = summary.get("influencer_count", 0)
        gen_at = summary.get("generated_at", "")
        if gen_at:
            try:
                dt = datetime.fromisoformat(gen_at)
                gen_at = dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                pass

        return f"""
<div class="report-header">
    <h1>Fashion Trend Analysis Report</h1>
    <p class="subtitle">{gen_at}</p>
    <div class="header-stats">
        <div class="header-stat">
            <div class="number">{total}</div>
            <div class="label">Total Images</div>
        </div>
        <div class="header-stat">
            <div class="number">{inf_count}</div>
            <div class="label">Influencers</div>
        </div>
    </div>
</div>"""

    # ----------------------------------------------------------
    # HTML 섹션: Executive Summary
    # ----------------------------------------------------------

    def _section_executive_summary(self, agg: Dict, total: int) -> str:
        """핵심 트렌드 요약 섹션"""
        lines = []

        # 상위 아이템
        all_items = Counter()
        for cat_data in agg.get("items", {}).values():
            for item, count in cat_data.items():
                all_items[item] += count
        top3_items = all_items.most_common(3)
        if top3_items:
            item_str = ", ".join(
                f"<strong>{it}</strong>({_safe_percentage(c, total)}%)"
                for it, c in top3_items
            )
            lines.append(f"Top items: {item_str}")

        # 상위 컬러
        main_colors = agg.get("colors", {}).get("main", {})
        top3_colors = sorted(main_colors.items(), key=lambda x: x[1], reverse=True)[:3]
        if top3_colors:
            color_str = ", ".join(
                f"<strong>{c}</strong>({_safe_percentage(n, total)}%)"
                for c, n in top3_colors
            )
            lines.append(f"Top colors: {color_str}")

        # 상위 무드
        moods = agg.get("moods", {}).get("primary", {})
        top3_moods = sorted(moods.items(), key=lambda x: x[1], reverse=True)[:3]
        if top3_moods:
            mood_str = ", ".join(
                f"<strong>{_MOOD_KR.get(m, m)}</strong>({_safe_percentage(n, total)}%)"
                for m, n in top3_moods
            )
            lines.append(f"Top moods: {mood_str}")

        items_html = "".join(f"<li>{line}</li>" for line in lines)

        return f"""
<div class="section">
    <h2 class="section-title"><span class="num">0</span> Executive Summary</h2>
    <div class="exec-summary">
        <h3>Key Trends</h3>
        <ul>{items_html}</ul>
    </div>
</div>"""

    # ----------------------------------------------------------
    # HTML 섹션: 아이템 트렌드
    # ----------------------------------------------------------

    def _section_items(self, items_data: Dict, total: int) -> str:
        """아이템 트렌드 섹션 (카테고리별 바 차트)"""
        cards = []
        gradient_classes = ["g1", "g2", "g3", "g4", "g5"]

        for i, (cat_en, items) in enumerate(items_data.items()):
            if not items:
                continue
            cat_kr = _CATEGORY_KR.get(cat_en, cat_en)
            g_class = gradient_classes[i % len(gradient_classes)]
            max_count = max(items.values()) if items else 1

            bars = []
            for item_name, count in list(items.items())[:10]:
                pct = _safe_percentage(count, total)
                bar_w = _safe_percentage(count, max_count)
                escaped = html_module.escape(item_name)
                bars.append(
                    f'<li class="bar-item">'
                    f'<span class="bar-label">{escaped}</span>'
                    f'<div class="bar-track">'
                    f'<div class="bar-fill {g_class}" style="width:{bar_w}%"></div>'
                    f"</div>"
                    f'<span class="bar-value">{count} ({pct}%)</span>'
                    f"</li>"
                )

            bars_html = "\n".join(bars)
            cards.append(
                f'<div class="card">'
                f'<div class="card-title">{cat_kr} ({cat_en})</div>'
                f'<ul class="bar-chart">{bars_html}</ul>'
                f"</div>"
            )

        grid_html = "\n".join(cards)
        return f"""
<div class="section">
    <h2 class="section-title"><span class="num">1</span> Item Trends</h2>
    <div class="grid-2">{grid_html}</div>
</div>"""

    # ----------------------------------------------------------
    # HTML 섹션: 컬러 트렌드
    # ----------------------------------------------------------

    def _section_colors(self, colors_data: Dict, total: int) -> str:
        """컬러 트렌드 섹션 (스와치 + 바 차트)"""
        main_colors = colors_data.get("main", {})
        schemes = colors_data.get("schemes", {})

        # 메인 컬러 스와치
        swatch_items = []
        for color_name, count in sorted(
            main_colors.items(), key=lambda x: x[1], reverse=True
        )[:12]:
            hex_color = COLOR_MAP.get(color_name, "#808080")
            pct = _safe_percentage(count, total)
            escaped = html_module.escape(color_name)
            swatch_items.append(
                f'<li class="color-item">'
                f'<span class="color-swatch" style="background:{hex_color}"></span>'
                f'<span class="color-name">{escaped}</span>'
                f'<span class="color-count">{count} ({pct}%)</span>'
                f"</li>"
            )
        swatch_html = "\n".join(swatch_items)

        # 컬러 스킴 바 차트
        max_scheme = max(schemes.values()) if schemes else 1
        scheme_bars = []
        for scheme_name, count in sorted(
            schemes.items(), key=lambda x: x[1], reverse=True
        ):
            pct = _safe_percentage(count, total)
            bar_w = _safe_percentage(count, max_scheme)
            escaped = html_module.escape(scheme_name)
            scheme_bars.append(
                f'<li class="bar-item">'
                f'<span class="bar-label">{escaped}</span>'
                f'<div class="bar-track">'
                f'<div class="bar-fill g4" style="width:{bar_w}%"></div>'
                f"</div>"
                f'<span class="bar-value">{count} ({pct}%)</span>'
                f"</li>"
            )
        scheme_html = "\n".join(scheme_bars)

        return f"""
<div class="section">
    <h2 class="section-title"><span class="num">2</span> Color Trends</h2>
    <div class="grid-2">
        <div class="card">
            <div class="card-title">Main Colors</div>
            <ul class="color-list">{swatch_html}</ul>
        </div>
        <div class="card">
            <div class="card-title">Color Schemes</div>
            <ul class="bar-chart">{scheme_html}</ul>
        </div>
    </div>
</div>"""

    # ----------------------------------------------------------
    # HTML 섹션: 실루엣 트렌드
    # ----------------------------------------------------------

    def _section_silhouettes(self, sil_data: Dict, total: int) -> str:
        """실루엣 트렌드 섹션 (핏 분포)"""
        cards = []
        fit_labels = {"top_fit": "Top Fit", "bottom_fit": "Bottom Fit"}
        g_map = {"top_fit": "g3", "bottom_fit": "g5"}

        for key, label in fit_labels.items():
            fits = sil_data.get(key, {})
            if not fits:
                continue

            max_count = max(fits.values()) if fits else 1
            bars = []
            for fit_name, count in sorted(
                fits.items(), key=lambda x: x[1], reverse=True
            ):
                pct = _safe_percentage(count, total)
                bar_w = _safe_percentage(count, max_count)
                escaped = html_module.escape(fit_name)
                bars.append(
                    f'<li class="bar-item">'
                    f'<span class="bar-label">{escaped}</span>'
                    f'<div class="bar-track">'
                    f'<div class="bar-fill {g_map[key]}" style="width:{bar_w}%"></div>'
                    f"</div>"
                    f'<span class="bar-value">{count} ({pct}%)</span>'
                    f"</li>"
                )

            bars_html = "\n".join(bars)
            cards.append(
                f'<div class="card">'
                f'<div class="card-title">{label}</div>'
                f'<ul class="bar-chart">{bars_html}</ul>'
                f"</div>"
            )

        grid_html = "\n".join(cards)
        return f"""
<div class="section">
    <h2 class="section-title"><span class="num">3</span> Silhouette Trends</h2>
    <div class="grid-2">{grid_html}</div>
</div>"""

    # ----------------------------------------------------------
    # HTML 섹션: 무드 분석
    # ----------------------------------------------------------

    def _section_moods(self, moods_data: Dict, total: int) -> str:
        """무드 분석 섹션 (도넛 차트 + 목록)"""
        primary = moods_data.get("primary", {})
        if not primary:
            return ""

        # 도넛 차트용 데이터 (conic-gradient)
        donut_colors = [
            "#e94560",
            "#0f3460",
            "#533483",
            "#00b4d8",
            "#e76f51",
            "#2a9d8f",
            "#f4a261",
            "#264653",
            "#a855f7",
            "#ec4899",
        ]

        sorted_moods = sorted(primary.items(), key=lambda x: x[1], reverse=True)
        segments = []
        legend_items = []
        cumulative = 0.0

        for i, (mood_name, count) in enumerate(sorted_moods[:8]):
            pct = _safe_percentage(count, total)
            color = donut_colors[i % len(donut_colors)]
            start = cumulative
            cumulative += pct
            segments.append(f"{color} {start}% {cumulative}%")

            kr_name = _MOOD_KR.get(mood_name, mood_name)
            legend_items.append(
                f"<li>"
                f'<span class="legend-dot" style="background:{color}"></span>'
                f"{kr_name} ({mood_name}) - {count} ({pct}%)"
                f"</li>"
            )

        # 나머지 비율 (기타)
        if cumulative < 100:
            segments.append(f"var(--bg-secondary) {cumulative}% 100%")

        gradient = ", ".join(segments)
        legend_html = "\n".join(legend_items)

        return f"""
<div class="section">
    <h2 class="section-title"><span class="num">4</span> Mood Analysis</h2>
    <div class="card">
        <div class="card-title">Primary Mood Distribution</div>
        <div class="donut-chart-wrapper">
            <div class="donut-chart" style="background: conic-gradient({gradient})">
                <div class="donut-hole">MOOD</div>
            </div>
            <ul class="donut-legend">{legend_html}</ul>
        </div>
    </div>
</div>"""

    # ----------------------------------------------------------
    # HTML 섹션: 시즌감
    # ----------------------------------------------------------

    def _section_seasons(self, seasons: Dict, total: int) -> str:
        """시즌 분포 섹션"""
        if not seasons:
            return ""

        max_count = max(seasons.values()) if seasons else 1
        bars = []
        for season, count in sorted(seasons.items(), key=lambda x: x[1], reverse=True):
            pct = _safe_percentage(count, total)
            bar_w = _safe_percentage(count, max_count)
            kr = _SEASON_KR.get(season, season)
            bars.append(
                f'<li class="bar-item">'
                f'<span class="bar-label">{kr} ({season})</span>'
                f'<div class="bar-track">'
                f'<div class="bar-fill g2" style="width:{bar_w}%"></div>'
                f"</div>"
                f'<span class="bar-value">{count} ({pct}%)</span>'
                f"</li>"
            )

        bars_html = "\n".join(bars)
        return f"""
<div class="section">
    <h2 class="section-title"><span class="num">5</span> Season Distribution</h2>
    <div class="card">
        <ul class="bar-chart">{bars_html}</ul>
    </div>
</div>"""

    # ----------------------------------------------------------
    # HTML 섹션: 스타일링 인사이트
    # ----------------------------------------------------------

    def _section_styling(self, styling_data: Dict, total: int) -> str:
        """스타일링 인사이트 섹션"""
        layering_rate = styling_data.get("layering_rate", 0)
        layering = styling_data.get("layering", {})
        tuck_types = styling_data.get("tuck_types", {})

        # 레이어링 분포
        layering_bars = self._make_bar_list(layering, total, "g4")

        # 넣어입기/빼입기 분포
        tuck_bars = self._make_bar_list(tuck_types, total, "g5")

        return f"""
<div class="section">
    <h2 class="section-title"><span class="num">6</span> Styling Insights</h2>
    <div class="grid-2">
        <div class="card">
            <div class="card-title">Layering (Rate: {layering_rate}%)</div>
            <ul class="bar-chart">{layering_bars}</ul>
        </div>
        <div class="card">
            <div class="card-title">Tuck Style</div>
            <ul class="bar-chart">{tuck_bars}</ul>
        </div>
    </div>
</div>"""

    # ----------------------------------------------------------
    # HTML 섹션: 인플루언서별 스타일
    # ----------------------------------------------------------

    def _section_influencers(self, influencer_stats: Dict) -> str:
        """인플루언서별 스타일 섹션 (TOP 10 테이블)"""
        if not influencer_stats:
            return ""

        # 이미지 수 기준 상위 10명
        sorted_inf = sorted(
            influencer_stats.items(),
            key=lambda x: x[1]["count"],
            reverse=True,
        )[:10]

        rows = []
        for rank, (name, data) in enumerate(sorted_inf, 1):
            count = data["count"]
            mood = data.get("top_mood", "n/a")
            color = data.get("top_color", "n/a")
            mood_kr = _MOOD_KR.get(mood, mood)
            hex_color = COLOR_MAP.get(color, "#808080")

            escaped_name = html_module.escape(name)
            escaped_mood = html_module.escape(mood_kr)
            escaped_color = html_module.escape(color)

            rows.append(
                f"<tr>"
                f"<td>{rank}</td>"
                f"<td>{escaped_name}</td>"
                f"<td>{count}</td>"
                f"<td>{escaped_mood}</td>"
                f'<td><span class="color-swatch" '
                f'style="background:{hex_color};display:inline-block;'
                f'width:14px;height:14px;vertical-align:middle;margin-right:4px">'
                f"</span>{escaped_color}</td>"
                f"</tr>"
            )

        rows_html = "\n".join(rows)
        return f"""
<div class="section">
    <h2 class="section-title"><span class="num">7</span> Influencer Styles (TOP 10)</h2>
    <div class="card">
        <table class="data-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Influencer</th>
                    <th>Images</th>
                    <th>Top Mood</th>
                    <th>Top Color</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
</div>"""

    # ----------------------------------------------------------
    # HTML 섹션: 인기 조합
    # ----------------------------------------------------------

    def _section_combinations(self, combinations: List[Dict], total: int) -> str:
        """인기 조합 섹션 (태그 + 빈도)"""
        if not combinations:
            return ""

        combo_items = []
        for entry in combinations[:10]:
            combo = entry.get("combo", [])
            count = entry.get("count", 0)
            pct = _safe_percentage(count, total)
            tags = "".join(
                f'<span class="combo-tag">{html_module.escape(str(item))}</span>'
                for item in combo
            )
            combo_items.append(
                f'<div class="card" style="padding:12px 16px">'
                f'<div class="combo-tags">{tags}</div>'
                f'<span class="combo-count">{count}x ({pct}%)</span>'
                f"</div>"
            )

        combos_html = "\n".join(combo_items)
        return f"""
<div class="section">
    <h2 class="section-title"><span class="num">8</span> Top Combinations</h2>
    {combos_html}
</div>"""

    # ----------------------------------------------------------
    # HTML 섹션: MLB 브랜드 액션 제안
    # ----------------------------------------------------------

    def _section_mlb_actions(self, agg: Dict, total: int) -> str:
        """MLB 브랜드 액션 제안 섹션"""
        suggestions = self._generate_mlb_suggestions(agg, total)
        if not suggestions:
            return ""

        items_html = "".join(f"<li>{html_module.escape(s)}</li>" for s in suggestions)

        return f"""
<div class="section">
    <h2 class="section-title"><span class="num">9</span> MLB Brand Action</h2>
    <div class="insight-box">
        <h3>Trend to MLB Matching</h3>
        <ul>{items_html}</ul>
    </div>
</div>"""

    # ----------------------------------------------------------
    # MLB 제안 생성
    # ----------------------------------------------------------

    def _generate_mlb_suggestions(self, agg: Dict, total: int) -> List[str]:
        """
        트렌드 데이터에서 MLB 브랜드 착장 매칭 제안 생성

        상위 아이템/컬러/무드를 기반으로 MLB 제품 카테고리와 매칭한다.
        """
        suggestions = []

        # 상위 아이템 분석
        all_items = Counter()
        for cat_data in agg.get("items", {}).values():
            for item, count in cat_data.items():
                all_items[item] += count

        top_items = [item for item, _ in all_items.most_common(5)]

        # 상위 컬러
        main_colors = agg.get("colors", {}).get("main", {})
        top_colors = [
            c
            for c, _ in sorted(main_colors.items(), key=lambda x: x[1], reverse=True)[
                :3
            ]
        ]

        # 상위 무드
        moods = agg.get("moods", {}).get("primary", {})
        top_moods = [
            m for m, _ in sorted(moods.items(), key=lambda x: x[1], reverse=True)[:3]
        ]

        # 아이템 기반 제안
        mlb_items = {
            "cap": "MLB cap (NY/LA/Red Sox)",
            "beanie": "MLB beanie",
            "oversized_tee": "MLB oversized logo tee",
            "crop_tee": "MLB crop top with big logo",
            "hoodie": "MLB hoodie (monogram or varsity)",
            "sweatshirt": "MLB crewneck sweatshirt",
            "jogger": "MLB jogger pants (side logo)",
            "shorts": "MLB shorts (track style)",
            "sneakers": "MLB Chunky Liner / Big Ball Chunky",
            "backpack": "MLB monogram backpack",
            "crossbody": "MLB mini crossbody bag",
            "bomber": "MLB varsity jacket",
            "padding": "MLB padding jacket (big logo back)",
            "fleece": "MLB fleece zip-up",
        }

        for item in top_items:
            if item in mlb_items:
                suggestions.append(f"[Item] '{item}' trending -> {mlb_items[item]}")

        # 모자류 트렌드 (MLB 핵심 카테고리)
        headwear = agg.get("items", {}).get("headwear", {})
        if headwear:
            top_hw = max(headwear, key=headwear.get)
            hw_pct = _safe_percentage(headwear[top_hw], total)
            suggestions.append(
                f"[Headwear] '{top_hw}' ({hw_pct}%) -> MLB {top_hw} 라인 강화"
            )

        # 컬러 기반 제안
        color_to_mlb = {
            "black": "NY Yankees Black series",
            "white": "MLB White Label clean line",
            "navy": "NY Yankees classic navy",
            "beige": "MLB Monogram beige series",
            "brown": "MLB Earth tone collection",
            "cream": "MLB Vintage cream line",
        }
        for color in top_colors:
            if color in color_to_mlb:
                suggestions.append(
                    f"[Color] '{color}' trending -> {color_to_mlb[color]}"
                )

        # 무드 기반 제안
        mood_to_mlb = {
            "street_casual": "MLB Varsity / Big Logo line (street appeal)",
            "clean_minimal": "MLB Monogram minimal series",
            "sporty": "MLB Athletic Heritage line",
            "athleisure": "MLB Track series + Chunky sneakers",
            "y2k": "MLB retro logo revival + chunky accessories",
            "preppy": "MLB Varsity jacket + cap classic combo",
        }
        for mood in top_moods:
            if mood in mood_to_mlb:
                kr = _MOOD_KR.get(mood, mood)
                suggestions.append(f"[Mood] '{kr}' trending -> {mood_to_mlb[mood]}")

        # 실루엣 기반 제안
        sil = agg.get("silhouettes", {})
        top_fit_data = sil.get("top_fit", {})
        bottom_fit_data = sil.get("bottom_fit", {})

        if top_fit_data:
            top_f = max(top_fit_data, key=top_fit_data.get)
            if top_f == "oversized":
                suggestions.append(
                    "[Silhouette] Oversized top trend -> "
                    "MLB oversized logo tee/hoodie sizing up"
                )
            elif top_f == "crop":
                suggestions.append(
                    "[Silhouette] Crop top trend -> "
                    "MLB crop tee/sweatshirt for female line"
                )

        if bottom_fit_data:
            bot_f = max(bottom_fit_data, key=bottom_fit_data.get)
            if bot_f == "wide":
                suggestions.append(
                    "[Silhouette] Wide pants trend -> "
                    "MLB wide jogger/cargo with side logo"
                )

        return suggestions

    # ----------------------------------------------------------
    # HTML 유틸리티
    # ----------------------------------------------------------

    def _make_bar_list(self, data: Dict, total: int, gradient_class: str = "g1") -> str:
        """딕셔너리를 바 차트 HTML로 변환"""
        if not data:
            return '<li class="bar-item"><span class="bar-label">No data</span></li>'

        max_count = max(data.values()) if data else 1
        bars = []
        for name, count in sorted(data.items(), key=lambda x: x[1], reverse=True):
            pct = _safe_percentage(count, total)
            bar_w = _safe_percentage(count, max_count)
            escaped = html_module.escape(name)
            bars.append(
                f'<li class="bar-item">'
                f'<span class="bar-label">{escaped}</span>'
                f'<div class="bar-track">'
                f'<div class="bar-fill {gradient_class}" style="width:{bar_w}%"></div>'
                f"</div>"
                f'<span class="bar-value">{count} ({pct}%)</span>'
                f"</li>"
            )
        return "\n".join(bars)

    def _html_footer(self) -> str:
        """리포트 푸터"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"""
<div class="report-footer">
    <p>Generated by FNF AI Studio - Trend Analysis Module | {now}</p>
    <p>F&F AX Team</p>
</div>"""
