@echo off
chcp 65001 >nul
echo ========================================
echo PII Agent 제거 스크립트
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

:: Native Messaging Host JSON 삭제
echo [1/2] Native Messaging Host 설정 파일 삭제 중...
set NATIVE_HOST_JSON=%LOCALAPPDATA%\Google\Chrome\User Data\NativeMessagingHosts\com.example.pii_host.json
if exist "%NATIVE_HOST_JSON%" (
    del "%NATIVE_HOST_JSON%"
    echo ✓ 설정 파일 삭제 완료
) else (
    echo - 설정 파일이 없습니다
)

:: 레지스트리 삭제
echo.
echo [2/2] 레지스트리 삭제 중...
reg delete "HKCU\Software\Google\Chrome\NativeMessagingHosts\com.example.pii_host" /f >nul 2>&1
if %errorLevel% equ 0 (
    echo ✓ 레지스트리 삭제 완료
) else (
    echo - 레지스트리 항목이 없습니다
)

echo.
echo ========================================
echo 제거 완료!
echo ========================================
echo.
echo Chrome 확장 프로그램은 수동으로 제거하세요:
echo chrome://extensions/ 에서 PII Agent 제거
echo.
pause
