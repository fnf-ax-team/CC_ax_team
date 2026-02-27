"""
YouTube Shorts Scraper 설정 파일
"""
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# ============================================================
# Apify API 설정
# ============================================================

# 환경변수에서 API 토큰 로드 (없으면 빈 문자열)
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")

# Apify Actor ID
APIFY_ACTOR_ID = "reGe1ST3OBgYZSsZJ"  # Instagram Hashtag Scraper

# Apify API Base URL
APIFY_BASE_URL = "https://api.apify.com/v2"


# ============================================================
# Google Gemini API 설정
# ============================================================

# 환경변수에서 Gemini API 키 로드 (없으면 빈 문자열)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Gemini 모델 이름
GEMINI_MODEL = "gemini-3-pro-preview"

# AI 요약 활성화 여부
ENABLE_AI_SUMMARY = True


# ============================================================
# 검색 설정 (YouTube Shorts)
# ============================================================

DEFAULT_MAX_RESULTS = 30
DEFAULT_TOP_N = 3
TIMEOUT_SECONDS = 300
POLL_INTERVAL = 5


# ============================================================
# Instagram Reels 설정
# ============================================================

# 검색할 해시태그 (키워드) - 기본값
INSTAGRAM_SEARCH_KEYWORD = os.getenv("INSTAGRAM_SEARCH_KEYWORD", "성수맛집")

# 최종적으로 얻고 싶은 릴스 개수
INSTAGRAM_TARGET_COUNT = int(os.getenv("INSTAGRAM_TARGET_COUNT", "30"))

# 필터링을 위해 넉넉히 수집할 개수 (보통 3~5배수 권장)
INSTAGRAM_FETCH_BUFFER = int(os.getenv("INSTAGRAM_FETCH_BUFFER", "200"))

# 크롤링 타임아웃 (초) - 이 시간 내에 수집이 완료되지 않으면 다음으로 진행
INSTAGRAM_CRAWL_TIMEOUT = int(os.getenv("INSTAGRAM_CRAWL_TIMEOUT", "600"))  # 기본 10분

# 키워드 관련성 필터링 활성화 (caption에 키워드가 있는지 확인)
INSTAGRAM_KEYWORD_FILTER = os.getenv("INSTAGRAM_KEYWORD_FILTER", "True").lower() == "true"

# 광고 필터링 활성화 (caption에 '광고'가 있으면 제외)
INSTAGRAM_AD_FILTER = os.getenv("INSTAGRAM_AD_FILTER", "True").lower() == "true"

# Gemini AI 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ENABLE_AI_SUMMARY = os.getenv("ENABLE_AI_SUMMARY", "True").lower() == "true"

# 전체 분석 모드 설정
AUTO_ANALYZE_ALL = os.getenv("AUTO_ANALYZE_ALL", "False").lower() == "true"
ENABLE_DB_SAVE = os.getenv("ENABLE_DB_SAVE", "True").lower() == "true"

# "최신성" 기준: 며칠 이내 게시물만 인정할지 (기본 12개월)
# 0으로 설정하면 날짜 필터 비활성화 (모든 게시물 포함)
INSTAGRAM_MAX_DAYS_OLD = int(os.getenv("INSTAGRAM_MAX_DAYS_OLD", "365"))

# 특정 서브카테고리만 크롤링 (None이면 전체, 특정 이름 입력 시 해당 서브카테고리만)
# 예: "클렌징 밤", "립틴트", "선크림" 등
INSTAGRAM_TARGET_SUBCATEGORY = os.getenv("INSTAGRAM_TARGET_SUBCATEGORY", None)

# TOP3 선정 시 최종 출력 개수
INSTAGRAM_TOP_N = int(os.getenv("INSTAGRAM_TOP_N", "3"))


# ============================================================
# 출력 설정
# ============================================================

OUTPUT_FILENAME = "youtube_shorts_results.json"
MAX_DESCRIPTION_LENGTH = 500

