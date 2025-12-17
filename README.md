# ShadowAI PII 탐지 시스템

**ShadowAI PII Detector**는 사용자가 생성형 AI (LLM) 챗봇 서비스와 상호작용할 때 입력하는 텍스트 및 파일에서 **개인식별정보(PII)** 를 실시간으로 탐지하고, 이를 중앙 대시보드로 전송하여 관리하는 통합 보안 솔루션입니다.

---

## 🚀 주요 기능

### 실시간 PII 탐지
- **텍스트 탐지**: ChatGPT, Gemini 등 주요 LLM 서비스에서 사용자 프롬프트 입력을 실시간 모니터링
- **파일 탐지**: PDF, DOCX, HWP, HWPX, XLSX, XLS, PPTX, PPT, 이미지 파일 등 다양한 형식 지원
- **이미지 OCR**: 문서 내 이미지에서 텍스트 추출 및 PII 탐지
- **얼굴 인식**: MTCNN 기반 이미지 내 얼굴 탐지 (신뢰도 98% 이상)

### 고급 탐지 기술
- **정규식 기반 탐지**: 전화번호, 이메일, 주민등록번호, 카드번호, 계좌번호, 운전면허번호, 여권번호, 외국인등록번호, IP 주소
- **NER(Named Entity Recognition)**: Hugging Face 기반 AI 모델로 인명, 조직명, 지명 탐지
- **준식별자 탐지**: 생년월일, 직위, 주소 등 조합 시 개인 특정 가능한 정보
- **조합 위험도 분석**: 여러 준식별자 조합으로 개인 식별 가능성 평가
- **검증 로직**: Luhn 알고리즘(카드번호), 주민등록번호 체크섬 검증

### 통합 대시보드
- **실시간 모니터링**: 탐지 내역을 실시간으로 시각화
- **통계 분석**: 탐지 추이, 사용자별/유형별 통계, 고위험 PII 비율
- **관리자 기능**: 계정 관리, 권한 설정, 활동 로그
- **상세 필터링**: 날짜, PII 유형, 파일 형식, 상태별 검색

---

## 🛠️ 시스템 아키텍처

본 시스템은 네 가지 주요 구성 요소로 작동합니다.

### 1. Chrome 확장 프로그램 (`/extension`)
- **content.js**: LLM 웹사이트에 주입되어 사용자 입력(텍스트/파일) 감지
- **background.js**: Service Worker로 네이티브 호스트와 통신 채널 관리
- **manifest.json**: 탐지 대상 LLM 도메인 정의 (ChatGPT, Gemini)

**지원 입력 방식**:
- Enter 키 전송
- 전송 버튼 클릭
- 파일 업로드 (input, 드래그앤드롭, 붙여넣기)

### 2. 네이티브 호스트 (`/native_host`)
- **host.py**: Chrome 확장 프로그램과 로컬 서버 간 브리지 역할
- **Native Messaging API**: Chrome과 Python 프로세스 간 통신
- **네트워크 정보 수집**: IP, 호스트명, 게이트웨이, DNS 정보 수집
- **host.exe**: PyInstaller로 빌드된 실행 파일

### 3. 로컬 PII 탐지 서버 (`/server`)
- **LocalServer_Final.py**: FastAPI 기반 서버 (포트 9000)
  - `/api/event`: 텍스트 이벤트 처리
  - `/api/file_collect`: 파일 업로드 처리
  - `/api/combined`: 텍스트+파일 통합 처리
  - `/dashboard`: 로컬 모니터링 대시보드
  - `/api/detections`: 탐지 내역 조회 API

- **Logic_Final.py**: PII 탐지 로직 구현
  - NER 모델 (klue-roberta-base-ner)
  - 정규식 패턴 매칭
  - 파일 파싱 (PDF, DOCX, HWP, XLSX 등)
  - OCR (EasyOCR)
  - 얼굴 탐지 (MTCNN)
  - 조합 위험도 분석

### 4. 중앙 대시보드 (`/backend.py`, `/templates`)
- **backend.py**: Flask 기반 중앙 관리 서버 (포트 5000)
  - MySQL 데이터베이스 연동
  - 관리자 인증 및 권한 관리
  - PII 로그 수신 및 저장 (`/api/log-pii`)
  - 통계 및 시각화 페이지

- **데이터베이스 스키마**:
  - `pii_log`: PII 탐지 로그
  - `pii_type`: PII 유형 관리
  - `file_type`: 파일/소스 유형
  - `llm_type`: LLM 서비스 유형
  - `dashboard_admin`: 관리자 계정
  - `dashboard_log`: 관리자 활동 로그

---

## 📦 설치 방법

### ✅ 권장: install.ps1 자동 설치 스크립트

1. 프로젝트 루트 폴더에서 PowerShell을 엽니다.
2. 아래 명령어를 실행합니다:

```powershell
.\install.ps1
```

3. 스크립트 안내에 따라 입력:
   - **Hugging Face 토큰**: https://huggingface.co/settings/tokens 에서 생성
   - **대시보드 IP**: 중앙 서버 IP (로컬 테스트 시 127.0.0.1)
   - **확장 프로그램 ID**: Chrome에서 확장 프로그램 로드 후 생성된 32자리 ID

**자동 설치 스크립트가 수행하는 작업**:
- Python 패키지 설치 (requirements.txt)
- 환경 변수 설정 (.env 파일 생성)
- 네이티브 호스트 빌드 (PyInstaller)
- Windows 레지스트리 등록
- 확장 프로그램 ID 설정

### 📋 수동 설치

상세한 수동 설치 가이드는 `ShadowAI_설치가이드.md` 파일을 참조하세요.

---

## ▶️ 시작하기

### 1. 중앙 대시보드 서버 실행 (선택사항)

```bash
# MySQL 데이터베이스 설정 (backend.py 내 설정 확인)
# 데이터베이스: shadowai
# 사용자: root / 비밀번호: mysql

# 최초 관리자 계정 생성
python create_admin.py

# 대시보드 서버 실행
python backend.py
```

대시보드 접속: http://localhost:5000

### 2. 로컬 PII 탐지 서버 실행

```bash
cd server
python LocalServer_Final.py
```

서버 실행 확인: http://127.0.0.1:9000

로컬 대시보드: http://127.0.0.1:9000/dashboard

### 3. Chrome 확장 프로그램 확인

1. Chrome에서 `chrome://extensions/` 접속
2. **개발자 모드** 활성화
3. **ShadowAI PII Detector** 확장 프로그램이 활성화(ON)되어 있는지 확인

### 4. PII 탐지 테스트

1. https://chatgpt.com/ 또는 https://gemini.google.com/ 접속
2. 채팅창에 테스트 데이터 입력:
   - 전화번호: 010-1234-5678
   - 이메일: test@example.com
   - 주민등록번호: 900101-1234567
3. 로컬 서버 터미널 및 대시보드에서 탐지 로그 확인

---

## ⚙️ 설정 변경

### 탐지 대상 LLM 도메인 변경

`extension/manifest.json` 파일의 `content_scripts` 섹션 수정:

```json
"content_scripts": [{
  "matches": [
    "https://chatgpt.com/*",
    "https://gemini.google.com/*",
    "https://claude.ai/*",
    "https://new-llm-service.com/*"
  ],
  "js": ["content.js"],
  "run_at": "document_start"
}]
```

변경 후 `chrome://extensions/`에서 확장 프로그램 새로고침 필요.

### 환경 변수 설정 (.env)

```env
# Hugging Face 토큰
HF_TOKEN=your_huggingface_token

# 대시보드 설정
DASHBOARD_URL=http://127.0.0.1:5000/api/log-pii
DASHBOARD_REQUIRE_AUTH=false
DASHBOARD_API_SECRET=

# 로컬 서버 인증 (선택)
PII_REQUIRE_AUTH=false
PII_API_SECRET=

# 확장 프로그램 ID
ALLOWED_EXTENSION_ID=your_32_char_extension_id
```

---

## 📁 프로젝트 구조

```
ShadowAIProject-main/
├── extension/                    # Chrome 확장 프로그램
│   ├── manifest.json            # 확장 프로그램 설정
│   ├── content.js               # 콘텐츠 스크립트 (입력 감지)
│   └── background.js            # 백그라운드 서비스 워커
│
├── native_host/                  # 네이티브 호스트
│   ├── host.py                  # 네이티브 메시징 브리지
│   ├── com.example.pii_host.json # 호스트 설정
│   ├── register_host.reg        # 레지스트리 등록 파일
│   └── build/host/host.exe      # 빌드된 실행 파일
│
├── server/                       # 로컬 PII 탐지 서버
│   ├── LocalServer_Final.py     # FastAPI 서버
│   └── Logic_Final.py           # PII 탐지 로직
│
├── templates/                    # 대시보드 HTML 템플릿
│   ├── main.html                # 메인 대시보드
│   ├── detection_details.html  # 탐지 현황
│   ├── user_type.html           # 사용자별 현황
│   ├── personal_information_type.html # PII 유형별 현황
│   ├── account_management.html  # 계정 관리
│   └── assets/                  # CSS, JS, 폰트
│
├── instance/                     # SQLite 데이터베이스 (로컬)
│   └── pii_logs.db
│
├── backend.py                    # Flask 중앙 대시보드 서버
├── create_admin.py              # 관리자 계정 생성 스크립트
├── install.ps1                  # 자동 설치 스크립트
├── requirements.txt             # Python 의존성
├── README.md                    # 프로젝트 문서
└── ShadowAI_설치가이드.md       # 상세 설치 가이드
```

---

## 🔍 탐지 가능한 PII 유형

### 직접 식별자
- **전화번호**: 010-XXXX-XXXX, 02-XXX-XXXX 등
- **이메일**: user@domain.com
- **주민등록번호**: XXXXXX-XXXXXXX (체크섬 검증)
- **외국인등록번호**: XXXXXX-5/6/7/8XXXXXX
- **운전면허번호**: XX-XX-XXXXXX-XX
- **여권번호**: M12345678
- **카드번호**: XXXX-XXXX-XXXX-XXXX (Luhn 알고리즘 검증)
- **계좌번호**: XXXXXX-XX-XXXXXX
- **IP 주소**: XXX.XXX.XXX.XXX

### NER 기반 탐지
- **인명(PS/PER)**: 한국인 이름 (성씨 기반 필터링)
- **조직명(ORG)**: 회사명, 기관명
- **지명(LOC)**: 주소, 지역명

### 준식별자
- **생년월일**: YYYY년 MM월 DD일
- **직위**: 사원, 대리, 과장, 부장 등
- **주소**: 시/도/구/동/로 포함 전체 주소

### 이미지 분석
- **얼굴 이미지**: MTCNN 기반 얼굴 탐지 (신뢰도 98% 이상)
- **OCR 텍스트**: 이미지 내 텍스트 추출 후 PII 탐지

### 조합 위험도
- 준식별자 2종 이상 조합 시 개인 특정 가능성 경고

---

## 📊 지원 파일 형식

### 문서
- **PDF**: 텍스트 추출 + 이미지 OCR
- **DOCX**: 텍스트 + 표 + 이미지 OCR
- **DOC**: win32com 변환 후 처리 (Windows 전용)
- **HWP**: olefile 기반 파싱 + 이미지 OCR
- **HWPX**: ZIP 기반 XML 파싱 + 이미지 OCR
- **TXT**: UTF-8, CP949 인코딩 지원

### 스프레드시트
- **XLSX**: openpyxl 기반 파싱
- **XLS**: xlrd 또는 win32com 변환

### 프레젠테이션
- **PPTX**: python-pptx + 이미지 OCR
- **PPT**: win32com 변환 후 처리 (Windows 전용)

### 이미지
- **PNG, JPG, JPEG, BMP, WEBP, TIFF**: EasyOCR 텍스트 추출
- **GIF**: 다중 프레임 OCR (3프레임마다 샘플링)

---

## 🔐 보안 기능

### 인증 및 권한
- **HMAC 기반 인증**: 타임스탬프 + 시크릿 키 검증
- **확장 프로그램 화이트리스트**: 허용된 Extension ID만 통신
- **관리자 권한 관리**: super/admin 등급 구분
- **비밀번호 해싱**: werkzeug.security 사용

### 데이터 보호
- **파일명 마스킹**: PII 포함 파일명 자동 마스킹
- **로컬 처리**: 민감 데이터는 로컬 서버에서만 처리
- **선택적 전송**: 주소(LC) 등 저위험 정보는 대시보드 전송 제외

### 로깅
- **활동 로그**: 관리자 로그인, 계정 생성/삭제 기록
- **탐지 로그**: 타임스탬프, IP, 호스트명, 브라우저 정보 포함

---

## 🧪 개발 및 디버깅

### 디버그 모드 활성화

```bash
# 환경 변수 설정
set PII_DEBUG=true

# 서버 실행
python server/LocalServer_Final.py
```

### 로그 파일
- **server_debug.log**: 로컬 서버 상세 로그
- **native_host/host_log.txt**: 네이티브 호스트 통신 로그

### Chrome 개발자 도구
- **확장 프로그램 콘솔**: `chrome://extensions/` → 확장 프로그램 상세 → 백그라운드 페이지 검사
- **콘텐츠 스크립트 콘솔**: F12 → Console 탭

---

## 📈 성능 최적화

### 병렬 처리
- **PDF 페이지**: ThreadPoolExecutor로 다중 페이지 동시 처리
- **이미지 OCR**: 여러 이미지 병렬 OCR 실행
- **얼굴 탐지**: 다중 이미지 동시 분석

### 파일 크기 제한
- **소프트 제한**: 20MB (경고)
- **하드 제한**: 100MB (거부)

### 중복 제거
- **PDF 이미지**: xref 기반 중복 이미지 스킵
- **탐지 결과**: 동일 PII 중복 제거

---

## 🐛 문제 해결

### 확장 프로그램이 작동하지 않음
1. `chrome://extensions/`에서 확장 프로그램 활성화 확인
2. 개발자 모드 활성화 확인
3. 확장 프로그램 새로고침 (⟳ 버튼)
4. Chrome 재시작

### 네이티브 호스트 연결 실패
1. `native_host/host.exe` 파일 존재 확인
2. 레지스트리 등록 확인: `regedit` → `HKEY_CURRENT_USER\Software\Google\Chrome\NativeMessagingHosts\com.example.pii_host`
3. `com.example.pii_host.json`의 `path` 경로 확인
4. `allowed_origins`에 올바른 확장 프로그램 ID 설정 확인

### 로컬 서버 연결 실패
1. 서버 실행 확인: http://127.0.0.1:9000
2. 방화벽 설정 확인
3. 포트 9000 사용 중인 프로세스 확인

### 대시보드 전송 실패
1. `DASHBOARD_URL` 환경 변수 확인
2. 대시보드 서버 실행 확인
3. MySQL 데이터베이스 연결 확인

---

## 📚 의존성

### Python 패키지
```
fastapi
uvicorn
transformers
torch
easyocr
PyMuPDF
Pillow
mtcnn
python-docx
olefile
openpyxl
python-pptx
xlrd
numpy
pywin32 (Windows 전용)
requests
flask
flask-sqlalchemy
flask-login
flask-cors
werkzeug
pymysql
```

### 외부 서비스
- **Hugging Face**: NER 모델 (klue-roberta-base-ner)
- **MySQL**: 중앙 데이터베이스 (선택사항)

---

## 🤝 기여

이 프로젝트는 K-Shield Jr. 프로그램의 일환으로 개발되었습니다.

---

## 📄 라이선스

이 프로젝트는 교육 및 연구 목적으로 제공됩니다.

---

## 📞 지원

문제가 발생하거나 질문이 있으시면 프로젝트 관리자에게 문의하세요.

---

## 🔄 업데이트 내역

### v0.2.2 (현재)
- Chrome 확장 프로그램 안정화
- 파일 업로드 중복 전송 방지
- GIF 파일 OCR 지원 추가
- 조합 위험도 분석 강화
- 이름 탐지 정확도 향상
- 구버전 파일 지원 확대 (.doc, .xls, .ppt)

---

**⚠️ 주의사항**
- 이 시스템은 개인정보 보호를 위한 모니터링 도구입니다.
- 탐지된 PII는 로컬 서버에서 처리되며, 중앙 서버로는 통계 정보만 전송됩니다.
- 실제 운영 환경에서는 적절한 보안 설정과 권한 관리가 필요합니다.
