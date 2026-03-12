# MCP 배포용 환경변수 설정 가이드

## 필수 환경변수

MCP 서버(Orbit HTTP) 배포 시 아래 환경변수를 설정해야 합니다.

### Gemini API

```bash
GEMINI_API_KEY=key1,key2,key3,key4,key5
```

### 스토리지 (S3 모드 — MCP 필수)

```bash
# 읽기: 프리셋/모델 이미지를 S3에서 로드
FNF_STORAGE_MODE=s3
FNF_S3_BASE_URL=https://tmp-img-s3.s3.ap-northeast-2.amazonaws.com/LINN/fnf-studio

# 쓰기: 생성 결과물을 S3에 저장
FNF_OUTPUT_MODE=s3
FNF_S3_BUCKET=tmp-img-s3
FNF_S3_PREFIX=LINN/fnf-studio
FNF_S3_REGION=ap-northeast-2
```

### AWS 인증 (S3 업로드용)

```bash
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=ap-northeast-2
```

## 환경별 설정

### 로컬 개발 (내 PC에서 직접 실행)

```bash
# .env
GEMINI_API_KEY=key1,key2,key3
FNF_STORAGE_MODE=local    # db/ 폴더에서 직접 로드
FNF_OUTPUT_MODE=local     # Fnf_studio_outputs/ 에 저장
```

### MCP 배포 (Orbit HTTP 원격 서버)

```bash
# .env
GEMINI_API_KEY=key1,key2,key3
FNF_STORAGE_MODE=s3       # S3에서 프리셋/이미지 로드
FNF_OUTPUT_MODE=s3        # S3에 결과 업로드
FNF_S3_BASE_URL=https://tmp-img-s3.s3.ap-northeast-2.amazonaws.com/LINN/fnf-studio
FNF_S3_BUCKET=tmp-img-s3
FNF_S3_PREFIX=LINN/fnf-studio
FNF_S3_REGION=ap-northeast-2
```

## 데이터 흐름

```
[MCP 사용자] → [Orbit MCP 서버]
                    ↓
              core/storage.py
                    ↓
        FNF_STORAGE_MODE=s3 이면:
        프리셋 JSON → S3에서 다운로드 → 캐시
        이미지 → S3 URL로 Gemini API에 전달
                    ↓
        Gemini API 이미지 생성
                    ↓
        FNF_OUTPUT_MODE=s3 이면:
        결과 이미지 → S3 업로드
                    ↓
        S3 URL 반환 → MCP 사용자에게 전달
```

## S3 데이터 업로드 (최초 1회)

```bash
# 1. db/ 폴더 전체 업로드 (프리셋 JSON + 이미지)
python scripts/upload_db_to_s3.py --dry-run  # 미리보기
python scripts/upload_db_to_s3.py            # 실제 업로드

# 2. 프리셋 레퍼런스 이미지 업로드 (pose/expression/background)
python scripts/upload_preset_images_to_s3.py --dry-run
python scripts/upload_preset_images_to_s3.py
```

## 확인

S3 콘솔에서 확인:
https://ap-northeast-2.console.aws.amazon.com/s3/buckets/tmp-img-s3?prefix=LINN/fnf-studio/db/

파일 구조가 로컬 `db/` 폴더와 동일해야 합니다:
```
s3://tmp-img-s3/LINN/fnf-studio/
├── db/presets/common/pose_presets.json
├── db/presets/common/expression_presets.json
├── db/presets/common/background_presets.json
├── db/presets/brandcut/mlb/mlb_pose_presets.json
├── db/mlb_style/MLB_STYLE (1).jpg
├── db/인플테스트/3. 포즈/전신 (1).jpeg
└── ...
```
