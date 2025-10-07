# PII Agent - 개인정보 탐지 시스템

## 📋 시스템 요구사항
- Windows 10/11
- Python 3.8 이상
- Google Chrome 브라우저

## 🚀 빠른 설치 (권장)

### 1단계: 자동 설치
1. `install.bat` 파일을 **마우스 우클릭**
2. **"관리자 권한으로 실행"** 선택
3. 설치 완료까지 대기 (약 2-3분)

**자동으로 설치되는 항목:**
- Python 경로 자동 탐지
- `requirements.txt` 기반 모든 라이브러리 설치
- Native Host 설정 파일 생성
- 레지스트리 자동 등록

### 2단계: Chrome 확장 프로그램 설치
1. Chrome 브라우저 열기
2. 주소창에 `chrome://extensions/` 입력
3. 우측 상단 **"개발자 모드"** 토글 활성화
4. **"압축해제된 확장 프로그램을 로드합니다"** 클릭
5. `Py_server\extension` 폴더 선택

### 3단계: 서버 실행
```cmd
cd Py_server\server
python LocalServer.py
```

### 4단계: 대시보드 접속
브라우저에서 `http://localhost:8000` 접속

---

## 🔧 수동 설치 (고급 사용자)

### 1. Python 패키지 설치
```cmd
pip install -r requirements.txt
```

**requirements.txt 내용:**
- fastapi
- uvicorn
- transformers
- torch
- easyocr
- pymupdf
- pillow
- mtcnn
- pycryptodome
- python-docx

### 2. Native Host 설정
1. `Py_server\native_host\run_host.bat` 파일에서 Python 경로 수정
2. Native Messaging Host JSON 생성:
   - 경로: `%LOCALAPPDATA%\Google\Chrome\User Data\NativeMessagingHosts\com.example.pii_host.json`
   - 내용:
   ```json
   {
     "name": "com.example.pii_host",
     "description": "PII Detection Native Host",
     "path": "C:\\절대경로\\Py_server\\native_host\\run_host.bat",
     "type": "stdio",
     "allowed_origins": [
       "chrome-extension://hblalecgjndcjeaineacembpdfmmjaoa/"
     ]
   }
   ```

### 3. 레지스트리 등록
```cmd
reg add "HKCU\Software\Google\Chrome\NativeMessagingHosts\com.example.pii_host" /ve /t REG_SZ /d "%LOCALAPPDATA%\Google\Chrome\User Data\NativeMessagingHosts\com.example.pii_host.json" /f
```

---

## 🗑️ 제거 방법

### 자동 제거
1. `uninstall.bat` 파일을 **마우스 우클릭**
2. **"관리자 권한으로 실행"** 선택
3. Chrome에서 확장 프로그램 수동 제거

---

## 📖 사용 방법

### 지원 사이트
- ChatGPT (https://chatgpt.com/)
- Gemini (https://gemini.google.com/)

### 탐지 항목
- **텍스트**: 이름, 전화번호, 이메일, 주민등록번호, 카드번호 등
- **파일**: PDF, DOCX, 이미지 내 개인정보
- **얼굴**: 이미지/문서 내 얼굴 탐지

### 대시보드 기능
- 실시간 탐지 내역 확인
- 탐지된 개인정보 상세 보기
- 브라우저/OS 정보 확인

---

## ⚠️ 문제 해결

### Chrome 확장 프로그램이 작동하지 않을 때
1. `chrome://extensions/` 접속
2. PII Agent 확장 프로그램 찾기
3. **새로고침 버튼(⟳)** 클릭
4. 페이지 새로고침 (F5)

### Native Host 연결 오류
1. `install.bat` 다시 실행 (관리자 권한)
2. Chrome 완전 종료 후 재시작
3. `Py_server\native_host\host_log.txt` 로그 확인

### 서버 실행 오류
```cmd
# Python 경로 확인
where python

# 패키지 재설치
pip install --upgrade -r requirements.txt
```

---

## 📁 프로젝트 구조
```
Py_server/
├── install.bat              # 자동 설치 스크립트
├── uninstall.bat            # 자동 제거 스크립트
├── requirements.txt         # Python 패키지 목록
├── README2.md               # 이 파일
├── Py_server/
│   ├── extension/           # Chrome 확장 프로그램
│   │   ├── manifest.json
│   │   ├── background.js
│   │   └── content.js
│   ├── native_host/         # Native Messaging Host
│   │   ├── host.py
│   │   └── run_host.bat
│   └── server/              # FastAPI 서버
│       ├── LocalServer.py
│       └── Logic.py
```

---

## 📞 지원
문제가 발생하면 다음 로그 파일을 확인하세요:
- Native Host: `Py_server\native_host\host_log.txt`
- Chrome Console: F12 → Console 탭
