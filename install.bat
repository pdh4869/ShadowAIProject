@echo off
chcp 65001 >nul
echo ========================================
echo PII Agent 자동 설치 스크립트
echo ========================================
echo.

:: 관리자 권한 확인
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [오류] 관리자 권한이 필요합니다.
    echo 이 파일을 마우스 우클릭 후 "관리자 권한으로 실행"을 선택하세요.
    pause
    exit /b 1
)

:: Python 경로 자동 탐지
echo [1/5] Python 경로 탐지 중...
where python >nul 2>&1
if %errorLevel% neq 0 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo Python 3.8 이상을 설치한 후 다시 실행하세요.
    pause
    exit /b 1
)

for /f "delims=" %%i in ('where python') do set PYTHON_PATH=%%i
echo ✓ Python 경로: %PYTHON_PATH%

:: 현재 스크립트 경로
set SCRIPT_DIR=%~dp0
set NATIVE_HOST_DIR=%SCRIPT_DIR%native_host
set EXTENSION_DIR=%SCRIPT_DIR%extension

:: 필수 디렉토리 확인
if not exist "%NATIVE_HOST_DIR%" (
    echo [오류] native_host 폴더를 찾을 수 없습니다.
    pause
    exit /b 1
)

:: run_host.bat 생성
echo.
echo [2/5] Native Host 배치 파일 생성 중...
(
    echo @echo off
    echo "%PYTHON_PATH%" "%%~dp0host.py"
) > "%NATIVE_HOST_DIR%\run_host.bat"
echo ✓ run_host.bat 생성 완료

:: Native Messaging Host JSON 생성
echo.
echo [3/5] Native Messaging Host 설정 파일 생성 중...
set NATIVE_HOST_JSON=%LOCALAPPDATA%\Google\Chrome\User Data\NativeMessagingHosts\com.example.pii_host.json

if not exist "%LOCALAPPDATA%\Google\Chrome\User Data\NativeMessagingHosts" (
    mkdir "%LOCALAPPDATA%\Google\Chrome\User Data\NativeMessagingHosts"
)

:: JSON 파일 생성 (경로 이스케이프 처리)
set RUN_HOST_PATH=%NATIVE_HOST_DIR%\run_host.bat
set RUN_HOST_PATH=%RUN_HOST_PATH:\=\\%

(
    echo {
    echo   "name": "com.example.pii_host",
    echo   "description": "PII Detection Native Host",
    echo   "path": "%RUN_HOST_PATH%",
    echo   "type": "stdio",
    echo   "allowed_origins": [
    echo     "chrome-extension://hblalecgjndcjeaineacembpdfmmjaoa/"
    echo   ]
    echo }
) > "%NATIVE_HOST_JSON%"
echo ✓ Native Messaging Host JSON 생성 완료

:: 레지스트리 등록
echo.
echo [4/5] 레지스트리 등록 중...
reg add "HKCU\Software\Google\Chrome\NativeMessagingHosts\com.example.pii_host" /ve /t REG_SZ /d "%NATIVE_HOST_JSON%" /f >nul 2>&1
if %errorLevel% equ 0 (
    echo ✓ 레지스트리 등록 완료
) else (
    echo [경고] 레지스트리 등록 실패
)

:: Python 패키지 설치
echo.
echo [5/5] Python 패키지 설치 중...
echo    (시간이 다소 걸릴 수 있습니다...)
"%PYTHON_PATH%" -m pip install --upgrade pip
"%PYTHON_PATH%" -m pip install -r "%SCRIPT_DIR%requirements.txt"
if %errorLevel% equ 0 (
    echo ✓ Python 패키지 설치 완료
) else (
    echo [경고] 일부 패키지 설치 실패
)

echo.
echo ========================================
echo 설치 완료!
echo ========================================
echo.
echo 다음 단계:
echo 1. Chrome 브라우저에서 chrome://extensions/ 접속
echo 2. "개발자 모드" 활성화 (우측 상단 토글)
echo 3. "압축해제된 확장 프로그램을 로드합니다" 클릭
echo 4. 다음 폴더 선택: %EXTENSION_DIR%
echo 5. 서버 실행: python "%SCRIPT_DIR%server\LocalServer.py"
echo.
pause
