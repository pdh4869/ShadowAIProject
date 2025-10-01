# LLM/PII 통합 후킹 에이전트 (Integrated Hooking Agent)

이 프로젝트는 **LLM 서비스(ChatGPT, Gemini 등)에 전송되는 데이터**를 두 가지 방식으로 통합 수집하는 연구 및 PoC(Proof of Concept)용 에이전트입니다.

---

## 📦 데이터 수집 방식

- **데이터베이스 저장**  
  사용자 프롬프트(텍스트), 파일 이름 목록, 그리고 전송 시점의 상세 시스템/네트워크 정보(PII 메타데이터)를 SQLite DB(`pii_sidecar.db`)에 저장합니다.

- **디스크 저장**  
  사용자가 업로드한 파일의 실제 내용을 Base64 디코딩 후 로컬 디스크(`collected_files/`)에 저장합니다.

---

## ✨ 최종 통합 기능 목록

| 기능 카테고리       | 상세 수집 내용                                  | 저장 위치                                |
|------------------|-------------------------------------------|---------------------------------------|
| 파일 내용 수집      | 업로드된 파일의 실제 바이너리 내용                   | 서버 폴더 내 `collected_files/`       |
| 프롬프트/메타데이터  | 사용자의 프롬프트(텍스트), 업로드된 파일 이름 목록         | SQLite DB (`pii_sidecar.db`)          |
| 네트워크/지리 정보   | 공인 IP, 국가 코드, 국가 이름, 사설 IP | SQLite DB (메타데이터와 함께)          |
| 시스템 정보        | User-Agent, OS 정보 (이름, 버전)                | SQLite DB (메타데이터와 함께)          |
| 대시보드          | 수집된 모든 메타데이터를 웹에서 시각화                | `http://127.0.0.1:8123/admin`         |

---

## 📂 프로젝트 구조

```
Integrated-Hooking-Agent/
├── native_host/            # Python Native Host (시스템/네트워크 정보 수집)
│   ├── host.py             # Native Host 메인 스크립트
│   └── com.example.pii_host.json # ⚠️ 확장 프로그램 ID 설정 파일
├── server/                 # Python FastAPI 백엔드 서버
│   ├── app.py              # 메인 서버 (CORS, IP/Geo 수집 로직 통합됨)
│   ├── pii_sidecar.db      # 수집된 메타데이터 저장 DB
│   └── collected_files/    # 📂 수집된 파일 내용 저장 위치
└── extension/              # Chrome 확장 프로그램
    ├── manifest.json       # 타겟 LLM 및 권한 설정
    ├── content.js          # 파일 내용 및 메타데이터 후킹 로직 통합됨
    └── background.js       # 데이터 분류 및 서버 전송 중계
```

---

## 🚀 실행 및 통합 가이드

이 에이전트는 **Native Host, FastAPI 서버, Chrome 확장 프로그램** 세 요소가 모두 실행되어야 완벽하게 작동합니다.

### 1. 백엔드 서버 실행 (FastAPI)

```bash
cd server
# (필요시 가상환경 활성화 및 'fastapi', 'uvicorn', 'pydantic', 'requests' 등 설치)

# 서버 실행
uvicorn app:app --host 127.0.0.1 --port 8123
```

- 서버 포트: [http://127.0.0.1:8123](http://127.0.0.1:8123)  
- 파일 내용은 `server/collected_files/` 폴더에 저장됩니다.

---

### 2. 크롬 확장 프로그램 로드 및 ID 확인

1. Chrome 주소창에 `chrome://extensions/` 입력 후 **개발자 모드**를 활성화합니다.  
2. **압축 해제된 확장 프로그램 로드**를 클릭 후 `extension/` 폴더를 선택합니다.  
3. 확장 프로그램을 로드한 후, 해당 확장 프로그램의 상세 정보 페이지에 표시된 확장 프로그램 ID(32자리 문자열)를 복사합니다.

---

### 3. Native Host 설정 및 실행 ⚠️ 필수

Native Host가 확장 프로그램과 통신하려면, 반드시 해당 확장 프로그램 ID를 허용해야 합니다.

- `native_host/com.example.pii_host.json` 파일을 엽니다.  
- `"allowed_origins"` 필드의 값을 2단계에서 복사한 확장 프로그램 ID로 교체합니다.

#### [수정 예시]

```json
{
  "name": "com.example.pii_host",
  // ... (중략) ...
  "allowed_origins": [
    "chrome-extension://YOUR_EXTENSION_ID_HERE/" 
    //  ^----- 이 부분을 실제 ID로 교체해야 합니다.
  ]
}
```

이후 Native Host를 실행합니다.

```bash
cd native_host
# (Windows 환경의 경우)
python host.py
```

---

## 🛡️ 중요 주의사항

이 프로젝트는 연구 및 PoC(Proof of Concept) 목적으로만 제작되었습니다.  

실제 서비스 환경에서 사용자의 동의 없이 개인 정보 또는 민감한 파일을 수집하는 행위는 관련 법규(개인정보보호법 등)에 위반될 수 있으며, 불법입니다.  
**사용에 따른 모든 책임은 사용자에게 있음을 명심하십시오.**
