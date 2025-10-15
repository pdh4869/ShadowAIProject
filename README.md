# PII Agent - 개인정보 탐지 시스템

ChatGPT 및 Gemini에서 파일 업로드 시 개인정보를 자동으로 탐지하는 Chrome 확장 프로그램 + Python 서버 시스템입니다.

## 주요 기능

### 📄 지원 파일 형식
- **문서**: PDF, DOCX, HWP, HWPX, TXT
- **오피스**: XLSX (엑셀), PPTX (파워포인트)
- **이미지**: PNG, JPG, JPEG, BMP, WEBP, GIF, TIFF

### 🔍 탐지 항목

#### 정규식 기반 탐지
- 전화번호 (010-1234-5678, 01012345678 등)
- 이메일 주소
- 생년월일 (1900~2006년생)
- 주민등록번호
- 외국인등록번호
- 운전면허번호
- 여권번호
- 계좌번호
- 카드번호
- IP 주소

#### NER 모델 기반 탐지
- **모델**: `soddokayo/klue-roberta-base-ner`
- **탐지 항목**:
  - `PS/PER`: 사람 이름 (3글자 이상, 한글 포함 필수)
  - `LOC/LC`: 위치/주소
- **필터링**:
  - 2글자 이하 제외
  - 숫자만 있는 경우 제외
  - 한글 없이 특수문자만 있는 경우 제외
  - 화이트리스트/블랙리스트 적용

#### 이미지 분석
- **얼굴 탐지**: MTCNN 모델 (신뢰도 98% 이상)
  - 얼굴 크기, 비율, keypoints 검증으로 오탐지 방지
  - 중복 이미지 자동 제거 (PDF)
- **OCR**: EasyOCR (한글/영어)
  - DOCX, PDF, HWP, HWPX, PPTX 내부 이미지 지원
  - 단일 이미지 파일 지원
  - 이미지 전처리 (대비 증가)

### 🌐 네트워크 정보 수집
- IP 주소 (로컬 네트워크)
- 컴퓨터 호스트명
- 브라우저 User-Agent
- 출처 URL

## 시스템 구조

```
Py_server/
├── extension/          # Chrome 확장 프로그램
│   ├── manifest.json
│   ├── background.js   # Service Worker
│   └── content.js      # 파일 감지 및 전송
├── native_host/        # Native Messaging Host
│   ├── host.py         # 네트워크 정보 수집
│   └── com.example.pii_host.json
├── server/             # Python 서버
│   ├── LocalServer.py  # FastAPI 서버
│   └── Logic.py        # 개인정보 탐지 로직
├── requirements.txt    # Python 패키지 목록
└── install.bat         # 자동 설치 스크립트
```

## 설치 방법

### 1. 필수 요구사항
- Python 3.8 이상
- Google Chrome 브라우저
- Windows 10/11

### 2. 자동 설치 (권장)

1. `install.bat` 파일을 **관리자 권한으로 실행**
2. Python 패키지 자동 설치
3. Native Messaging Host 자동 등록

### 3. Chrome 확장 프로그램 설치

1. Chrome에서 `chrome://extensions/` 접속
2. 우측 상단 "개발자 모드" 활성화
3. "압축해제된 확장 프로그램을 로드합니다" 클릭
4. `Py_server/extension` 폴더 선택

### 4. 환경 변수 설정 (선택)

HuggingFace 토큰이 필요한 경우:

```bash
set HF_TOKEN=your_huggingface_token_here
```

또는 시스템 환경 변수에 `HF_TOKEN` 추가

## 실행 방법

### 1. 서버 실행

```bash
cd Py_server/server
python LocalServer.py
```

서버가 `http://127.0.0.1:9000`에서 실행됩니다.

### 2. 대시보드 접속

브라우저에서 `http://127.0.0.1:9000/dashboard` 접속하여 실시간 탐지 결과 확인

### 3. ChatGPT/Gemini에서 파일 업로드

- ChatGPT: `https://chatgpt.com`
- Gemini: `https://gemini.google.com`

파일 업로드 시 자동으로 개인정보 탐지 및 대시보드에 표시

## 주요 라이브러리

```
fastapi              # 웹 서버
uvicorn              # ASGI 서버
transformers         # NER 모델
torch                # 딥러닝 프레임워크
easyocr              # OCR
pymupdf              # PDF 파싱
pillow               # 이미지 처리
mtcnn                # 얼굴 탐지
python-docx          # DOCX 파싱
olefile              # HWP 파싱
openpyxl             # XLSX 파싱
python-pptx          # PPTX 파싱
```

## 파일별 처리 방식

| 파일 형식 | 텍스트 추출 | 이미지 OCR | 얼굴 탐지 | 특이사항 |
|----------|-----------|----------|---------|----------|
| PDF      | ✅        | ✅       | ✅      | 병렬 처리 (8 workers) ⚡ |
| DOCX     | ✅        | ✅       | ✅      | 테이블 지원, 병렬 OCR |
| HWP      | ✅        | ✅       | ✅      | 띄어쓰기 자동 병합 🔥 |
| HWPX     | ✅        | ✅       | ✅      | 최적화 (30-40% 향상) |
| PPTX     | ✅        | ✅       | ✅      | 슬라이드별, 병렬 OCR |
| XLSX     | ✅        | ❌       | ❌      | 셀 단위 |
| TXT      | ✅        | ❌       | ❌      | UTF-8/CP949 |
| 이미지    | ❌        | ✅       | ✅      | 7가지 형식, 리사이즈 |

## 문제 해결

### HWP 파일에서 이름이 탐지 안 되는 경우

- HWP는 텍스트를 "이 무 송" 형태로 저장
- **자동 해결**: 한글 띄어쓰기 정규화 ("이 무 송" → "이무송")
- **정규식 이름 추출**: "성명이무송" 패턴 자동 인식
- **주소 자동 병합**: "##서울특별시", "##강남구" → "서울특별시 강남구"
- 서버 재시작 불필요 ✅

### HWPX 파일이 "지원하지 않는 파일 형식"으로 나오는 경우

1. Chrome 확장 프로그램 새로고침 (`chrome://extensions/`)
2. 브라우저 캐시 삭제 (Ctrl + Shift + Delete)
3. ChatGPT/Claude 페이지 새로고침

### Native Host 프로세스가 쌓이는 경우

- `host.py`에서 stdin 종료 시 프로세스 종료 로직 구현됨
- Chrome 종료 시 자동으로 정리됨

### Service Worker 비활성화 문제

- 자동 재연결 로직 구현
- ping 메시지로 Service Worker 깨우기
- 포트 연결 실패 시 100ms 대기 후 재시도

### 파일 취소 시 전송되는 문제

- 드롭 후 취소 버튼 클릭 시 대기 파일 자동 삭제
- 취소 버튼 감지: aria-label, className 기반
- 500ms 지연으로 취소 여부 확인

## 개발 정보

### NER 모델 필터링

- 2글자 이하 제외
- 숫자만 있는 경우 제외
- 한글 없이 특수문자만 있는 경우 제외
- 접두사 제거 ("저는", "나는", "제가" 등)
- 화이트리스트: 탐지 제외 목록
- 블랙리스트: 일반 명사 제외 ("컴퓨터", "키보드" 등)

### 생년월일 범위

- 1900~2006년생만 탐지
- 2007년 이후는 교육/근무 기간으로 간주하여 제외

### 주민등록번호 검증

- 생년월일 유효성 검사
- 체크섬 검증 (2020년 이후 출생자 제외)
- 성별 코드 검증 (1~8)

### 카드번호 검증

- Luhn 알고리즘 적용
- 16자리 숫자 (띄어쓰기/하이픈 포함 가능)
- 유효하지 않은 카드번호는 "invalid" 표시

### 파일 크기 제한

- Soft Limit: 20MB (경고 로그)
- Hard Limit: 100MB (거부)
- 최대 파일 개수: 10개
- Base64 인코딩 크기 기준

## 라이선스

이 프로젝트는 개인정보 보호를 위한 교육 및 연구 목적으로 제작되었습니다.

## 🚀 성능 최적화

### 병렬 처리 (ThreadPoolExecutor)
- **PDF 얼굴 탐지**: 최대 8 workers, CPU 코어 수 동적 조정
- **DOCX/HWP/PPTX OCR**: 최대 4 workers
- **이미지 1개**: 순차 처리 (오버헤드 방지)
- **효과**: 처리 속도 2-4배 향상 ⚡

### 이미지 처리 최적화
- **얼굴 탐지용 리사이즈**: 400px (속도 2-4배 향상)
- **PDF 중복 이미지 제거**: xref 기반
- **작은 이미지 스킵**: 5KB 이하 (로고/아이콘)
- **효과**: 메모리 사용량 50% 감소 💾

### 정규식 패턴 캐싱
- **모듈 레벨 컴파일**: `COMPILED_PATTERNS`, `COMPILED_NORMALIZED_PATTERNS`
- **효과**: 정규식 탐지 속도 10-20% 향상 🎯

### HWPX 파싱 최적화
- **불필요한 XML 제외**: settings, styles, header, footer
- **Contents/ 우선 처리**: 텍스트 콘텐츠만
- **효과**: HWPX 처리 속도 30-40% 향상 📄

### 디버그 로그 최적화
- **환경 변수 제어**: `PII_DEBUG=false` (기본값)
- **중요 로그만 유지**: INFO, ERROR
- **효과**: 로그 오버헤드 제거, 가독성 향상 📝

### 메모리 관리
- **메모리 누수 방지**: deque, maxlen=1000
- **텍스트 정규화 캐싱**: 반복 처리 방지
- **효과**: 장시간 실행 안정성 향상 🛡️

**전체 성능 개선: 처리 속도 2-3배 향상, 메모리 50% 절감**

## 보안 기능

- CORS 화이트리스트 (Extension ID 기반)
- HMAC 인증 (선택적, 환경변수 `PII_REQUIRE_AUTH=true`)
- 타임스탬프 검증 (5분 이내)
- 암호화된 문서 감지 및 거부

## 주의사항

⚠️ 이 시스템은 개인정보 탐지를 위한 보조 도구이며, 100% 정확도를 보장하지 않습니다.
⚠️ 중요한 개인정보는 반드시 수동으로 확인하시기 바랍니다.
⚠️ NER 모델은 문맥에 따라 오탐지/미탐지가 발생할 수 있습니다.
⚠️ 얼굴 탐지는 신뢰도 98% 이상만 표시하지만, 완벽하지 않습니다.
