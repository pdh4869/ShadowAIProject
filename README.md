# README — PII 탐지 에이전트 (Chrome 확장 + 로컬 FastAPI 서버)

이 프로젝트는 **브라우저에서 입력/전송하려는 텍스트와 업로드한 파일**을 감지해, **개인정보(전화/이메일/주민번호/카드/계좌/IP/인명 NER/얼굴 이미지)**를 로컬에서 탐지하고, **대시보드**로 실시간 표시하는 도구입니다.  
구성은 다음 3가지로 이뤄집니다.

1) **Chrome 확장**: 전송 이벤트/파일 업로드를 가로채어 백그라운드로 넘김.  
2) **Native Messaging Host**: 로컬 IP 등 네트워크 정보를 안전하게 조회.  
3) **FastAPI 로컬 서버**: 텍스트/파일 분석, OCR/NER/얼굴탐지, 대시보드 제공.

---

## 1. 폴더/파일 개요

- `manifest.json` — 확장 설정(권한/스크립트/네이티브 권한).  
- `content.js` — 페이지 내 전송/업로드 감지 + 파일 수집/직렬화 + 포트 통신.  
- `background.js` — 허용 URL 필터링, 네이티브 호스트 호출(IP), 로컬 서버로 전송.  
- `com.example.pii_host.json` — **네이티브 호스트 매니페스트(설치 경로/허용 확장 ID)**.  
- `host.py` — 네이티브 호스트(표준 입력/출력으로 메시지 교환, IP/네트워크 조회).  
- `LocalServer.py` — FastAPI 서버/대시보드/REST API.  
- `Logic.py` — 파일 파싱, 정규식 탐지, NER, OCR, 얼굴탐지(MTCNN).

---

## 2. 사전 준비 (Python & 패키지)

```bash
pip install fastapi uvicorn[standard] pillow numpy opencv-python pymupdf python-docx             pycryptodome requests easyocr mtcnn transformers torch torchvision sentencepiece
```

---

## 3. 로컬 서버 실행

```bash
python LocalServer.py
```

- 대시보드: **http://127.0.0.1:9000/dashboard**  
- 주요 API: `/api/event`, `/api/file_collect`, `/api/combined`, `/api/detections`

---

## 4. Chrome 확장 설치

1) **개발자 모드** → `chrome://extensions`  
2) **압축해제된 확장 프로그램 로드** → `manifest.json` 폴더 선택  
3) 설치 후 확장 **ID** 확인

---

## 5. Native Messaging Host 설정

### 매니페스트 수정
`com.example.pii_host.json`에서 `"path"`를 host.exe 절대경로로 수정,  
`"allowed_origins"`에 확장 ID 추가.

### 빌드 예시
```bash
pyinstaller --onefile host.py --name host
```

---

## 6. 동작 흐름

1) **content.js** — 텍스트/파일 감지 → COMBINED_EVENT 전송  
2) **background.js** — IP 조회 → FastAPI로 POST 전송  
3) **LocalServer.py** — 텍스트+파일 분석 → 대시보드 표시

---

## 7. 탐지 항목

- 전화번호, 이메일, 주민번호, 여권, 계좌, 카드, IP, 인명, 조직, 위치  
- 이미지 내 OCR + 얼굴탐지(MTCNN)  
- PDF/DOCX 내 이미지·텍스트 추출

---

## 8. 테스트

1) 서버 실행  
2) 확장 설치 후 예시 텍스트 입력  
3) 파일 업로드 시 탐지 로그 확인  
4) 대시보드에서 결과 확인

---

## 9. 보안

- 전송 대상: **127.0.0.1:9000 (로컬 전용)**  
- `send_to_backend`는 기본 비활성화 (원격 전송 없음)

---

## 10. 커스터마이징

- 허용 URL: `background.js`의 `isAllowedLLMUrl`  
- 지원 파일형식: `content.js`의 `allowed` 배열  
- 정규식/NER: `Logic.py` 함수 내부

---

## 11. 트러블슈팅

- 대시보드 미표시 → 허용 URL 확인, 서버 로그 확인  
- IP가 unknown → `com.example.pii_host.json` 설정 확인  
- 파일 미탐지 → OCR, MTCNN 라이브러리 설치 확인

---

## 12. 라이선스

- 연구/로컬용 예시 코드입니다. 상용 사용 시 개인정보보호법을 준수하세요.
