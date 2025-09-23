# LLM Upload Collector

브라우저에서 LLM 서비스(ChatGPT, Gemini 등)에 업로드되는 **파일과 프롬프트**를 가로채어,  
로컬 백엔드 서버에 저장하는 Chrome 확장 프로그램 + Python 서버입니다.  
개인정보 탐지/연구용 **수집 전용 PoC** 프로젝트입니다.

---

## 📂 프로젝트 구조

```
llm-upload-collector/
├── backend/                # Python 백엔드 서버
│   ├── server.py           # 수집된 데이터 저장 서버
│   ├── requirements.txt    # 필요 라이브러리
│   ├── collected/          # 업로드된 파일/프롬프트 저장 위치
│   └── venv/               # (개인 가상환경, Git에는 제외)
└── extension/              # Chrome 확장 프로그램
    ├── manifest.json       # 확장앱 메타정보
    ├── content.js          # DOM에서 업로드/입력 가로채기
    ├── background.js       # 확장앱 백그라운드 처리
    └── service_worker.js   # 확장앱 서비스워커
```

---

## 🚀 실행 방법

### 1) 백엔드 서버 실행
```bash
cd backend
python -m venv venv (가상환경 생성)
venv\Scripts\activate(윈도우)
pip install -r requirements.txt (최초 1회 설치)
uvicorn server:app --host 127.0.0.1 --port 18080(backend 폴더에서)
```
- 서버 기본 포트: `http://127.0.0.1:18080`
- 수집된 결과는 `backend/collected/` 폴더에 저장됨

### 2) 크롬 확장 프로그램 로드
1. Chrome 주소창에 `chrome://extensions/` 입력
2. **개발자 모드** 활성화
3. "압축 해제된 확장 프로그램 로드" 클릭 후 `extension/` 폴더 선택
4. 확장 프로그램 활성화 후, LLM 서비스(예: ChatGPT, Gemini) 접속

---

## 🛡️ 주의사항
- 이 프로젝트는 **연구 및 PoC용**입니다.  
- 실제 서비스 환경에서 사용자의 동의 없는 개인정보 수집은 불법입니다.  
- Git에는 `venv/` 와 `collected/` 폴더 내용을 업로드하지 않도록 `.gitignore`에 추가하세요.

---

## ✅ TODO
- [ ] 수집 데이터 마스킹/분석 기능 추가
- [ ] 대시보드 시각화
- [ ] Docker 기반 배포 스크립트 작성
