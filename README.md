# ShadowAIProject
Masking project that blocks bad acts to Generative AI

## server.py와 연결된 db에 사용자 있음. 확장 프로그램으로 로그인. receive.py로 사번 전송 (대시보드 예정)

Chrome Extension Login & Data Forwarding System
이 프로젝트는 Chrome 확장 프로그램 팝업 내에서 사용자가 직접 로그인하고, Python Flask로 구축된 백엔드 서버를 통해 인증을 처리하는 시스템입니다.

로그인에 성공하면, 사용자의 특정 데이터(예: 사번)를 또 다른 서버 엔드포인트로 전송하는 기능이 포함되어 있습니다.


✨ 주요 기능
팝업 내장 로그인: 별도의 웹 페이지 탭을 열지 않고, 확장 프로그램 팝업 안에서 직접 아이디와 비밀번호를 입력하여 로그인합니다.

토큰 기반 인증: JWT(JSON Web Token)를 사용하여 안전하고 상태 없이(stateless) 사용자의 로그인 세션을 관리합니다.

동적 UI 변경: 사용자의 로그인 상태에 따라 팝업 화면이 '로그인 폼'과 '로그아웃 버튼'으로 자동 전환됩니다.

데이터베이스 연동: MySQL 데이터베이스에 사용자 정보를 저장하고 관리하며, SQLAlchemy ORM을 통해 데이터를 처리합니다.

데이터 포워딩: 로그인 성공 시, 사용자의 사번(employee_id)을 지정된 두 번째 서버(또는 다른 API 엔드포인트)로 즉시 전송합니다.

CORS 처리: 확장 프로그램 환경(chrome-extension://...)과 서버 간의 교차 출처 리소스 공유(CORS) 문제를 처리합니다.


🛠️ 기술 스택
백엔드: Python, Flask, Flask-SQLAlchemy, Flask-Cors, PyJWT

데이터베이스: MySQL

프론트엔드: JavaScript (Chrome Extension APIs), HTML, CSS


🚀 설치 및 실행 방법

1. 사전 준비
Python 3.x 버전 설치

MySQL 서버 설치 및 실행

Google Chrome 브라우저


2. 백엔드 서버 설정
프로젝트 클론 또는 다운로드

Bash

git clone <repository_url>
cd <project_folder>
필요 라이브러리 설치

Bash

pip install Flask Flask-SQLAlchemy Flask-Cors PyMySQL PyJWT
데이터베이스 설정

MySQL에 접속하여 이 프로젝트가 사용할 데이터베이스를 생성합니다. (예: shadowai)

SQL

CREATE DATABASE shadowai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
데이터베이스에 접근할 사용자를 생성하고 권한을 부여합니다.

app.py 설정 수정

app.py 파일을 열어 상단에 있는 아래 변수들을 자신의 환경에 맞게 수정합니다.

SECRET_KEY: JWT 서명을 위한 임의의 비밀 키

SQLALCHEMY_DATABASE_URI: MySQL 연결 정보

CHROME_EXTENSION_ID: 아래 '프론트엔드 설정' 4단계에서 확인한 확장 프로그램 ID

서버 실행

터미널에서 아래 명령어를 실행하여 서버를 시작합니다. 테이블이 없으면 자동으로 생성됩니다.

Bash

python app.py
서버는 기본적으로 http://127.0.0.1:5001에서 실행됩니다.

3. 프론트엔드 (확장 프로그램) 설정
프로젝트 내의 extension 폴더가 확장 프로그램의 소스 코드입니다.

Google Chrome에서 주소창에 chrome://extensions/를 입력하여 확장 프로그램 관리 페이지로 이동합니다.

오른쪽 상단의 **'개발자 모드'**를 활성화합니다.

'압축해제된 확장 프로그램을 로드합니다' 버튼을 클릭하고, extension 폴더를 선택합니다.

설치된 확장 프로그램 카드에서 ID를 복사한 뒤, 위 '백엔드 설정' 4단계에 따라 app.py의 CHROME_EXTENSION_ID 변수에 붙여넣고 서버를 재시작합니다.


📂 파일 구조


├── extension/                # 크롬 확장 프로그램 폴더

│   ├── popup.html            # 팝업 UI

│   ├── popup.js              # 팝업 로직

│   └── manifest.json         # 확장 프로그램 설정 파일

│

├── app.py                    # 메인 인증 서버 (서버 A)

└── receive_server.py         # 데이터 수신 테스트용 서버 (서버 B)


🔌 API 엔드포인트
이 프로젝트는 다음과 같은 API 엔드포인트를 사용합니다.

서버 A (app.py, port:5001)
POST /api/login

설명: 사용자를 인증하고 JWT 토큰을 발급합니다.

요청 본문 (JSON): {"employee_id": "...", "password": "..."}

성공 응답 (JSON): {"token": "..."}

서버 B (receive_server.py, port:5002)
POST /api/receive-data

설명: 확장 프로그램으로부터 사번 데이터를 수신합니다.

요청 본문 (JSON): {"employee_id": "..."}

성공 응답 (JSON): {"status": "success", "message": "..."}
