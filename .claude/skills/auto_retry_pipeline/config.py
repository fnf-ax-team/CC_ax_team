"""
파이프라인 설정 - core 모듈에서 re-export (하위 호환성 유지)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import PipelineConfig
from core.prompts import BASE_PRESERVATION_PROMPT, DEFAULT_BACKGROUND_PROMPT

__all__ = ['PipelineConfig', 'BASE_PRESERVATION_PROMPT', 'DEFAULT_BACKGROUND_PROMPT']
