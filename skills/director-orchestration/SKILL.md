---
name: 오케스트레이션_director-orchestration
description: Director/오케스트레이션 스킬. 다단계 워크플로우 조율 시, 분석-생성-검증 파이프라인 구현 시, 여러 노드를 연결하는 Director 노드 개발 시 사용. asyncio.gather 기반 비동기 파이프라인, 단계별 실행 관리, 에러 전파 및 롤백 패턴을 제공합니다.
---

## 개요

FNF Studio의 **Director/오케스트레이션 스킬**입니다.
여러 단계를 조율하는 Director 노드 개발 패턴을 제공합니다.

## 역할

- 다단계 워크플로우 조율 (분석 -> 생성 -> 검증)
- asyncio.gather 기반 비동기 파이프라인
- 단계별 실행 관리 및 상태 추적
- 에러 전파 및 롤백 처리
- 캐싱 및 성능 최적화

## 사용 시점

다음 상황에서 이 스킬을 사용하세요:

- 다단계 워크플로우를 조율할 때
- 분석-생성-검증 파이프라인 구현 시
- 여러 노드를 연결하는 Director 노드 개발 시
- 복잡한 워크플로우의 상태 관리가 필요할 때

## 핵심 패턴

### 1. 기본 Director 구조

```python
class Linn_Director:
    """
    Director 노드 기본 구조:
    1. 입력 분석 (analyze)
    2. 작업 생성 (generate)
    3. 결과 검증 (validate)
    4. 후처리 (post_process)
    """

    STAGES = ["analyze", "generate", "validate", "post_process"]

    def __init__(self):
        self.current_stage = None
        self.stage_results = {}

    async def execute(self, inputs):
        """전체 워크플로우 실행"""
        try:
            # Stage 1: 분석
            self.current_stage = "analyze"
            analysis = await self._analyze(inputs)
            self.stage_results["analyze"] = analysis

            # Stage 2: 생성
            self.current_stage = "generate"
            generated = await self._generate(analysis)
            self.stage_results["generate"] = generated

            # Stage 3: 검증
            self.current_stage = "validate"
            validated = await self._validate(generated)
            self.stage_results["validate"] = validated

            # Stage 4: 후처리
            self.current_stage = "post_process"
            final = await self._post_process(validated)
            self.stage_results["post_process"] = final

            return final

        except Exception as e:
            print(f"[Director] Stage '{self.current_stage}' 실패: {e}")
            raise
```

### 2. asyncio.gather 기반 병렬 단계

```python
import asyncio

async def parallel_pipeline(self, items):
    """여러 아이템을 병렬로 처리하는 파이프라인"""

    # Stage 1: 모든 아이템 동시 분석
    analysis_tasks = [self._analyze_single(item) for item in items]
    analyses = await asyncio.gather(*analysis_tasks, return_exceptions=True)

    # 에러 필터링
    valid_analyses = [
        (i, a) for i, a in enumerate(analyses)
        if not isinstance(a, Exception)
    ]

    # Stage 2: 분석 성공한 아이템만 생성
    generate_tasks = [
        self._generate_single(analysis, index)
        for index, analysis in valid_analyses
    ]
    results = await asyncio.gather(*generate_tasks, return_exceptions=True)

    return results
```

### 3. 단계별 상태 추적

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Any

class StageStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class StageResult:
    stage: str
    status: StageStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: float = 0

class DirectorWithTracking:
    def __init__(self):
        self.stage_history: list[StageResult] = []

    async def run_stage(self, stage_name: str, func, *args, **kwargs):
        """단계 실행 및 추적"""
        import time
        start = time.time()

        stage_result = StageResult(stage=stage_name, status=StageStatus.RUNNING)
        self.stage_history.append(stage_result)

        try:
            result = await func(*args, **kwargs)
            stage_result.status = StageStatus.COMPLETED
            stage_result.result = result
            return result

        except Exception as e:
            stage_result.status = StageStatus.FAILED
            stage_result.error = str(e)
            raise

        finally:
            stage_result.duration_ms = (time.time() - start) * 1000

    def get_summary(self):
        """실행 요약"""
        return {
            "total_stages": len(self.stage_history),
            "completed": sum(1 for s in self.stage_history if s.status == StageStatus.COMPLETED),
            "failed": sum(1 for s in self.stage_history if s.status == StageStatus.FAILED),
            "total_duration_ms": sum(s.duration_ms for s in self.stage_history),
            "stages": [
                {"name": s.stage, "status": s.status.value, "duration_ms": s.duration_ms}
                for s in self.stage_history
            ]
        }
```

### 4. 에러 전파 및 롤백

```python
class DirectorWithRollback:
    def __init__(self):
        self.rollback_stack = []

    async def execute_with_rollback(self, stages):
        """롤백 지원 실행"""
        results = {}

        for stage in stages:
            try:
                result = await stage["func"](**stage.get("args", {}))
                results[stage["name"]] = result

                # 롤백 함수 등록
                if stage.get("rollback"):
                    self.rollback_stack.append(stage["rollback"])

            except Exception as e:
                print(f"[Director] Stage '{stage['name']}' 실패, 롤백 시작...")

                # 역순으로 롤백 실행
                for rollback_func in reversed(self.rollback_stack):
                    try:
                        await rollback_func()
                    except Exception as rollback_error:
                        print(f"[Director] 롤백 실패: {rollback_error}")

                raise

        return results

# 사용 예시
director = DirectorWithRollback()
stages = [
    {
        "name": "create_temp_files",
        "func": create_temp_files,
        "args": {"path": "/tmp/work"},
        "rollback": lambda: cleanup_temp_files("/tmp/work")
    },
    {
        "name": "generate_images",
        "func": generate_images,
        "args": {"prompts": prompts},
        "rollback": lambda: delete_generated_images()
    },
    {
        "name": "upload_results",
        "func": upload_results,
        "args": {"destination": "s3://bucket"}
    }
]

results = await director.execute_with_rollback(stages)
```

### 5. 싱글톤 및 캐싱 패턴

```python
from collections import OrderedDict

class DirectorWithCaching:
    """
    Director v3 스타일 싱글톤 및 캐싱
    """
    _INSTANCE = None
    _CLIENT_INSTANCE = None
    _CACHE: OrderedDict = OrderedDict()
    _CACHE_MAX_SIZE = 100
    _CACHE_TTL = 3600  # 1시간

    @classmethod
    def get_instance(cls):
        if cls._INSTANCE is None:
            cls._INSTANCE = cls()
        return cls._INSTANCE

    @classmethod
    def get_client(cls):
        """Gemini 클라이언트 싱글톤"""
        if cls._CLIENT_INSTANCE is None:
            from google import genai
            api_key = get_api_key("gemini")
            cls._CLIENT_INSTANCE = genai.Client(api_key=api_key)
        return cls._CLIENT_INSTANCE

    def get_cached(self, key):
        """TTL 기반 캐시 조회"""
        import time
        if key in self._CACHE:
            entry = self._CACHE[key]
            if time.time() - entry["timestamp"] < self._CACHE_TTL:
                # 최근 사용 항목을 끝으로 이동 (LRU)
                self._CACHE.move_to_end(key)
                return entry["value"]
            else:
                del self._CACHE[key]
        return None

    def set_cached(self, key, value):
        """캐시 저장 (크기 제한 포함)"""
        import time
        if len(self._CACHE) >= self._CACHE_MAX_SIZE:
            self._CACHE.popitem(last=False)  # 가장 오래된 항목 제거
        self._CACHE[key] = {"value": value, "timestamp": time.time()}
```

## 코드 예제

### 예제 1: Linn_Director_v3 구조

```python
# Linn_Director_v3.py 참조
class Linn_Director_v3:
    """Creative Director v3: 분석 -> 프롬프트 생성 -> 이미지 생성"""

    async def direct(self, reference_images, brand, mood, batch_count):
        # Stage 1: 레퍼런스 분석
        print("[Director] Stage 1: 레퍼런스 분석")
        analysis = await self._analyze_references(reference_images)

        # Stage 2: 브랜드 가이드 로드 (캐싱)
        print("[Director] Stage 2: 브랜드 가이드 로드")
        brand_guide = self.get_cached(f"brand:{brand}")
        if not brand_guide:
            brand_guide = self.load_brand_guide(brand)
            self.set_cached(f"brand:{brand}", brand_guide)

        # Stage 3: 프롬프트 생성
        print("[Director] Stage 3: 프롬프트 생성")
        prompts = await self._generate_prompts(analysis, brand_guide, mood, batch_count)

        # Stage 4: 이미지 병렬 생성
        print("[Director] Stage 4: 이미지 생성 (병렬)")
        images = await self._generate_images_parallel(prompts)

        return images, prompts
```

### 예제 2: EcommerceDirector 파이프라인

```python
# Linn_image_EcommerceDirector.py 참조
class Linn_EcommerceDirector:
    """이커머스 Director: 제품 분석 -> 배경 생성 -> 합성 -> QC"""

    async def process(self, product_image, style):
        pipeline = [
            {"name": "product_analysis", "func": self._analyze_product},
            {"name": "background_generation", "func": self._generate_background},
            {"name": "composition", "func": self._compose},
            {"name": "quality_check", "func": self._quality_check},
        ]

        context = {"product_image": product_image, "style": style}

        for stage in pipeline:
            print(f"[Ecommerce] {stage['name']} 실행 중...")
            context = await stage["func"](context)

            # 실패 시 조기 종료
            if context.get("failed"):
                print(f"[Ecommerce] {stage['name']} 실패, 중단")
                break

        return context
```

### 예제 3: ProductDirector 조건부 분기

```python
# Linn_ProductDirector.py 참조
class Linn_ProductDirector:
    """제품 Director: 조건에 따른 분기 처리"""

    async def direct(self, product_image, product_type, options):
        # 공통 분석
        analysis = await self._analyze(product_image)

        # 제품 타입에 따른 분기
        if product_type == "apparel":
            return await self._process_apparel(analysis, options)
        elif product_type == "accessory":
            return await self._process_accessory(analysis, options)
        elif product_type == "footwear":
            return await self._process_footwear(analysis, options)
        else:
            return await self._process_generic(analysis, options)

    async def _process_apparel(self, analysis, options):
        """의류 처리 파이프라인"""
        stages = [
            self._extract_garment,
            self._generate_model,
            self._virtual_tryon,
            self._post_process,
        ]
        result = analysis
        for stage in stages:
            result = await stage(result, options)
        return result
```

## DO/DON'T

### DO

- **단계별 분리** (analyze, generate, validate, post_process)
- **asyncio.gather로 병렬화** (독립적인 작업)
- **상태 추적** (StageResult, stage_history)
- **캐싱 활용** (브랜드 가이드, 클라이언트 싱글톤)
- **에러 격리** (한 단계 실패가 전체 영향 최소화)
- **롤백 지원** (임시 파일 정리 등)

### DON'T

- **동기 블로킹 호출 금지** (asyncio 환경에서 time.sleep 대신 asyncio.sleep)
- **글로벌 상태 변경 금지** (스레드 안전하지 않음)
- **무한 재시도 금지** (최대 재시도 횟수 설정)
- **캐시 무한 증가 금지** (TTL + 최대 크기 제한)
- **단계 건너뛰기 금지** (의존성 있는 단계는 순차 실행)

## 고급 패턴

### 1. 조건부 단계 스킵

```python
async def execute_conditional(self, stages, context):
    """조건에 따라 단계 스킵"""
    for stage in stages:
        # 조건 확인
        if stage.get("condition") and not stage["condition"](context):
            print(f"[Director] Stage '{stage['name']}' 스킵")
            continue

        # 실행
        context = await stage["func"](context)

    return context

# 사용
stages = [
    {"name": "analyze", "func": analyze},
    {"name": "enhance", "func": enhance, "condition": lambda ctx: ctx.get("quality") < 0.8},
    {"name": "validate", "func": validate},
]
```

### 2. 재시도 래퍼

```python
async def with_retry(self, func, max_retries=3, delay=1.0):
    """재시도 래퍼"""
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"[Director] 재시도 {attempt + 1}/{max_retries}: {e}")
                await asyncio.sleep(delay * (attempt + 1))
            else:
                raise
```

### 3. 프로그레스 콜백

```python
async def execute_with_progress(self, stages, on_progress=None):
    """진행률 콜백 지원"""
    total = len(stages)

    for i, stage in enumerate(stages):
        if on_progress:
            on_progress({
                "current": i + 1,
                "total": total,
                "stage": stage["name"],
                "progress": (i + 1) / total * 100
            })

        await stage["func"]()

# 사용
def progress_callback(info):
    print(f"[{info['current']}/{info['total']}] {info['stage']} ({info['progress']:.1f}%)")

await director.execute_with_progress(stages, on_progress=progress_callback)
```

## 관련 스킬

- **병렬처리_parallel-processing**: 병렬 작업 실행
- **브랜드컷_brand-cut**: 결과 검증 패턴 (Step 6: 품질 검증)
- **에러처리및재시도_error-handling-retry**: 에러 및 재시도

## 참고 파일

- **Director 노드 예제**:
  - `Linn_node/Linn_Director_v3.py` (Creative Director)
  - `Linn_node/Linn_ProductDirector.py` (Product Director)
  - `Linn_node/Linn_image_EcommerceDirector.py` (Ecommerce Director)

---

**작성일**: 2026-01-21
**버전**: 1.0
**관련 스킬**: 병렬처리_parallel-processing, 브랜드컷_brand-cut
