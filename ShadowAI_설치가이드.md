📋 ShadowAI PII 탐지 시스템 설치 가이드 이 가이드는 install.ps1
스크립트를 사용하여 설치를 자동화하는 과정을 안내합니다.

## 1단계: 사전 준비 및 Hugging Face 토큰 생성

스크립트를 실행하기 전에 다음 두 가지 정보를 미리 준비해야 합니다.

-   **Python 설치 확인**: 컴퓨터에 Python이 설치되어 있어야 합니다
    (스크립트가 `py --version` 명령어로 확인합니다).
-   **대시보드 서버 IP**: PII 탐지 로그를 전송할 대시보드 서버의 IP
    주소입니다 (예: `192.168.1.100`).
-   **Hugging Face 토큰 (Access Token) 생성**: AI 모델을 다운로드하려면
    허깅페이스 인증 토큰이 필요합니다. 스크립트 실행 전에 미리 생성하여
    복사해 두는 것이 편리합니다.

1.  웹 브라우저에서 <https://huggingface.co/settings/tokens> 로 이동하여
    로그인합니다 (계정이 없다면 **Sign Up**으로 회원가입).
2.  **Access Tokens** 페이지에서 **New token** 버튼을 클릭합니다.
3.  **Name**: 토큰의 용도를 알아보기 쉽게 이름을 입력합니다 (예:
    `ShadowAIProject`).
4.  **Role**: 권한을 `read` (읽기)로 선택합니다.
5.  **Generate a token** 버튼을 클릭합니다.
6.  **\[중요\]** 토큰이 생성되면 `hf_`로 시작하는 긴 문자열이
    표시됩니다. 이 토큰은 지금만 전체 값을 볼 수 있으므로, 즉시 복사
    아이콘을 클릭하여 토큰 값을 복사한 뒤, 메모장 등 안전한 곳에 임시로
    보관하세요. 이 토큰을 2단계에서 사용합니다.

------------------------------------------------------------------------

## 2단계: 설치 스크립트 실행 및 정보 입력

PowerShell을 열어 이 프로젝트의 루트 폴더(`install.ps1` 파일이 있는
위치)로 이동한 후, 다음 명령어를 입력하여 스크립트를 실행합니다.

``` powershell
.\install.ps1
(실행 정책으로 인해 실행이 안될 시 
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
명령어로 현재 창에서만 Bypss로 변경)
```

스크립트가 실행되면 다음 과정을 자동으로 진행하며, 중간에 사용자 입력을
요구합니다.

-   **패키지 자동 설치**: `requirements.txt`의 패키지들과 `tensorflow`,
    `pyinstaller`를 자동으로 설치합니다.
-   **허깅페이스 토큰 입력**: `"허깅페이스 토큰을 입력하세요"`라는
    메시지가 나타나면, 1단계에서 복사해 둔 토큰 값(`hf_...`)을 붙여넣고
    Enter를 누릅니다.
-   **대시보드 IP 입력**: `"대시보드 서버 IP를 입력하세요"`라는 메시지가
    나타나면, 준비한 IP 주소(예: `192.168.1.100`)를 입력하고 Enter를
    누릅니다.
-   **자동 설정**: 스크립트가 입력된 정보를 바탕으로 `.env` 파일을 자동
    생성하고, `native_host` 빌드 및 레지스트리 등록을 자동으로
    완료합니다.

------------------------------------------------------------------------

## 3단계: Chrome 확장 프로그램 로드 및 ID 입력

스크립트가 잠시 멈추고 확장 프로그램 ID를 입력하라고 요청합니다. 이때
다음 작업을 수행해야 합니다.

1.  Chrome 브라우저를 열고 주소창에 `chrome://extensions/` 를 입력하여
    확장 프로그램 관리 페이지로 이동합니다.
2.  우측 상단의 **개발자 모드(Developer mode)** 스위치를 켭니다.
3.  좌측 상단의 **압축해제된 확장 프로그램 로드(Load unpacked)** 버튼을
    클릭합니다.
4.  파일 탐색기가 열리면 이 프로젝트의 `extension` 폴더를 선택합니다.
5.  설치가 완료되면 `ShadowAI PII Detector` 항목에 **ID (32자리의
    영문자)** 가 표시됩니다. 이 ID를 복사합니다.
6.  다시 PowerShell 창으로 돌아와 복사한 ID를 붙여넣고 Enter를 누릅니다.

------------------------------------------------------------------------

## 4단계: 설치 완료 및 서버 실행

스크립트가 방금 입력한 ID를 `.env`, `server\LocalServer_Final.py`,
`native_host\com.example.pii_host.json` 세 곳에 모두 자동으로
반영합니다.

`🎉 설치 완료!` 메시지가 나타나면 모든 설정이 끝난 것입니다.

이제 다음 명령어를 입력하여 로컬 서버를 실행할 수 있습니다.

``` powershell
cd server
py LocalServer_Final.py
```

## 1.2 수동 설치 (자동 설치 실패 시)

PowerShell 스크립트(`install.ps1`) 실행이 불가능하거나 오류가 발생하는 경우, 다음 단계를 순서대로 따라 수동으로 설치할 수 있습니다.

### 1.2.1. 사전 준비
- PC에 Python을 설치합니다.
- Hugging Face 토큰과 대시보드 IP를 미리 준비합니다. (1.1.1. 항목 참고)

### 1.2.2. Python 패키지 설치
```bash
py -m pip install -r requirements.txt
py -m pip install tensorflow pyinstaller
```

### 1.2.3. 환경 변수 설정
Windows '시스템 환경 변수 편집'을 통해 다음 2개의 사용자 환경 변수를 직접 추가합니다.

- 변수 이름: HF_TOKEN  
  변수 값: [준비한 Hugging Face 토큰 값 (hf_...)]
- 변수 이름: DASHBOARD_URL  
  변수 값: http://[준비한 대시보드 IP]:5000/api/log-pii

### 1.2.4. .env 파일 생성
프로젝트 루트 폴더(install.ps1이 있는 위치)에 `.env` 라는 이름의 새 파일을 생성하고, 아래 내용을 복사하여 붙여넣습니다.

```bash
# 허깅페이스 토큰
HF_TOKEN=[준비한 Hugging Face 토큰 값]

# 대시보드 설정
DASHBOARD_URL=http://[준비한 대시보드 IP]:5000/api/log-pii
DASHBOARD_REQUIRE_AUTH=false
DASHBOARD_API_SECRET=

# 기타 환경 변수들
PII_REQUIRE_AUTH=false
ALLOWED_EXTENSION_ID=CHANGE_AFTER_LOADING_EXTENSION
```
> **(중요)**: HF_TOKEN과 DASHBOARD_URL 값을 실제 값으로 직접 수정해야 합니다.

### 1.2.5. 네이티브 호스트 빌드
```bash
cd native_host
py -m PyInstaller --onefile --distpath=build/host --name=host host.py
cd ..
```

### 1.2.6. 네이티브 호스트 경로 설정 (.json)
`native_host\com.example.pii_host.json` 파일을 텍스트 편집기(메모장 등)으로 열어 `"path"` 키의 값을 수정합니다.

> [중요] 경로 구분자는 반드시 이중 역슬래시(`\\`)여야 합니다.

변경 전 (예시): `"path": "C:\\Users\\KSH\\AppData\\...\\host.exe"`  
변경 후 (예시): `"path": "C:\\MyProjects\\ShadowAIProject-integratedKKK\\native_host\\build\\host\\host.exe"`

### 1.2.7. 레지스트리 등록
`native_host\register_host.reg` 파일을 텍스트 편집기로 열고, 마지막 줄의 경로(@=...)를 현재 PC의 전체 경로로 수정합니다.

> [중요] 경로 구분자는 반드시 이중 역슬래시(`\\`)여야 합니다.

변경 전 (예시): `@="C:\\Users\\KSH\\AppData\\...\\com.example.pii_host.json"`  
변경 후 (예시): `@="C:\\MyProjects\\ShadowAIProject-integratedKKK\\native_host\\com.example.pii_host.json"`

파일을 저장한 뒤, `register_host.reg` 파일을 더블 클릭하여 실행하고 레지스트리 등록을 승인합니다.

### 1.2.8. 확장 프로그램 ID 3중 동기화
이 단계는 자동 설치(1.1.4)와 동일하게 진행하되, ID를 3곳에 수동으로 입력해야 합니다.

1. Chrome `chrome://extensions/` 에서 **개발자 모드**를 켜고, `extension` 폴더를 로드합니다.  
2. 생성된 **32자리 확장 프로그램 ID**를 복사합니다.

**파일 1: `.env` 파일**  
`ALLOWED_EXTENSION_ID=CHANGE_AFTER_LOADING_EXTENSION` 값을 `ALLOWED_EXTENSION_ID=[복사한_ID]` 로 변경합니다.

**파일 2: `server/LocalServer_Final.py`**  
기본값 `"jmmkffpdjciopflbblfpaomjceifdndf"` 를 복사한 새 ID로 교체합니다.

**파일 3: `native_host/com.example.pii_host.json`**  
`"allowed_origins"` 배열의 값을 수정합니다.  
변경 전: `"chrome-extension://jmmkffpdjciopflbblfpaomjceifdndf/"`  
변경 후: `"chrome-extension://[복사한_ID]/"`

### 1.2.9. 설치 완료
```bash
cd server
py LocalServer_Final.py
```
