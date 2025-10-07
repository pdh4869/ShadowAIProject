# 🛡️ Shadow AI: LLM을 위한 민감 정보 유출 방지 시스템

**Shadow AI**는 사용자가 ChatGPT, Gemini 등 외부 LLM(거대 언어 모델) 서비스에 **민감 정보를 전송하는 것을 실시간으로 탐지하고 차단**하기 위해 설계된 **클라이언트 기반 데이터 유출 방지(DLP)** 솔루션입니다.

사용자의 프롬프트(텍스트, 파일)를 로컬 서버에서 분석하여 개인정보, 개인 식별 정보(PII) 및 기타 민감 데이터가 외부로 유출되는 것을 사전에 방지합니다.

---

## 🏛️ 아키텍처

Shadow AI 시스템은 세 가지 주요 컴포넌트로 구성되어 있으며, 모든 데이터 처리는 사용자의 로컬 환경 내에서 이루어집니다.

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

### 구성 요소

- **Browser Extension**: 사용자가 LLM 서비스에 입력하는 프롬프트와 파일을 감지하여 로컬 서버로 전송합니다.  
- **Native Host**: 확장 프로그램의 요청에 따라 사용자의 PC 이름, IP 주소 등 컨텍스트 정보를 수집하여 제공합니다.  
- **Local Server**: 확장 프로그램으로부터 전달받은 데이터와 Native Host의 정보를 종합하여 민감 정보를 분석하고 탐지 로그를 기록합니다.  

---

## ✨ 주요 기능

- **실시간 프롬프트 모니터링**: ChatGPT, Gemini, Claude 등 주요 LLM 서비스의 프롬프트 입력을 실시간으로 감지합니다.  
- **다양한 파일 형식 지원**: 텍스트(txt), docx, pdf 및 이미지(png, jpg 등) 파일 내부의 텍스트까지 분석합니다.  
- **고급 텍스트 분석**  
  - **정규식(Regex)**: 주민등록번호, 전화번호, 카드번호 등 정형화된 개인정보 탐지  
  - **개체명 인식(NER)**: transformers 모델을 사용하여 사람 이름, 기관명, 위치 등 비정형 개인정보 탐지  
- **이미지 분석 기능**  
  - **광학 문자 인식(OCR)**: easyocr로 이미지 속 텍스트 추출  
  - **안면 인식**: mtcnn으로 이미지 속 인물(얼굴) 탐지  
- **100% 로컬 처리**: 모든 분석은 외부 전송 없이 로컬 서버에서만 수행되어 보안성을 극대화  
- **간편한 설치**: `install.bat` 스크립트를 통해 복잡한 설정 과정을 자동화  

---

## 🚀 설치 및 실행 방법

### ✅ 방법 1: 자동 설치 스크립트 사용 (권장)

`install.bat` 스크립트를 통해 대부분의 과정을 자동으로 설정합니다.

#### 사전 요구사항

- Windows 운영체제  
- Python 3.9 이상 (`Add Python to PATH` 옵션 체크 권장)  
- Google Chrome 브라우저  

#### 설치 절차

1. 프로젝트 폴더의 `install.bat` 파일을 **관리자 권한으로 실행**합니다.  
2. 스크립트가 실행되며 초기 설정을 진행합니다.  
3. 완료 후 다음을 수행합니다:  
   - Chrome 브라우저에서 `chrome://extensions`로 이동하여 `extension` 폴더를 로드합니다.  
   - 확장 프로그램의 **고유 ID**를 확인합니다.  
   - `install.bat` 파일을 편집기로 열고 맨 위의 `EXTENSION_ID` 값을 해당 ID로 수정합니다.  
   - 수정한 후 다시 **관리자 권한으로 실행**하여 최종 설정을 완료합니다.  

---

### ⚙️ 방법 2: 수동 설치

#### 1️⃣ 필수 라이브러리 설치

터미널을 열고 프로젝트 최상위 폴더로 이동한 뒤 다음 명령어를 실행합니다.

```bash
pip install -r requirements.txt
```

#### 2️⃣ Native Host 설정

- **com.example.pii_host.json 수정**  
  `native_host/com.example.pii_host.json` 파일을 열어 아래 항목을 수정합니다.  
  - `"path"`: `host.exe` 파일의 전체 경로 (경로의 `\`는 `\`로 두 번 입력)  
  - `"allowed_origins"`: Chrome 확장 프로그램의 실제 ID로 수정  

- **레지스트리 등록 (Windows)**  

```bash
reg add "HKCU\Software\Google\Chrome\NativeMessagingHosts\com.example.pii_host" /ve /t REG_SZ /d "C:\path\to\project\native_host\com.example.pii_host.json" /f
```

> ⚠️ `C:\path\to\project` 부분은 실제 경로로 변경해야 합니다.

#### 3️⃣ 브라우저 확장 프로그램 로드

1. Chrome에서 `chrome://extensions` 페이지로 이동  
2. **개발자 모드** 활성화  
3. **압축 해제된 확장 프로그램 로드** 클릭  
4. `extension` 폴더 선택  

---

## 🛠️ 사용 방법

1. **서버 실행**  
   ```bash
   python server/LocalServer.py
   ```

2. **확장 프로그램 활성화**  
   Chrome의 `chrome://extensions` 페이지에서 `PII Agent`가 활성화되어 있는지 확인합니다.  

3. **테스트 실행**  
   ChatGPT 등 LLM 서비스에 접속하여 아래와 같은 프롬프트를 입력합니다.  
   ```
   제 주민등록번호는 900101-1234567 입니다.
   ```

4. **로그 확인**  
   LocalServer 실행 터미널에서 실시간 탐지 로그가 표시됩니다.

---

## 📜 License
MIT License

---

## 👤 Author
**Shadow AI Project Team**
