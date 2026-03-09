---
name: fnf-dept-mapping
description: F&F 사내 챗봇 로그 분석을 위한 부서-키워드 매핑 스킬. 사용자 질문을 분석하여 담당 부서(총무팀, 인사팀, 회계팀, 자금팀, 법무팀, 정보보안팀, 커뮤니케이션팀)를 자동 분류하고, 관련 문서와 핵심 키워드를 매칭. 챗봇 실패 로그 분석, 부서별 문의 통계, FAQ 개선점 도출에 활용. "챗봇 로그 분석", "부서 분류", "질문 매핑", "FAQ 분석" 요청 시 트리거.
---

# F&F 부서-키워드 매핑 스킬

사내 챗봇(Jane_Agent) 로그를 분석하여 질문을 담당 부서로 분류하고, 관련 문서를 매칭하는 스킬.

## 부서별 키워드 매핑

### 1. 총무팀 (General Affairs)
**담당 업무**: 시설관리, 복지, 차량, 방문자, 사옥 운영

**핵심 키워드**:
- 시설: 회의실, 예약, 사옥, 층별안내, 주차, 주차권, 엘리베이터, 에어컨, 난방, 시설물, 수리, 고장
- 방문자: 방문객, 방문증, 게스트, 손님, 외부인, 접견실
- 차량: 법인차량, 렌터카, 하이패스, 주유, 차량예약, 운행일지
- 복지: 동호회, 레벨업, 외부교육, 리조트, 콘도, 복지포인트, 경조사
- 건강: 건강검진, 노드의원, 상담서비스, 단체보험
- 식당: 구내식당, Fresh Farm, 조식, 중식, 석식, 식권, 메뉴
- 헬스장: Fit Room, 피트니스, 운동, 샤워실
- 야근: 야근택시, 야근식대, 22:30, 카카오T비즈
- 사무용품: 비품, 소모품, 명함, 복합기, 프린터
- 우편: 등기, 택배, 퀵서비스

**관련 문서**:
- 방문객 관리 가이드
- 시설물 사용 안내
- 법인 차량 사용 가이드
- 복지제도 안내 (동호회, 레벨업, 리조트)
- 사옥 안내 및 회의실 예약
- 직원 건강서비스 안내
- 야근 택시비 신청 안내

---

### 2. 인사팀 (HR)
**담당 업무**: 인사제도, 급여, 평가, 휴가, 출산/육아, 복리후생

**핵심 키워드**:
- 근태: 출퇴근, 시차출근, 연장근무, 야근, 휴일근무, 대체휴가, 근무시간, 점심시간
- 휴가: 연차, 월차, 반차, 반반차, 경조휴가, 병가, 생리휴가, 휴가신청, 휴가조정
- 급여: 급여일, 28일, 연봉, 인센티브, 수당, AX수당, 핵심인재수당, 원천징수, iPayView, 급여명세서
- 평가: 시즌평가, Annual평가, SS, FW, 승진, 승진연한, 정기승진, 특별승진
- 출산육아: 출산휴가, 육아휴직, 임신기단축근무, 육아기단축근무, 배우자출산휴가, 산전검사, 난임휴가, 유산휴가, 사산휴가, Mom Gift Box
- 복리후생: 통신비, 차량유지비, 학자금, 보육료, 장기근속, 입사선물, 생일선물, 명절선물
- 직원할인: 직원구매, 포인트, MLB, Discovery, 바닐라코, 아트박스, 할인율
- 증명서: 재직증명서, 경력증명서, 급여명세서, 원천징수영수증
- 입퇴사: 입사, 퇴사, 퇴직, 퇴직금, 퇴직프로세스, 사내추천, 사내공모
- 규정: 사규, 인사규정, 취업규칙, 겸직, VOE, 직장내괴롭힘, 성희롱

**담당자 키워드**: HR팀, 인사팀, 조수홍, 박성우

**관련 문서**:
- HR 가이드 (인사제도 및 규칙 + 복지소개 + 사옥소개)
- 인사 관련 문의 FAQ
- HR 관련 자주하는 질문

---

### 3. 회계팀 (Accounting)
**담당 업무**: SA시스템, 비용정산, 매출정산, 출장비, 생산비, 원천세

**핵심 키워드**:
- SA시스템: SA, Simply Account, 비용정산, 매출정산, 전표, 품의, 마감, 마감일, 영업일 3일
- 법인카드정산: 법인카드, 안분, 코스트센터, 제외처리, 취소, 개인사용
- 세금계산서: 세금계산서, 역발행, 정발행, 부가세, 부가세코드, V1, V3, VZ
- 계정과목: 복리후생비, 여비교통비, 통신비, 소모품비, 광고선전비, 접대비, 지급수수료, 지급임차료, 샘플구입대, 유무형자산
- 해외출장: 출장비, 사전품의, 출장코드, 일비, 간편정산, 정산표, 초과사용, 사유서, 환율
- 생산비: FOB, DDP, 외담대, 물대, 관부가세, 부대비, 선적일, 수입신고일, 입고일, M-ERP, GOMS
- 클레임: 미입고, 숏티지, 소비자클레임대, 제품하자, 클레임합의서
- 원천세: 일용직, 사업소득, 기타소득, 3.3%, 20%, 4대보험, 경품, 포상금
- 선급금: 선급금, 샘플대, 수입통관비, 관세, 관세사, 선급대체
- BP: 거래처, BP마스터, 사업자등록증, 계좌등록

**담당자 키워드**: 회계팀, 박성은, 강지혜, 박재윤

**관련 문서**:
- SA 시스템 개요 및 비용/매출 정산 가이드
- 해외 출장비 정산 안내
- 생산비 지급/마감 프로세스 + 클레임 프로세스
- 원천세 업무 개요 및 정산 가이드
- 선급금 신청 프로세스 (샘플대 수입통관비)
- 회계 계정 및 담당자 안내
- 회계팀 자주하는 질문

---

### 4. 자금팀 (Finance)
**담당 업무**: 법인카드 발급/관리, 자금 지급

**핵심 키워드**:
- 법인카드: 개인형법인카드, 국민카드, 카드한도, 한도증액, 카드재발급, 카드반납, 카드분실
- 카드사용: 결제, ISP, 온라인결제, 해외결제, 할부, 교통카드
- 정산: 정산마감, 미정산, 급여공제, 22일, 23일
- 공용카드: 공용법인카드, 카드신청
- 기타: 주업종코드, 중견기업확인서, 입금계좌

**담당자 키워드**: 자금팀, 이혜연, 박선영, 박나연

**관련 문서**:
- 개인형 법인카드 가이드

---

### 5. 법무팀 (Legal)
**담당 업무**: 계약검토, E-LAW시스템, 상표관리, 인감관리

**핵심 키워드**:
- E-LAW: E-LAW, 이로우, 계약검토, 계약생성, 계약체결, 법무검토, 법무승인
- 계약: 계약서, 표준계약, 계약템플릿, 계약변경, 연장합의서, 변경합의서, 재계약
- 서명/날인: 전자서명, 문서서명, 날인, 인감, 법인인감, 사용인감, 날인품의
- 자문: 법무자문, 법률자문, 내용증명
- 상표: 상표, 상표관리, 상표등록, 상표검토, 위조품, IP
- 공문: 공문발송, 사업자등록신청
- 해외법무: 해외계약, DocuSign, 도큐사인

**담당자 키워드**: 법무팀, 김지원, 김라연, 우지영, 김경민

**관련 문서**:
- New E-LAW 기본 안내
- 법무팀 계약 관련 자주하는 질문
- 상표관리시스템 매뉴얼
- 해외법무 관련 문의
- 법인 인감 사용 가이드

---

### 6. 정보보안팀/IT팀 (Information Security / IT)
**담당 업무**: 네트워크, 보안프로그램, VPN, 시스템접근권한

**핵심 키워드**:
- 네트워크: Wi-Fi, 와이파이, FNF, FNF_EX, FNF_GUEST, 인터넷, 네트워크, MAC주소
- VPN: SSL VPN, VPN, 외부접속, 원격접속, FortiClient
- NAC: NAC, 네트워크접근제어, 사용자인증, Genian
- 보안프로그램: Privacy-i, DLP, 개인정보검사, 파일반출, 반출승인, 암호화, 복호화
- VDI: VDI, 망분리, 가상PC, Horizon, 공용PC, 전용PC
- NAS: NAS, 공용폴더, 네트워크드라이브, 폴더접근
- 권한신청: Jira, 티켓, 권한신청, 계정신청, 방화벽
- DB접근: HIWARE, 쿼리, 데이터마스킹, DB접근
- 보안서약: 보안서약서, 비밀유지서약서, PC초기화, 포맷

**담당자 키워드**: 정보보안팀, IT팀

**관련 문서**:
- Jira 티켓 작성 가이드
- Privacy-i Agent 설치 및 가이드
- FNF Horizon VDI 가이드
- 정보보안팀 자주하는 질문
- 방문자용 Wi-Fi 인증 방법
- HIWARE 시스템 사용 안내
- 무선 네트워크(Wi-Fi) 이용 가이드
- SSL-VPN PC/모바일 설치 가이드
- NAC 개요 및 사용자 인증 절차

---

### 7. 커뮤니케이션팀 (Communications)
**담당 업무**: 회사정보, CEO메시지, 기업문화, 대외활동

**핵심 키워드**:
- 회사정보: F&F, 에프앤에프, 회사소개, 기업소개, 회사연혁
- 미션/비전: 미션, 비전, 핵심가치, MVC, 일하는방식
- CEO: 김창수, 회장님, 대표님, CEO, 신년사
- 브랜드: MLB, 디스커버리, Discovery, 듀베티카, 세르지오타키니, 바닐라코
- DT전략: DT, DT2.0, DCS, Digital Conveyor System, O2O2O, 디지털전환
- 글로벌: 글로벌, 해외진출, 중국, 아시아, K패션
- 수상: 수상, EY, 납세의탑, 수출의탑
- 뉴스: 보도자료, 언론, 기사, 뉴스

**관련 문서**:
- 대표님 소개 (김창수 회장 경영철학)
- 에프앤에프 MVC
- 회사 소식 (신사옥 이전, 글로벌사업 보도자료)
- 대외 활동 (수상, 사회공헌)
- CEO 메세지 (신년사, 타운홀미팅, 인터뷰)

---

## 데이터 전처리 규칙

### 1. 챗봇 응답(response) 필드 처리

챗봇의 `response` 필드에는 내부 추론 과정이 포함될 수 있습니다. 사용자에게 실제로 전달된 답변만 추출하기 위해 다음 규칙을 적용합니다.

**추론 태그 제거 규칙:**
- `<sequential>` 태그와 `</sequential>` 태그 사이의 내용은 챗봇 내부 추론 과정이므로 제거
- 태그가 없는 응답은 전체가 사용자 응답으로 처리
- 태그 이후 내용만 실제 사용자 응답으로 사용

**예시:**
```
# 원본 response
<sequential>
사용자가 명함 신청에 대해 묻고 있습니다.
총무팀 관련 문서를 검색합니다.
명함 신청 프로세스를 안내해야 합니다.
</sequential>
명함 신청은 인트라넷 > 총무 > 명함신청 메뉴에서 가능합니다.

# 처리 후 (실제 사용자 응답)
명함 신청은 인트라넷 > 총무 > 명함신청 메뉴에서 가능합니다.
```

**Python 코드:**
```python
import re

def extract_user_response(response):
    """챗봇 응답에서 실제 사용자 응답만 추출"""
    if pd.isna(response):
        return response

    response = str(response)

    # <sequential>...</sequential> 태그 및 내용 제거
    # 여러 개의 sequential 태그가 있을 수 있으므로 반복 처리
    pattern = r'<sequential>.*?</sequential>'
    cleaned = re.sub(pattern, '', response, flags=re.DOTALL)

    # 앞뒤 공백 제거
    cleaned = cleaned.strip()

    return cleaned if cleaned else response

# DataFrame에 적용
df['user_facing_response'] = df['response'].apply(extract_user_response)
```

---

### 2. 계층적 질문 그룹핑 (2단계 구조)

동일한 주제의 질문들을 **상위 그룹(주제)**과 **하위 그룹(세부 의도)**으로 계층화하여 정확한 빈도를 계산합니다.

**핵심 원칙:**
1. **2단계 계층 구조**: 주제(Topic) → 세부 의도(Intent)
2. **상위 그룹**: 핵심 주제 키워드로 묶음 (예: 가족돌봄, 법인카드, wifi)
3. **하위 그룹**: 세부 의도로 분류 (예: 신청, 급여, 품의가이드, 오류)
4. **대표 질문**: 각 그룹에서 가장 빈도 높은 원본 질문 선택

**출력 형식 예시:**
```
■ 가족돌봄 (8건)
  └ 일반/개념 (5건): "가족돌봄휴가"
  └ 품의가이드 (1건): "가족돌봄휴가 품의가이드"
  └ 급여 (1건): "가족돌봄휴가 급여"
  └ 휴직 (1건): "가족돌봄 휴직"

■ 법인카드 (25건)
  └ 비밀번호 (8건): "법인카드 비밀번호 뭐야"
  └ 신청 (6건): "법인카드 신청 방법"
  └ 한도 (5건): "법인카드 한도 증액"
  └ 정산 (4건): "법인카드 정산 방법"
  └ 일반 (2건): "법인카드"
```

**Python 코드:**
```python
import re
from collections import Counter, defaultdict

# 1단계: 핵심 주제 키워드 (상위 그룹)
TOPIC_KEYWORDS = [
    # HR 관련
    '가족돌봄', '연차', '휴가', '병가', '대체휴가', '육아휴직', '출산휴가',
    '급여', '수당', '인센티브', '퇴직', '퇴직금', '승진', '평가',
    '재직증명서', '증명서', '경조', '복지',
    # 총무 관련
    '명함', '회의실', '주차', '리조트', '동호회', '레벨업', '야근택시',
    '직원할인', '직원구매', '포인트', '건강검진', '식당', '헬스장',
    # 회계 관련
    '법인카드', '출장', '정산', '품의', '전표', '세금계산서', '비용',
    # 자금 관련
    '카드한도', '한도증액',
    # IT/보안 관련
    'wifi', 'vpn', 'vdi', '인트라넷', '팀즈',
    # 법무 관련
    'elaw', '계약서', '상표',
    # 시스템
    'sa', 'merp', 'serp',
]

# 2단계: 세부 의도 키워드 (하위 그룹)
INTENT_KEYWORDS = {
    '신청': ['신청', '요청', '등록', '제출'],
    '방법/가이드': ['방법', '가이드', '절차', '프로세스', '매뉴얼'],
    '품의': ['품의', '결재', '승인'],
    '급여/금액': ['급여', '금액', '비용', '얼마', '돈'],
    '한도': ['한도', '증액', '상향'],
    '비밀번호': ['비밀번호', '비번', '패스워드'],
    '담당자': ['담당자', '담당', '연락처', '문의처', '누구'],
    '기간/일정': ['기간', '일정', '언제', '며칠', '날짜'],
    '조건/자격': ['조건', '자격', '대상', '요건'],
    '오류/문제': ['오류', '에러', '안됨', '안돼', '실패', '문제'],
    '연결/접속': ['연결', '접속', '로그인'],
    '변경/취소': ['변경', '취소', '삭제', '수정'],
    '조회/확인': ['조회', '확인', '보기', '현황'],
    '휴직': ['휴직'],
}

# 동의어 매핑 (변형 → 대표어)
SYNONYM_MAP = {
    '법카': '법인카드', '회사카드': '법인카드',
    '비번': '비밀번호', '비번호': '비밀번호',
    '와이파이': 'wifi', 'wi-fi': 'wifi',
    '이로우': 'elaw', 'e-law': 'elaw',
    '에스에이': 'sa', '브이피엔': 'vpn',
    '가족 돌봄': '가족돌봄', '가족돌봄휴가': '가족돌봄',
    '가족돌봄휴직': '가족돌봄',
    '월차': '휴가', '반차': '휴가', '휴무': '휴가',
}

# 불용어 (의미 없는 패턴)
STOPWORDS = [
    '어떻게', '뭐야', '뭐지', '알려줘', '알려주세요', '좀', '요',
    '해줘', '줘', '하는법', '궁금해', '싶어', '할수있', '가능',
]

def normalize_text(text):
    """텍스트 정규화"""
    if pd.isna(text):
        return ''
    text = str(text).lower().strip()
    for variant, standard in SYNONYM_MAP.items():
        text = text.replace(variant, standard)
    return text

def extract_topic(query):
    """질문에서 핵심 주제 추출"""
    normalized = normalize_text(query)
    for topic in TOPIC_KEYWORDS:
        if topic in normalized:
            return topic
    return None

def extract_intent(query, topic):
    """질문에서 세부 의도 추출"""
    normalized = normalize_text(query)
    # 주제 키워드 제거 후 의도 파악
    remaining = normalized.replace(topic, '') if topic else normalized

    for intent_name, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in remaining:
                return intent_name

    # 의도 키워드가 없으면 '일반/개념'
    return '일반/개념'

def hierarchical_grouping(df, query_column='user_query'):
    """계층적 질문 그룹핑 (주제 → 세부의도)"""

    results = defaultdict(lambda: defaultdict(list))

    for idx, row in df.iterrows():
        query = row[query_column]
        topic = extract_topic(query)

        if topic:
            intent = extract_intent(query, topic)
            results[topic][intent].append(query)
        else:
            # 주제 없으면 정규화된 질문 자체를 키로
            normalized = normalize_text(query)
            for sw in STOPWORDS:
                normalized = normalized.replace(sw, ' ')
            normalized = re.sub(r'\s+', ' ', normalized).strip()
            results[normalized]['일반/개념'].append(query)

    # 결과 정리
    final_results = []
    for topic, intents in results.items():
        topic_total = sum(len(queries) for queries in intents.values())

        intent_details = []
        for intent, queries in sorted(intents.items(), key=lambda x: -len(x[1])):
            # 대표 질문: 가장 빈도 높은 원본 질문
            rep_query = Counter(queries).most_common(1)[0][0]
            intent_details.append({
                'intent': intent,
                'count': len(queries),
                'representative': rep_query
            })

        final_results.append({
            'topic': topic,
            'total_count': topic_total,
            'intents': intent_details
        })

    # 총 건수 기준 정렬
    final_results.sort(key=lambda x: -x['total_count'])

    return final_results

# 사용 예시
# grouped = hierarchical_grouping(dept_df, 'user_query')
# for item in grouped[:10]:
#     print(f"■ {item['topic']} ({item['total_count']}건)")
#     for intent in item['intents']:
#         print(f"  └ {intent['intent']} ({intent['count']}건): {intent['representative']}")
```

**출력 형식 (노션):**
```
■ 가족돌봄 (8건)
  └ 일반/개념 (5건): "가족돌봄휴가"
  └ 품의 (1건): "가족돌봄휴가 품의가이드"
  └ 급여/금액 (1건): "가족돌봄휴가 급여"
  └ 휴직 (1건): "가족돌봄 휴직"

■ wifi (15건)
  └ 연결/접속 (10건): "와이파이 연결 방법"
  └ 비밀번호 (3건): "wifi 비밀번호"
  └ 일반/개념 (2건): "wifi"
```

**주의사항:**
- 주제 키워드가 포함된 질문만 해당 주제로 그룹화
- 세부 의도는 주제 제거 후 남은 텍스트에서 추출
- 의도 키워드가 없으면 "일반/개념"으로 분류
- 대표 질문은 각 세부 의도 내에서 가장 빈도 높은 원본 질문

---

## 분류 규칙

### 우선순위 매칭
1. **정확 키워드 매칭**: 질문에 핵심 키워드가 직접 포함된 경우
2. **유사어 매칭**: 동의어, 약어, 오타 포함 매칭
3. **문맥 매칭**: 키워드 조합으로 부서 유추

### 복합 질문 처리
- 여러 부서 관련 키워드 포함 시 → 가장 관련도 높은 부서 1개 선택
- 관련도 동일 시 → 첫 번째 언급된 키워드의 부서 선택

### 미분류 처리
- 매칭 키워드 없음 → "미분류"
- 일반 인사말/잡담 → "미분류"

---

## 분석 출력 형식

챗봇 로그 분석 시 다음 형식으로 출력:

```
| 원본질문 | 담당부서 | 매칭키워드 | 관련문서 | 신뢰도 |
|----------|----------|------------|----------|--------|
| 연차 신청 방법 | 인사팀 | 연차, 신청 | HR 가이드 | 높음 |
| VPN 연결 안됨 | 정보보안팀 | VPN, 연결 | SSL-VPN 가이드 | 높음 |
```

---

## 키워드 동의어/변형

### 자주 사용되는 변형
- 휴가 = 연차, 월차, 반차, 휴무, 쉬는날
- 급여 = 월급, 봉급, 연봉, 페이
- 카드 = 법인카드, 법카, 회사카드
- 와이파이 = Wi-Fi, wifi, 무선, 무선랜
- 출장 = 해외출장, 국내출장, 외근
- 계약 = 계약서, 컨트랙, contract
- 시스템 = SA, E-LAW, Jira, HIWARE, VDI

### 오타/약어 처리
- 이로우 = E-LAW
- 프라이버시아이 = Privacy-i
- 에스에이 = SA
- 브이피엔 = VPN
- 나스 = NAS

---

## 노션 DB 연동

분석 결과를 노션 데이터베이스에 자동으로 저장합니다.

### 노션 설정 정보
```
NOTION_API_KEY: [사용자 설정 필요]
DATABASE_ID: [사용자 설정 필요]
```

### 노션 DB 스키마 (권장)

**월별 로그 분석 DB** 속성:
| 속성명 | 타입 | 설명 |
|--------|------|------|
| 분석일자 | Date | 분석 실행 날짜 |
| 데이터기간 | Text | 로그 데이터 기간 (예: 2025-09 ~ 2026-02) |
| 총질문수 | Number | 전체 질문 건수 |
| 응답성공률 | Number | 응답 성공 비율 (%) |
| 미응답률 | Number | 미응답 비율 (%) |
| Good피드백 | Number | 긍정 피드백 건수 |
| Bad피드백 | Number | 부정 피드백 건수 |
| 상태 | Select | 완료/진행중/오류 |

### 분석 결과 저장 구조

분석 완료 시 노션 페이지에 다음 내용을 블록으로 추가:

1. **요약 통계** (Callout 블록)
   - 데이터 기간, 총 질문 수, 응답률, 피드백 현황

2. **부서별 질문 분류** (Table 블록)
   - 부서명, 질문수, 비율

3. **질문 유형 분포** (Table 블록)
   - 유형별 건수 및 비율

4. **부서별 자주하는 질문 TOP 10** (Toggle 블록)
   - 각 부서별 상위 10개 질문

5. **미응답 질문 TOP 10** (Toggle 블록)
   - 각 부서별 미응답 상위 10개 질문

6. **월별 통계** (Table 블록)
   - 월, 질문수, 미응답률, Bad율, Good율

### Python 코드 예시

```python
import requests
from datetime import datetime

NOTION_API_KEY = "your_notion_api_key"
DATABASE_ID = "your_database_id"

headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def create_analysis_page(analysis_results):
    """분석 결과를 노션 페이지로 생성"""

    url = "https://api.notion.com/v1/pages"

    # 페이지 속성 설정
    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "제목": {
                "title": [{"text": {"content": f"챗봇 로그 분석 - {datetime.now().strftime('%Y-%m-%d')}"}}]
            },
            "분석일자": {
                "date": {"start": datetime.now().isoformat()}
            },
            "데이터기간": {
                "rich_text": [{"text": {"content": analysis_results['period']}}]
            },
            "총질문수": {
                "number": analysis_results['total_queries']
            },
            "응답성공률": {
                "number": analysis_results['response_rate']
            },
            "미응답률": {
                "number": analysis_results['no_response_rate']
            },
            "Good피드백": {
                "number": analysis_results['good_count']
            },
            "Bad피드백": {
                "number": analysis_results['bad_count']
            },
            "상태": {
                "select": {"name": "완료"}
            }
        },
        "children": build_page_content(analysis_results)
    }

    response = requests.post(url, headers=headers, json=data)
    return response.json()

def build_page_content(results):
    """페이지 본문 블록 생성"""
    blocks = []

    # 1. 요약 통계 (Callout)
    blocks.append({
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [{"text": {"content": f"""
📊 분석 요약
• 데이터 기간: {results['period']}
• 총 질문 수: {results['total_queries']:,}건
• 응답 성공률: {results['response_rate']:.1f}%
• 미응답률: {results['no_response_rate']:.1f}%
• Good 피드백: {results['good_count']}건
• Bad 피드백: {results['bad_count']}건
"""}}],
            "icon": {"emoji": "📈"}
        }
    })

    # 2. 부서별 질문 분류 (Heading + Table)
    blocks.append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"text": {"content": "1. 부서별 질문 분류"}}]
        }
    })

    # 테이블 추가
    blocks.append({
        "object": "block",
        "type": "table",
        "table": {
            "table_width": 3,
            "has_column_header": True,
            "children": build_dept_table_rows(results['dept_stats'])
        }
    })

    # 3. 월별 통계 (Toggle)
    blocks.append({
        "object": "block",
        "type": "toggle",
        "toggle": {
            "rich_text": [{"text": {"content": "📅 월별 상세 통계"}}],
            "children": build_monthly_stats_blocks(results['monthly_stats'])
        }
    })

    # 4. 부서별 자주하는 질문 (Toggle)
    for dept, questions in results['top_questions'].items():
        blocks.append({
            "object": "block",
            "type": "toggle",
            "toggle": {
                "rich_text": [{"text": {"content": f"🏢 {dept} - 자주하는 질문 TOP 10"}}],
                "children": build_question_list(questions)
            }
        })

    # 5. 미응답 질문 (Toggle)
    blocks.append({
        "object": "block",
        "type": "toggle",
        "toggle": {
            "rich_text": [{"text": {"content": "⚠️ 미응답 질문 TOP 10 (부서별)"}}],
            "children": build_no_response_blocks(results['no_response_questions'])
        }
    })

    return blocks

def build_dept_table_rows(dept_stats):
    """부서 통계 테이블 행 생성"""
    rows = []
    # 헤더 행
    rows.append({
        "type": "table_row",
        "table_row": {
            "cells": [
                [{"text": {"content": "부서"}}],
                [{"text": {"content": "질문수"}}],
                [{"text": {"content": "비율"}}]
            ]
        }
    })
    # 데이터 행
    for dept, stats in dept_stats.items():
        rows.append({
            "type": "table_row",
            "table_row": {
                "cells": [
                    [{"text": {"content": dept}}],
                    [{"text": {"content": f"{stats['count']:,}건"}}],
                    [{"text": {"content": f"{stats['ratio']:.1f}%"}}]
                ]
            }
        })
    return rows

def build_question_list(questions):
    """질문 목록 블록 생성"""
    blocks = []
    for i, (question, count) in enumerate(questions, 1):
        blocks.append({
            "object": "block",
            "type": "numbered_list_item",
            "numbered_list_item": {
                "rich_text": [{"text": {"content": f"[{count}건] {question[:80]}"}}]
            }
        })
    return blocks

def build_monthly_stats_blocks(monthly_stats):
    """월별 통계 블록 생성"""
    blocks = []
    for month, stats in monthly_stats.items():
        blocks.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"text": {"content": f"{month}: {stats['total']}건 | 미응답 {stats['no_response_rate']:.1f}% | Bad {stats['bad_rate']:.1f}% | Good {stats['good_rate']:.1f}%"}}]
            }
        })
    return blocks

def build_no_response_blocks(no_response_data):
    """미응답 질문 블록 생성"""
    blocks = []
    for dept, questions in no_response_data.items():
        blocks.append({
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"text": {"content": dept}}]
            }
        })
        for i, (question, count) in enumerate(questions[:10], 1):
            blocks.append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": [{"text": {"content": f"[{count}건] {question[:80]}"}}]
                }
            })
    return blocks
```

### 사용 방법

1. **노션 통합 설정**
   - https://www.notion.so/my-integrations 에서 새 통합 생성
   - API 키 복사

2. **데이터베이스 연결**
   - 분석 결과를 저장할 노션 DB 생성
   - DB 페이지에서 "연결" → 생성한 통합 추가
   - DB ID 복사 (URL에서 확인)

3. **환경 변수 설정**
   ```
   NOTION_API_KEY=secret_xxx
   NOTION_DATABASE_ID=xxx
   ```

4. **분석 실행**
   ```
   /fnf-dept-mapping [엑셀파일명] --notion
   ```

### 자동화 옵션

- `--notion`: 분석 결과를 노션에 자동 저장
- `--notion-only`: 노션 저장만 수행 (콘솔 출력 생략)
- `--update [page_id]`: 기존 페이지 업데이트

---

## 사내 시스템 정규화 규칙

사용자가 시스템 이름을 다양한 형태로 입력할 수 있습니다. 아래 정규화 규칙을 적용하여 동일 시스템으로 인식합니다.

### 1. SA (회계 비용정산 시스템)

**정규화 대상:**
```
SA, sa, Sa, SA정산, SA비용정산, SA시스템, 에스에이, 에스 에이
```

**예상 오타:**
```
sa정ㅅ나, SA저산, 에스에이정산
```

**관련 키워드:**
- 비용정산, 매출정산, 전표, 품의, 마감
- 법카정산, 법인카드정산, 일반매입
- 세금계산서, 계정과목, 출장비정산
- BP마스터, 거래처등록

**담당부서:** 회계팀

---

### 2. E-LAW (법무 계약검토 시스템)

**정규화 대상:**
```
E-LAW, e-law, ELAW, elaw, E-Law, e-Law, E-law, 이로우, 이-로우, 이로우시스템
```

**예상 오타:**
```
e-raw, E-RAW, eraw, 이로오, 이러우, 일로우, e-low, E-LOW
```

**관련 키워드:**
- 계약검토, 계약생성, 계약체결, 법무검토
- 전자서명, 문서서명, 날인품의
- 법무자문, 자문요청, 자문시스템
- 계약서, 템플릿, 표준계약

**담당부서:** 법무팀

---

### 3. Jira (IT 업무요청 시스템)

**정규화 대상:**
```
Jira, JIRA, jira, 지라, 지라시스템, Jira시스템, 지라티켓, Jira티켓
```

**예상 오타:**
```
지랴, 자라, 지아라, jira, jria, 지러
```

**관련 키워드:**
- IT업무요청, IT 업무요청, IT요청
- 권한요청, 권한신청, 계정신청
- 데이터요청, 방화벽신청
- 티켓, 티켓작성

**담당부서:** 정보보안팀/IT팀

---

### 4. HIWARE (DB 접근 시스템)

**정규화 대상:**
```
HIWARE, Hiware, hiware, HiWare, 하이웨어, 하이웨어시스템, 하이웨어결재
```

**예상 오타:**
```
highware, 하이웨아, 하이웨얼, hiwar, 하이워
```

**관련 키워드:**
- DB접근, 쿼리, 데이터조회
- 데이터마스킹, 쿼리타입제한
- 결재위임

**담당부서:** 정보보안팀/IT팀

---

### 5. Milkyway (데이터 분석 플랫폼)

**정규화 대상:**
```
Milkyway, milkyway, MILKYWAY, 밀키웨이, 밀키웨이시스템
```

**예상 오타:**
```
milkiway, 밀키웨이, 밀키웨잉, milkway, 밀크웨이, 밀키웨이
```

**관련 키워드:**
- 데이터분석, 데이터확인, 데이터요청
- 샘플대등록, 샘플비

**담당부서:** IT팀

---

### 6. 프똑이 (사내 AI 챗봇)

**정규화 대상:**
```
프똑이, 프똑, F-talk, f-talk, FTALK, ftalk, F-Talk, 사내챗봇, 에프톡
```

**예상 오타:**
```
프도기, 프또기, 픗도기, 픗또기, 프똑아, 푸똑이, 프똣이, ftlak, f-tlak
```

**관련 키워드:**
- 챗봇, AI챗봇, 사내AI
- 질문, 문의

---

### 7. SERP (유통 ERP)

**정규화 대상:**
```
SERP, serp, S-ERP, s-erp, S-erp, 에스이알피, 유통ERP, 유통erp, 유통이알피
```

**예상 오타:**
```
srrp, serrp, 셀프, 서프, s-erp, 에스알피
```

**관련 키워드:**
- 유통시스템, AP재고, AP코드
- 계정잠김, 비밀번호초기화

**담당부서:** IT팀

---

### 8. MERP (생산 ERP)

**정규화 대상:**
```
MERP, merp, M-ERP, m-erp, M-erp, 엠이알피, 생산ERP, 생산erp
```

**예상 오타:**
```
merrp, mrrp, 엠알피, 멀프, m-erp
```

**관련 키워드:**
- 생산시스템, 생산비, FOB, DDP
- 비밀번호찾기, 계정등록

**담당부서:** IT팀

---

### 9. 인트라넷 (사내 포털)

**정규화 대상:**
```
인트라넷, INTRANET, intranet, Intranet, 인트라넷포털, 포털, 사내포털, 사내인트라넷, 인트라넷시스템
```

**예상 오타:**
```
인트라넸, 인트라넵, 인트러넷, 인트라네, intarnet, intraent
```

**관련 키워드:**
- 품의, 결재, 공지사항
- 바탕화면설치, 다운로드

**담당부서:** IT팀

---

### 10. PLM (제품 관리 시스템)

**정규화 대상:**
```
PLM, plm, Plm, 피엘엠, PLM시스템
```

**예상 오타:**
```
plm, pml, 플름, 피에엘엠, plm시스템
```

**관련 키워드:**
- 상품설명서, 시즌폴더, 협력사등록
- 로그인, 권한요청

**담당부서:** IT팀

---

### 11. iPayView (급여 확인 시스템)

**정규화 대상:**
```
iPayView, IPAYVIEW, ipayview, IPayView, 아이페이뷰
```

**예상 오타:**
```
ipayviwe, ipay view, i pay view, 아이패뷰, 아이페이부
```

**관련 키워드:**
- 급여확인, 급여시스템, 급여명세서
- 연봉확인, 원천징수, 연말정산
- 회사코드

**담당부서:** 인사팀

---

### 12. VOE (직원 의견 시스템)

**정규화 대상:**
```
VOE, voe, Voe, 브이오이, Voice of Employee, VOE시스템
```

**예상 오타:**
```
veo, 보이, 브이오에, v.o.e
```

**관련 키워드:**
- 직원의견, 제안, 건의

**담당부서:** 인사팀

---

### 13. VARCO (AI 디자인 시스템) ⚠️ 종료 예정

**정규화 대상:**
```
VARCO, varco, Varco, 바르코, 바르코시스템
```

**예상 오타:**
```
varcoi, varoco, 발코, 바코, barco
```

**관련 키워드:**
- AI디자인, 이미지생성, 이미지편집

**담당부서:** AX마케팅팀

**⚠️ 서비스 종료 안내:**
```
- 서비스 종료일: 2026년 2월 28일 (새 이미지 생성/편집 기능 중단)
- 데이터 다운로드 마감: 2026년 3월 6일 (금)
- 마감 이후 모든 데이터 삭제, 복구 불가
- 필요한 이미지는 반드시 3월 6일까지 백업 필요
- 문의: AX마케팅팀 송예린 대리
- 공지: https://portal.fnf.co.kr/board/69815038ba29a9ad76058169
```

---

### 14. GOMS (생산 관리 시스템)

**정규화 대상:**
```
GOMS, goms, Goms, 곰스, GOMS시스템
```

**예상 오타:**
```
gom, 곰, 고므스, gomms
```

**관련 키워드:**
- 생산관리, 권한요청
- URL: https://goms.fnf.co.kr/login.do

**담당부서:** IT팀

---

### 15. GSCM / SCM (공급망 관리)

**정규화 대상:**
```
GSCM, gscm, Gscm, SCM, scm, Scm, 에스씨엠, 지에스씨엠
```

**예상 오타:**
```
gsmc, 지scm, g-scm, 에쓰씨엠
```

**관련 키워드:**
- 공급망, 발주, 재고

**담당부서:** IT팀

---

## 내부 용어 정규화

사내에서 줄여 쓰거나 비공식적으로 사용하는 용어입니다.

### 1. 법인카드

**정규화 대상:**
```
법인카드, 법카, 회사카드, 회사법카, 개인법카, 공용법카, 개인형법인카드, 공용법인카드
```

**예상 오타:**
```
법카드, 법ㅋ, 법가, 법인카느, 버인카드
```

**관련 키워드:**
- 카드한도, 한도증액, 카드발급, 카드분실
- ISP, 온라인결제, 해외결제
- 정산마감, 미정산, 급여공제

**담당부서:** 자금팀 (발급/한도), 회계팀 (정산)

---

### 2. Wi-Fi / 와이파이

**정규화 대상:**
```
Wi-Fi, WiFi, WIFI, wifi, Wifi, wi-fi, WI-FI, 와이파이, 무선네트워크, 무선랜, 무선인터넷
```

**예상 오타:**
```
와이파아, 와파, 와이화이, wif, wiif, 와이피, 외파이
```

**관련 키워드:**
- FNF_EX, FNF_GUEST, 게스트와이파이
- MAC주소, 인터넷연결, 네트워크
- 연결안됨, 접속불가

**담당부서:** 정보보안팀/IT팀

---

### 3. VPN

**정규화 대상:**
```
VPN, vpn, Vpn, 브이피엔, SSL VPN, SSL-VPN, FortiClient
```

**예상 오타:**
```
vpm, bpn, 비피엔, 브피엔, vpn신청
```

**관련 키워드:**
- 외부접속, 원격접속, 재택접속
- FortiClientVPN, 90일미접속

**담당부서:** 정보보안팀

---

### 4. VDI (가상 PC)

**정규화 대상:**
```
VDI, vdi, Vdi, 브이디아이, 가상PC, 가상피씨, Horizon, 호라이즌
```

**예상 오타:**
```
vd, 브디아, vdi시스템, 가상pc
```

**관련 키워드:**
- 망분리, OTP인증, MS Authenticator
- 공용PC, 전용PC

**담당부서:** 정보보안팀

---

### 5. Teams / 팀즈

**정규화 대상:**
```
Teams, TEAMS, teams, 팀즈, 팀스, MS Teams, MSTeams, 마이크로소프트팀즈
```

**예상 오타:**
```
팀스, 틈즈, temas, tema, 팀츠
```

**관련 키워드:**
- 화상회의, 회의록, 녹음, 미팅
- 채팅, 공유

**담당부서:** IT팀

---

### 6. Outlook / 아웃룩

**정규화 대상:**
```
Outlook, OUTLOOK, outlook, 아웃룩, 아웃룩메일
```

**예상 오타:**
```
아우룩, 아웃록, 아웉룩, outlock, outlok
```

**관련 키워드:**
- 회의실예약, 미팅예약, 일정
- 메일, 명함

**담당부서:** IT팀

---

## 정규화 Python 코드

```python
# 시스템 정규화 매핑
SYSTEM_NORMALIZE = {
    # SA
    'sa': 'SA', 'sa정산': 'SA', 'sa비용정산': 'SA', 'sa시스템': 'SA',
    '에스에이': 'SA', '에스 에이': 'SA',

    # E-LAW
    'e-law': 'E-LAW', 'elaw': 'E-LAW', 'e-Law': 'E-LAW', 'e-raw': 'E-LAW',
    '이로우': 'E-LAW', '이-로우': 'E-LAW', '이로오': 'E-LAW', 'e-low': 'E-LAW',

    # Jira
    'jira': 'JIRA', '지라': 'JIRA', '지라시스템': 'JIRA', '지라티켓': 'JIRA',
    '지랴': 'JIRA', 'jria': 'JIRA',

    # HIWARE
    'hiware': 'HIWARE', '하이웨어': 'HIWARE', 'highware': 'HIWARE',
    '하이웨아': 'HIWARE', '하이워': 'HIWARE',

    # Milkyway
    'milkyway': 'MILKYWAY', '밀키웨이': 'MILKYWAY', 'milkiway': 'MILKYWAY',
    '밀크웨이': 'MILKYWAY', 'milkway': 'MILKYWAY',

    # 프똑이
    'f-talk': '프똑이', 'ftalk': '프똑이', '프똑': '프똑이', '사내챗봇': '프똑이',
    '프도기': '프똑이', '프또기': '프똑이', '픗도기': '프똑이', '픗또기': '프똑이',
    'f-tlak': '프똑이', '에프톡': '프똑이',

    # SERP
    'serp': 'SERP', 's-erp': 'SERP', '에스이알피': 'SERP',
    '유통erp': 'SERP', '유통이알피': 'SERP',

    # MERP
    'merp': 'MERP', 'm-erp': 'MERP', '엠이알피': 'MERP',
    '생산erp': 'MERP', '엠알피': 'MERP',

    # 인트라넷
    'intranet': '인트라넷', '포털': '인트라넷', '사내포털': '인트라넷',
    'intarnet': '인트라넷', '인트러넷': '인트라넷',

    # PLM
    'plm': 'PLM', '피엘엠': 'PLM', 'pml': 'PLM',

    # iPayView
    'ipayview': 'IPAYVIEW', 'i pay view': 'IPAYVIEW', '아이페이뷰': 'IPAYVIEW',
    'ipay view': 'IPAYVIEW',

    # VOE
    'voe': 'VOE', '브이오이': 'VOE', 'voice of employee': 'VOE',

    # VARCO
    'varco': 'VARCO', '바르코': 'VARCO', 'varcoi': 'VARCO', 'barco': 'VARCO',

    # GOMS
    'goms': 'GOMS', '곰스': 'GOMS', 'gom': 'GOMS',

    # GSCM/SCM
    'gscm': 'GSCM', 'scm': 'SCM', '에스씨엠': 'SCM',

    # 법인카드
    '법카': '법인카드', '회사카드': '법인카드', '법가': '법인카드',
    '개인법카': '법인카드', '공용법카': '법인카드',

    # WiFi
    'wifi': 'Wi-Fi', 'wi-fi': 'Wi-Fi', '와이파이': 'Wi-Fi',
    '와이파아': 'Wi-Fi', '와파': 'Wi-Fi', '무선네트워크': 'Wi-Fi',

    # VPN
    'vpn': 'VPN', '브이피엔': 'VPN', 'vpm': 'VPN', 'forticlient': 'VPN',

    # VDI
    'vdi': 'VDI', '브이디아이': 'VDI', '가상pc': 'VDI', 'horizon': 'VDI',

    # Teams
    'teams': 'TEAMS', '팀즈': 'TEAMS', '팀스': 'TEAMS', 'ms teams': 'TEAMS',

    # Outlook
    'outlook': 'OUTLOOK', '아웃룩': 'OUTLOOK', '아우룩': 'OUTLOOK',
}

def normalize_system(text):
    """시스템 이름 정규화"""
    text_lower = text.lower().strip()
    return SYSTEM_NORMALIZE.get(text_lower, text)
```

---

## 종료 시스템 안내

서비스가 종료되었거나 종료 예정인 시스템입니다. 관련 질문 시 아래 안내가 필요합니다.

### VARCO (AI 디자인 시스템)

| 항목 | 내용 |
|------|------|
| **서비스 종료일** | 2026년 2월 28일 |
| **종료 내용** | 새로운 이미지 생성 및 편집 기능 중단 |
| **데이터 다운로드 마감** | 2026년 3월 6일 (금) |
| **마감 후** | 모든 데이터 삭제, 복구 불가 |
| **조치사항** | 필요한 이미지 3월 6일까지 반드시 백업 |
| **문의처** | AX마케팅팀 송예린 대리 |
| **관련공지** | https://portal.fnf.co.kr/board/69815038ba29a9ad76058169 |

**VARCO 관련 질문 시 응답 예시:**
```
VARCO 서비스는 2026년 2월 28일부로 종료됩니다.

■ 주요 일정
- 2/28: 새 이미지 생성/편집 기능 중단
- 3/6: 데이터 다운로드 마감 (이후 전체 삭제)

■ 조치사항
업무에 필요한 기존 결과물은 반드시 3월 6일까지 백업해주세요.

■ 문의: AX마케팅팀 송예린 대리
■ 공지: https://portal.fnf.co.kr/board/69815038ba29a9ad76058169
```
 