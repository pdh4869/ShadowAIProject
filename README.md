# ShadowAI PII 탐지 시스템

**ShadowAI PII Detector**는 사용자가 생성형 AI (LLM) 챗봇 서비스와 상호작용할 때 입력하는 텍스트에서 **개인식별정보(PII)** 를 실시간으로 탐지하고, 이를 중앙 대시보드로 전송하는 시스템입니다.

---

## 🚀 주요 기능

- **실시간 PII 탐지:** ChatGPT, Claude, Gemini 등 주요 LLM 서비스 웹사이트에서 사용자의 프롬프트 입력을 모니터링합니다.
- **로컬 AI 모델 구동:** 로컬 머신에서 FastAPI 서버를 구동하여, Hugging Face의 AI 모델을 사용해 PII 탐지 로직을 수행합니다.
- **중앙 로깅:** 탐지된 PII 내역을 지정된 대시보드 서버로 전송하여 관리자가 모니터링할 수 있도록 합니다.
- **간편한 설치:** PowerShell 스크립트(`install.ps1`)를 통해 복잡한 설치 과정을 자동화합니다.

---

## 🛠️ 시스템 아키텍처

본 시스템은 세 가지 주요 구성 요소로 작동합니다.

### **1. Chrome 확장 프로그램 (`/extension`)**

- 지정된 LLM 웹사이트(`manifest.json`에 정의됨)에 `content.js`를 주입하여 사용자 입력을 감지합니다.  
- `background.js`는 감지된 텍스트를 '네이티브 호스트'로 전송하는 통신 채널 역할을 합니다.

### **2. 네이티브 호스트 (`/native_host`)**

- Chrome 확장 프로그램과 로컬 Python 서버 간의 **브리지(Bridge)** 역할을 합니다.  
- `host.py` 스크립트가 `host.exe`로 빌드되며, Chrome의 **Native Messaging API**를 통해 확장 프로그램으로부터 데이터를 수신하여 로컬 서버(포트 9000)로 전달합니다.

### **3. 로컬 서버 (`/server`)**

- `LocalServer_Final.py`는 uvicorn에서 실행되는 **FastAPI 서버**입니다.  
- 네이티브 호스트로부터 텍스트를 수신하면, `Logic_Final.py`의 **PII 탐지 로직**을 실행합니다.  
- PII가 탐지되면, 결과를 환경 변수(`DASHBOARD_URL`)에 지정된 **대시보드**로 전송합니다.

---

## 📦 설치 방법

### ✅ 권장: install.ps1 자동 설치 스크립트

1. 프로젝트 루트 폴더에서 PowerShell을 엽니다.  
2. 아래 명령어를 실행하고, 스크립트의 안내에 따라 Hugging Face 토큰, 대시보드 IP, Chrome 확장 프로그램 ID를 입력합니다.

```powershell
.\install.ps1
```

> 📘 **상세 가이드:** 자동 설치 및 수동 설치에 대한 전체 단계별 가이드는 `ShadowAI_설치가이드.md` 파일을 참조하세요.

---

## ▶️ 시작하기

### **1. 로컬 서버 실행**
```bash
cd server
py LocalServer_Final.py
```
서버가 `http://127.0.0.1:9000` 에서 실행됩니다.

### **2. Chrome 확장 프로그램 확인**
- Chrome 브라우저에서 `chrome://extensions/` 로 이동합니다.  
- **ShadowAI PII Detector**가 활성화(ON)되어 있는지 확인합니다.

### **3. PII 탐지 테스트**
1. `extension/manifest.json`에 등록된 사이트 (예: https://chat.openai.com/)로 이동합니다.  
2. 채팅창에 주민등록번호, 전화번호 등 PII 정보를 입력합니다.  
3. 로컬 서버 터미널 및 대시보드에서 로그가 출력되는지 확인합니다.

---

## ⚙️ 설정 변경

### **탐지 대상 LLM 도메인 변경**

PII 탐지를 적용할 웹사이트를 추가하거나 변경할 수 있습니다.

1. `extension/manifest.json` 파일을 엽니다.  
2. `"content_scripts"` 섹션의 `"matches"` 배열에 원하는 도메인 주소를 추가하거나 수정합니다.

```json
"matches": [
  "https://chat.openai.com/*",
  "https://claude.ai/*",
  "https://gemini.google.com/*",
  "https://new-llm-service.com/*"
]
```

파일 저장 후 `chrome://extensions/` 페이지에서 확장 프로그램의 새로고침 아이콘을 클릭하여 변경사항을 적용합니다.

---

## 📁 주요 설정 파일

| 파일명 | 설명 |
|--------|------|
| **.env** | (설치 시 자동 생성) Hugging Face 토큰, 대시보드 URL, 확장 프로그램 ID 등 핵심 환경 변수 관리 |
| **requirements.txt** | Python 의존성 패키지 목록 |
| **install.ps1** | 자동 설치 및 환경 구성 스크립트 |
| **manifest.json** | 확장 프로그램의 LLM 탐지 대상 사이트 목록 |

---

