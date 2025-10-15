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
  - `PS/PER`: 사람 이름 (한글 포함 시만 탐지, 숫자/특수문자만 있는 경우 필터링)
  - `ORG`: 조직명
  - `LOC/LC`: 위치/주소
  - `MISC`: 기타 개체

#### 이미지 분석
- **얼굴 탐지**: MTCNN 모델 사용
- **OCR**: EasyOCR로 이미지 내 텍스트 추출
  - DOCX, PDF, HWP, PPTX 내부 이미지 지원
  - 단일 이미지 파일 지원

### 🌐 네트워크 정보 수집
- IP 주소
- 컴퓨터 호스트명 (`platform.node()`)
- 브라우저 정보
- OS 정보

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

서버가 `http://localhost:8000`에서 실행됩니다.

### 2. 대시보드 접속

브라우저에서 `http://localhost:8000` 접속하여 탐지 결과 확인

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

| 파일 형식 | 텍스트 추출 | 이미지 OCR | 얼굴 탐지 |
|----------|-----------|----------|---------|
| PDF      | ✅        | ✅       | ✅      |
| DOCX     | ✅        | ✅       | ✅      |
| HWP      | ✅        | ✅       | ✅      |
| PPTX     | ✅        | ✅       | ✅      |
| XLSX     | ✅        | ❌       | ❌      |
| TXT      | ✅        | ❌       | ❌      |
| 이미지    | ❌        | ✅       | ✅      |

## 문제 해결

### 호스트명이 "unknown"으로 표시되는 경우

1. `host.py` 수정 후 재컴파일 필요:
```bash
cd Py_server/native_host
pyinstaller --onefile --noconsole host.py
```

2. `com.example.pii_host.json`에서 `host.exe` 경로 확인

### Native Host 프로세스가 쌓이는 경우

- `host.py`에서 stdin 종료 시 프로세스 종료 로직 구현됨
- Chrome 종료 시 자동으로 정리됨

### Service Worker 비활성화 문제

- `content.js`에서 자동 재연결 로직 구현됨
- ping 메시지로 Service Worker 깨우기

### 파일 취소 시 전송되는 문제

- 드롭 후 취소 버튼 클릭 시 대기 파일 자동 삭제
- `mousedown` 이벤트에서 취소 버튼 감지

## 개발 정보

### NER 모델 필터링

- 숫자만 있는 경우 제외 (예: "111", "55")
- 한글 없이 특수문자만 있는 경우 제외 (예: "##55")
- 한글 + 특수문자는 허용 (예: "##박명수")

### 생년월일 범위

- 1900~2006년생만 탐지
- 2007년 이후는 교육/근무 기간으로 간주하여 제외

### 파일 크기 제한

- 최대 파일 크기: 100MB
- 최대 파일 개수: 10개

## 라이선스

이 프로젝트는 개인정보 보호를 위한 교육 및 연구 목적으로 제작되었습니다.

## 주의사항

⚠️ 이 시스템은 개인정보 탐지를 위한 보조 도구이며, 100% 정확도를 보장하지 않습니다.
⚠️ 중요한 개인정보는 반드시 수동으로 확인하시기 바랍니다.
