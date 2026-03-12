"""
Trend Analysis Module - 인플루언서 이미지에서 패션 트렌드 추출

Usage:
    from core.trend_analysis import TrendAnalyzer, TrendAggregator

    # 1. VLM 분석
    analyzer = TrendAnalyzer(image_dir="path/to/images")
    analyzer.run(max_images=100)

    # 2. 집계 + 리포트
    aggregator = TrendAggregator(results_dir="path/to/results")
    aggregator.generate_report()
"""

from core.trend_analysis.analyzer import TrendAnalyzer
from core.trend_analysis.aggregator import TrendAggregator

__all__ = ["TrendAnalyzer", "TrendAggregator"]
