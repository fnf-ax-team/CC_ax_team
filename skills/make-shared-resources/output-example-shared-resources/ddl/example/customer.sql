-- 테이블: customer
-- 설명: 고객 기본 정보 테이블
-- 최종 수정: 2024-02-04
-- 담당자: 데이터팀 홍길동

CREATE TABLE customer (
    customer_id     BIGINT PRIMARY KEY AUTO_INCREMENT,
    customer_name   VARCHAR(100) NOT NULL,
    email           VARCHAR(255) UNIQUE,
    phone           VARCHAR(20),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    status          VARCHAR(20) DEFAULT 'ACTIVE'
);

-- 인덱스
CREATE INDEX idx_customer_email ON customer(email);
CREATE INDEX idx_customer_status ON customer(status);

-- 참고사항
-- - status: ACTIVE, INACTIVE, SUSPENDED
-- - 개인정보 포함 테이블 (보안 주의)
