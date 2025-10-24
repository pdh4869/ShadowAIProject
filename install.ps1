# ShadowAI PII 탐지 시스템 자동 설치 스크립트
# PowerShell에서 실행: .\install.ps1

Write-Host "🚀 ShadowAI PII 탐지 시스템 설치 시작..." -ForegroundColor Green

# 0. 루트 경로 검증
if (-not (Test-Path "server\LocalServer_Final.py")) {
    Write-Host "❌ 프로젝트 루트( server\LocalServer_Final.py 가 있는 위치 )에서 실행하세요." -ForegroundColor Red
    exit 1
}

# 1. Python 버전 확인
Write-Host "`n1️⃣ Python 설치 확인 중..." -ForegroundColor Yellow
try {
    $pythonVersion = py --version
    Write-Host "✅ Python 설치됨: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python이 설치되지 않았습니다. https://python.org 에서 설치하세요." -ForegroundColor Red
    exit 1
}

# 2. 패키지 설치
Write-Host "`n2️⃣ Python 패키지 설치 중..." -ForegroundColor Yellow
Write-Host "기본 패키지 설치 중..."
py -m pip install -r requirements.txt

Write-Host "추가 패키지 설치 중..."
py -m pip install tensorflow pyinstaller

# 3. 환경 변수 설정
Write-Host "`n3️⃣ 환경 변수 설정 중..." -ForegroundColor Yellow

# 사용자에게 토큰 입력 받기
Write-Host "허깅페이스 토큰이 필요합니다. (https://huggingface.co/settings/tokens 에서 생성)" -ForegroundColor Cyan
$hfToken = Read-Host "허깅페이스 토큰을 입력하세요"
if ([string]::IsNullOrEmpty($hfToken)) {
    Write-Host "❌ 허깅페이스 토큰이 필요합니다!" -ForegroundColor Red
    exit 1
}

# 대시보드 IP 입력 받기
Write-Host "대시보드 서버 IP 주소가 필요합니다." -ForegroundColor Cyan
$dashboardIP = Read-Host "대시보드 서버 IP를 입력하세요 (예: 192.168.1.100)"
if ([string]::IsNullOrEmpty($dashboardIP)) {
    Write-Host "❌ 대시보드 IP가 필요합니다!" -ForegroundColor Red
    exit 1
}
$dashboardUrl = "http://$dashboardIP:5000/api/log-pii"

# 환경 변수 설정
$env:HF_TOKEN = $hfToken
$env:DASHBOARD_URL = $dashboardUrl
[Environment]::SetEnvironmentVariable("HF_TOKEN", $hfToken, "User")
[Environment]::SetEnvironmentVariable("DASHBOARD_URL", $dashboardUrl, "User")

Write-Host "✅ 환경 변수 설정 완료" -ForegroundColor Green

# 4. .env 파일 생성
Write-Host "`n4️⃣ .env 파일 생성 중..." -ForegroundColor Yellow
$envContent = @"
# 허깅페이스 토큰
HF_TOKEN=$hfToken

# 대시보드 설정
DASHBOARD_URL=$dashboardUrl
DASHBOARD_REQUIRE_AUTH=false
DASHBOARD_API_SECRET=

# 기타 환경 변수들
PII_REQUIRE_AUTH=false
ALLOWED_EXTENSION_ID=CHANGE_AFTER_LOADING_EXTENSION
"@

$envContent | Out-File -FilePath ".env" -Encoding UTF8
Write-Host "✅ .env 파일 생성 완료" -ForegroundColor Green

# 5. 네이티브 호스트 설정
Write-Host "`n5️⃣ 네이티브 호스트 설정 중..." -ForegroundColor Yellow

# 현재 경로 가져오기
$currentPath = (Get-Location).Path

# com.example.pii_host.json 파일 수정
$hostConfigPath = "native_host\com.example.pii_host.json"
if (-not (Test-Path $hostConfigPath)) {
    Write-Host "❌ 파일 없음: $hostConfigPath" -ForegroundColor Red
    exit 1
}
$hostConfigRaw = Get-Content $hostConfigPath -Raw
$hostConfig = $hostConfigRaw | ConvertFrom-Json
$hostConfig.path = "$currentPath\native_host\build\host\host.exe"
$hostConfig | ConvertTo-Json -Depth 10 | Out-File $hostConfigPath -Encoding UTF8

# register_host.reg 파일 생성/갱신
$regPath = "native_host\register_host.reg"
$regContent = @"
Windows Registry Editor Version 5.00

[HKEY_CURRENT_USER\Software\Google\Chrome\NativeMessagingHosts\com.example.pii_host]
@="$($currentPath.Replace('\', '\\'))\\native_host\\com.example.pii_host.json"
"@

$regContent | Out-File -FilePath $regPath -Encoding UTF8

Write-Host "✅ 네이티브 호스트 경로/레지스트리 파일 업데이트 완료" -ForegroundColor Green

# 6. 네이티브 호스트 빌드
Write-Host "`n6️⃣ 네이티브 호스트 빌드 중..." -ForegroundColor Yellow
Push-Location "native_host"
py -m PyInstaller --onefile --distpath=build/host --name=host host.py
Pop-Location
Write-Host "✅ 네이티브 호스트 빌드 완료" -ForegroundColor Green

# 7. 레지스트리 등록
Write-Host "`n7️⃣ 네이티브 호스트 레지스트리 등록 중..." -ForegroundColor Yellow
try {
    reg import "native_host\register_host.reg" | Out-Null
    Write-Host "✅ 레지스트리 등록 완료" -ForegroundColor Green
} catch {
    Write-Host "⚠️ 레지스트리 등록 실패. 관리자 권한으로 다시 시도하세요." -ForegroundColor Yellow
}

# 8. 확장 프로그램 ID 설정
Write-Host "`n8️⃣ 확장 프로그램 ID 설정..." -ForegroundColor Yellow
Write-Host "Chrome에서 확장 프로그램을 먼저 로드하세요:" -ForegroundColor Cyan
Write-Host "1. Chrome에서 chrome://extensions/ 접속" -ForegroundColor White
Write-Host "2. '개발자 모드' 활성화" -ForegroundColor White
Write-Host "3. '압축해제된 확장 프로그램 로드' 클릭" -ForegroundColor White
Write-Host "4. extension 폴더 선택" -ForegroundColor White
Write-Host "5. 생성된 ID 복사" -ForegroundColor White

$extensionId = Read-Host "`n생성된 확장 프로그램 ID를 입력하세요 (32자리 영문자)"
if ([string]::IsNullOrEmpty($extensionId)) {
    Write-Host "⚠️ 확장 프로그램 ID를 나중에 수동으로 설정해야 합니다." -ForegroundColor Yellow
} elseif ($extensionId -notmatch '^[a-z0-9]{32}$') {
    Write-Host "❌ 확장 프로그램 ID 형식이 올바르지 않습니다. (소문자 영문/숫자 32자)" -ForegroundColor Red
    exit 1
} else {
    # .env 파일 업데이트
    $envPath = ".env"
    if (-not (Test-Path $envPath)) {
        Write-Host "❌ .env 파일이 없습니다." -ForegroundColor Red
        exit 1
    }
    $envContentRaw = Get-Content $envPath -Raw
    $envContentRaw = $envContentRaw.Replace("ALLOWED_EXTENSION_ID=CHANGE_AFTER_LOADING_EXTENSION", "ALLOWED_EXTENSION_ID=$extensionId")
    $envContentRaw | Out-File -FilePath $envPath -Encoding UTF8 -NoNewline

    # server/LocalServer_Final.py 업데이트 (기본값이 무엇이든 32자 토큰을 교체)
    $serverPath = "server\LocalServer_Final.py"
    if (-not (Test-Path $serverPath)) {
        Write-Host "❌ 파일 없음: $serverPath" -ForegroundColor Red
        exit 1
    }
    $serverContent = Get-Content $serverPath -Raw
    $serverContent = $serverContent -replace '(?<=os\.getenv\(\s*"ALLOWED_EXTENSION_ID"\s*,\s*")[a-z0-9]{32}(?="\s*\))', $extensionId
    $serverContent | Out-File -FilePath $serverPath -Encoding UTF8 -NoNewline

    # native_host/com.example.pii_host.json 업데이트
    $hostConfig = (Get-Content $hostConfigPath -Raw) | ConvertFrom-Json
    $hostConfig.allowed_origins = @("chrome-extension://$extensionId/")
    $hostConfig | ConvertTo-Json -Depth 10 | Out-File $hostConfigPath -Encoding UTF8

    Write-Host "✅ 확장 프로그램 ID가 .env / 서버 / 네이티브 호스트에 모두 반영되었습니다!" -ForegroundColor Green
}

# 9. 설치 완료
Write-Host "`n🎉 설치 완료!" -ForegroundColor Green

Write-Host "`n📋 설치 완료 확인사항:" -ForegroundColor Cyan
Write-Host "- 서버 주소: http://127.0.0.1:9000" -ForegroundColor White
Write-Host "- 대시보드: $dashboardUrl" -ForegroundColor White
if ($extensionId -and $extensionId -match '^[a-z0-9]{32}$') {
    Write-Host "- 확장 프로그램 ID: $extensionId (설정 완료)" -ForegroundColor Green
} else {
    Write-Host "- 확장 프로그램 ID: 수동 설정 필요" -ForegroundColor Yellow
}

Write-Host "`n🚀 다음 단계:" -ForegroundColor Cyan
Write-Host "서버 실행: cd server && py LocalServer_Final.py" -ForegroundColor White

Read-Host "`nEnter를 누르면 종료됩니다..."