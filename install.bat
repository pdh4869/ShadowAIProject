@echo off
chcp 65001 >nul

:: =================================================================
:: !!! 중요: 아래의 확장 프로그램 ID를 당신의 ID로 수정하세요 !!!
:: =================================================================
:: 1. 이 스크립트를 한 번 실행하여 초기 설정을 마칩니다.
:: 2. Chrome에서 chrome://extensions 페이지를 열고 '압축 해제된 확장 프로그램 로드'로
::    extension 폴더를 로드한 후, 생성된 ID를 복사합니다.
:: 3. 아래 YOUR_EXTENSION_ID_HERE 부분을 복사한 ID로 변경하고 저장한 뒤,
::    이 스크립트를 다시 한번 실행하면 최종 설정이 완료됩니다.
:: =================================================================
set EXTENSION_ID=YOUR_EXTENSION_ID_HERE


echo ========================================
echo Shadow AI 자동 설치 스크립트
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
echo [1/4] Python 경로 탐지 중...
for /f "delims=" %%i in ('where python') do set "PYTHON_PATH=%%i"
if not defined PYTHON_PATH (
    echo [오류] Python이 설치되어 있지 않거나 경로가 설정되지 않았습니다.
    echo Python 3.9 이상을 설치한 후 다시 실행하세요.
    pause
    exit /b 1
)
echo ✓ Python 경로: %PYTHON_PATH%

:: 경로 설정
set SCRIPT_DIR=%~dp0
set NATIVE_HOST_DIR=%SCRIPT_DIR%native_host

:: Native Host 실행 파일 생성
echo.
echo [2/4] Native Host 실행 파일(run_host.bat) 생성 중...
(
    echo @echo off
    echo "%PYTHON_PATH%" "%NATIVE_HOST_DIR%host.py"
) > "%NATIVE_HOST_DIR%\run_host.bat"
echo ✓ run_host.bat 생성 완료

:: Chrome Native Messaging Host 설정 파일(.json) 생성 및 레지스트리 등록
echo.
echo [3/4] Chrome Native Messaging Host 설정 중...
set RUN_HOST_PATH=%NATIVE_HOST_DIR%\run_host.bat
set RUN_HOST_PATH=%RUN_HOST_PATH:\=\\%
set JSON_PATH=%NATIVE_HOST_DIR%\com.example.pii_host.json

(
    echo {
    echo    "name": "com.example.pii_host",
    echo    "description": "PII Agent Native Host",
    echo    "path": "%RUN_HOST_PATH%",
    echo    "type": "stdio",
    echo    "allowed_origins": [
    echo        "chrome-extension://%EXTENSION_ID%/"
    echo    ]
    echo }
) > "%JSON_PATH%"

set REG_KEY="HKCU\Software\Google\Chrome\NativeMessagingHosts\com.example.pii_host"
reg add %REG_KEY% /ve /t REG_SZ /d "%JSON_PATH%" /f >nul
echo ✓ 설정 파일 생성 및 레지스트리 등록 완료

:: Python 패키지 설치
echo.
echo [4/4] 필수 Python 패키지 설치 중...
"%PYTHON_PATH%" -m pip install -r "%SCRIPT_DIR%requirements.txt" >nul
if %errorLevel% equ 0 (
    echo ✓ Python 패키지 설치 완료
) else (
    echo [경고] 일부 패키지 설치에 실패했습니다.
)

echo.
echo =================================================================
if "%EXTENSION_ID%"=="YOUR_EXTENSION_ID_HERE" (
    echo               초기 설정 완료! - 다음 단계를 진행하세요
    echo =================================================================
    echo.
    echo   1. Chrome 브라우저에서 주소창에 chrome://extensions 를 입력하세요.
    echo   2. 우측 상단의 '개발자 모드'를 활성화하세요.
    echo   3. '압축해제된 확장 프로그램을 로드합니다' 버튼을 클릭하고,
    echo      이 프로젝트의 'extension' 폴더를 선택하세요.
    echo.
    echo   4. 방금 로드한 확장 프로그램 정보 창에서 'ID' 값을 복사하세요.
    echo      (예: mhfhimdjakcgolmhjiplchgchfahhemd)
    echo.
    echo   5. 이 install.bat 파일을 편집기로 열어서 맨 위쪽의
    echo      'YOUR_EXTENSION_ID_HERE' 부분을 방금 복사한 ID로 바꾸고 저장하세요.
    echo.
    echo   6. 마지막으로, 이 install.bat 파일을 한번 더 실행하여 최종 설정을 완료하세요!
) else (
    echo                      최종 설정이 완료되었습니다!
    echo =================================================================
    echo.
    echo   모든 설정이 완료되었습니다.
    echo.
    echo   1. Chrome 브라우저의 확장 프로그램 목록(chrome://extensions)에서
    echo      'PII Agent'가 활성화되어 있는지 확인하세요.
    echo.
    echo   2. 아래 명령어로 로컬 서버를 실행하면 모든 준비가 끝납니다:
    echo      python "%SCRIPT_DIR%server\LocalServer.py"
)
echo.
pause