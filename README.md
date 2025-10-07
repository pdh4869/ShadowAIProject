# 🛡️ Shadow AI: LLM을 위한 민감 정보 유출 방지 시스템

**Shadow AI**는 사용자가 ChatGPT, Gemini 등 외부 LLM(거대 언어 모델) 서비스에 **민감 정보를 전송하는 것을 실시간으로 탐지하고 차단**하기 위해 설계된 **클라이언트 기반 데이터 유출 방지(DLP)** 솔루션입니다.  

로컬 서버에서 사용자의 프롬프트(텍스트, 파일)를 분석하여 **개인정보(PII)** 및 기타 민감 데이터의 외부 유출을 사전에 방지합니다.  
모든 데이터는 사용자의 **로컬 환경에서 100% 처리**됩니다.

---

## 🏛️ 시스템 아키텍처

```
+------------------+      (1) User Input      +---------------------+      (2) Collect & Send      +-----------------+
|   사용자 브라우저   | ---------------------> |  Browser Extension  | --------------------------> |   Local Server  |
| (ChatGPT, Gemini) |      (Prompt, Files)   |   (content.js,      |      (HTTP Request)       | (Flask, Python) |
+------------------+                        |   background.js)    |                           +--------+--------+
                                            +----------+----------+                                     |
                                                       | (3) Get Network Info                       (4) PII Analysis
                                            +----------v----------+                                     |
                                            |     Native Host     | <-----------------------------------+
                                            |      (host.exe)     |      (Regex, NER, OCR, Face Detection)
                                            +---------------------+
```

### 구성 요소 요약
1. **사용자 입력**
   - 사용자가 LLM 서비스(ChatGPT, Gemini 등)에 텍스트 또는 파일을 입력합니다.
2. **Browser Extension**
   - 입력된 데이터를 가로채어 Local Server로 전송합니다.
3. **Native Host**
   - PC 정보(IP, 호스트명 등)를 수집하여 컨텍스트 정보를 함께 전달합니다.
4. **Local Server**
   - 정규식, NER, OCR, 얼굴인식 등을 통해 민감 정보를 탐지하고 로그로 출력합니다.

---

## ✨ 주요 기능

| 기능 | 설명 |
|------|------|
| **실시간 프롬프트 모니터링** | ChatGPT, Gemini, Claude 등 주요 LLM 서비스의 입력을 실시간으로 감지 |
| **다양한 파일 형식 지원** | txt, docx, pdf, 이미지(png, jpg 등) 내부 텍스트까지 분석 |
| **정규식(Regex)** | 주민등록번호, 전화번호, 카드번호 등 정형화된 개인정보 탐지 |
| **개체명 인식(NER)** | transformers 모델로 사람 이름, 기관명, 위치 등 비정형 개인정보 탐지 |
| **OCR 분석** | easyocr로 이미지 속 텍스트 추출 후 분석 |
| **안면 인식** | mtcnn으로 이미지 속 얼굴 탐지 |
| **100% 로컬 처리** | 모든 분석은 로컬 서버에서만 수행되어 외부 유출 방지 |
| **컨텍스트 정보 수집** | Native Host를 통해 유출 시도 PC 식별 가능 |

---

## 🚀 설치 및 실행 방법

### 🧩 사전 요구사항
- Python 3.9 이상
- Google Chrome
- pip (Python 패키지 관리자)

---

### 1️⃣ Local Server 설정

```bash
# 1. 서버 디렉토리로 이동
cd ShadowAIProject/server

# 2. 가상 환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate.bat  # Windows

# 3. 라이브러리 설치
pip install Flask requests numpy PyMuPDF easyocr python-docx Pillow transformers torch pycryptodome mtcnn opencv-python

# 4. 서버 실행
python LocalServer.py
```
서버가 실행되면 `http://127.0.0.1:9123` 에서 요청을 대기합니다.

---

### 2️⃣ Native Host 설정

```bash
# 1. Native Host 디렉토리로 이동
cd ShadowAIProject/native_host

# 2. PyInstaller 설치
pip install pyinstaller

# 3. host.py를 host.exe로 빌드
pyinstaller host.spec

# 4. 레지스트리 등록 (Windows 전용)
# register_host.reg 파일 실행
```
> 경로가 변경되었다면 `com.example.pii_host.json` 및 `register_host.reg` 내부의 경로를 수정해야 합니다.

---

### 3️⃣ Browser Extension 설정

1. Chrome 주소창에 `chrome://extensions` 입력  
2. 우측 상단 **개발자 모드** 활성화  
3. **압축 해제된 확장 프로그램 로드** 클릭  
4. `ShadowAIProject/extension` 폴더 선택  
5. `'PII Agent'` 확장 프로그램 추가 확인  

---

## 🛠️ 사용 방법

1. 서버와 Native Host가 실행 중이어야 합니다.  
2. Chrome에서 ChatGPT, Gemini 등 LLM 서비스에 접속합니다.  
3. 예시 프롬프트 입력:
   ```
   제 주민등록번호는 900101-1234567 입니다.
   ```
4. LocalServer 터미널에서 탐지 로그를 확인합니다.

---

## 📜 License
MIT License

---

## 👤 Author
**Shadow AI Project Team**
