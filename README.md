# 개인정보 탐지 시스템 (FastAPI)

문서/이미지에서 **개인정보**(텍스트·얼굴 등)를 자동 탐지하고 대시보드로 확인할 수 있는 로컬 서버입니다.  
- Backend: **FastAPI + Uvicorn**
- Dashboard: HTML/Tailwind (템플릿/인라인 두 가지 버전)
- OCR: **EasyOCR**, PDF 파싱: **PyMuPDF**
- NER: **Hugging Face Transformers**
- 얼굴 탐지(선택): **MTCNN** (TensorFlow 필요)
- 암호화: **PyCryptodome (AES)**

> 프로젝트 원본 폴더 기준 경로 예시: `Py_server - 복사본/Py_server/server`

---

## 📁 폴더 구조 (요약)

```
Py_server - 복사본/
└─ Py_server/
   └─ server/
      ├─ LocalServer.py          # API + 인라인 대시보드
      ├─ Logic.py                # OCR/NER/얼굴탐지/암호화 로직
      ├─ app.py                  # 템플릿 기반 대시보드(대안)
      └─ templates/
         └─ dashboard.html       # 템플릿 파일
```

---

## 🚀 주요 기능

- **파일/이벤트 수집 API**로 입력을 받아 분석 수행
- **OCR(EasyOCR)** 및 **정규식/NER** 기반 개인정보 탐지
- (선택) **얼굴 탐지(MTCNN)** – TensorFlow 설치 필요
- **AES 암호화** 후 백엔드로 전송하는 샘플 핸들러 포함
- **대시보드**(http://127.0.0.1:9000/dashboard)에서 탐지 이력 조회

---

## 🧩 필수 요건

- **Python 3.11 권장** (안정된 의존성 조합)
- macOS(Apple Silicon/Intel) 또는 Linux/Windows
- (선택) 얼굴탐지 사용 시 **TensorFlow** 필요

---

## 🔧 설치

> 아래 두 가지 방식 중 **하나**를 선택하세요.

### 옵션 A) Python 3.11 권장 경로

**macOS (Homebrew 예시)**

```bash
# (선택) Homebrew 설치가 필요하면 공식 문서 참고
brew install python@3.11

# 프로젝트 폴더로 이동
cd "Py_server - 복사본/Py_server/server"

# 가상환경 생성/활성화
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1

# 필수 패키지 설치 (권장 조합)
pip install --upgrade pip setuptools wheel

# TensorFlow + MTCNN(얼굴탐지) 사용할 경우: numpy 1.x + OpenCV 4.9 계열
pip install "numpy==1.26.4"
pip install "opencv-python==4.9.0.80"     # 또는 opencv-python-headless==4.9.0.80 (둘 중 하나)

# 나머지
pip install fastapi "uvicorn[standard]" Jinja2 Pillow PyMuPDF easyocr transformers python-docx pycryptodome requests mtcnn

# TensorFlow (환경에 맞는 것 택1)
# Apple Silicon: 가속 권장
pip install "tensorflow-macos>=2.16,<2.18" "tensorflow-metal>=1.1,<2"
# Intel/일반 CPU: 아래 사용
# pip install "tensorflow-cpu>=2.16,<2.18"
```

> 만약 얼굴탐지를 **사용하지 않을** 계획이라면, `mtcnn`/`tensorflow-*`는 설치하지 않아도 됩니다.

### 옵션 B) Python 3.13 등 최신 해상도(얼굴탐지 비활성화)

TensorFlow를 빼고 **numpy 2.x + OpenCV 4.12** 조합으로 간단히 실행:
```bash
cd "Py_server - 복사본/Py_server/server"
python -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1

pip install --upgrade pip setuptools wheel

# 얼굴탐지 비활성화 프로필
pip install "numpy>=2,<2.3"
pip install "opencv-python==4.12.0.88"    # 또는 opencv-python-headless==4.12.0.88 (둘 중 하나)
pip install fastapi "uvicorn[standard]" Jinja2 Pillow PyMuPDF easyocr transformers python-docx pycryptodome requests
# mtcnn / tensorflow-* 는 설치하지 않음
```

> 이 경우 `Logic.py`에서 **MTCNN import/사용을 try/except**로 감싸 **미설치 시 스킵**하도록 처리하세요.
> 예시:
> ```python
> try:
>     from mtcnn import MTCNN
>     _mtcnn_available = True
> except Exception:
>     _mtcnn_available = False
> # 사용부
> if _mtcnn_available:
>     # 얼굴탐지 수행
> else:
>     print("[INFO] MTCNN not installed; skipping face detection")
> ```

---

## ▶️ 실행

두 가지 서버 방식 중 **하나만** 사용하세요.

### 방법 1) `LocalServer.py` (API + 인라인 대시보드)

```bash
uvicorn LocalServer:app --host 127.0.0.1 --port 9000 --reload
```

- 대시보드: http://127.0.0.1:9000/dashboard  
- 엔드포인트:
  - `GET /` – 헬스체크/간단 페이지
  - `GET /dashboard` – 대시보드
  - `POST /api/file_collect` – 파일 수집/분석 트리거
  - `POST /api/event` – 파일 이벤트 등 외부 에이전트 보고
  - `GET /api/detections` – 탐지 이력 조회

### 방법 2) `app.py` (Jinja 템플릿 기반 대시보드)

```bash
python app.py     # 내부에서 127.0.0.1:9000 바인딩
```

---

## 🧪 빠른 테스트 (에이전트 모의)

에이전트가 없다면 `curl`로 API를 호출해 동작을 확인할 수 있습니다.

```bash
# 이벤트 보고
curl -X POST "http://127.0.0.1:9000/api/event" \
  -H "Content-Type: application/json" \
  -d '{"type":"file_created","file_name":"sample.pdf","timestamp":"2025-10-02T10:00:00"}'

# 파일 수집/분석 (예시)
curl -X POST "http://127.0.0.1:9000/api/file_collect" \
  -H "Content-Type: application/json" \
  -d '{"file_path":"/absolute/path/to/sample.pdf"}'

# 탐지 이력 확인
curl "http://127.0.0.1:9000/api/detections"
```

브라우저에서 http://127.0.0.1:9000/dashboard 접속해 카드/카운트가 올라가는지 확인하세요.

---

## ⚙️ 환경 변수/설정 (예시)

- `Key` (AES 키): 현재 `LocalServer.py`/`Logic.py`에 상수로 정의 (`b"1234567890abcdef"`).  
  운영 시 `.env`로 분리하고 `os.environ` 또는 `pydantic-settings`로 주입하는 것을 권장합니다.
- 모델/캐시 경로: `transformers`, `easyocr`는 최초 실행 시 모델을 다운로드할 수 있습니다(인터넷 필요).

---

## 🛠 트러블슈팅

- **OpenCV ↔ numpy 버전 충돌**
  - `opencv-python 4.12.0.88`는 **numpy 2.x** 요구, 반면 **TensorFlow**는 보통 **numpy 1.x**를 선호합니다.
  - 얼굴탐지(=TF/MTCNN)를 쓰면 `numpy==1.26.4 + opencv-python==4.9.0.80` 조합으로 맞추세요.
  - 얼굴탐지를 끄면 `numpy>=2,<2.3 + opencv-python==4.12.0.88` 조합 권장.
  - `opencv-python`과 `opencv-python-headless`는 **둘 중 하나만** 설치하세요.

- **`ModuleNotFoundError: No module named 'tensorflow'`**
  - MTCNN 사용 시 TensorFlow가 필요합니다.
  - Apple Silicon: `tensorflow-macos`(+`tensorflow-metal`), Intel/일반: `tensorflow-cpu` 설치.

- **`pkg_resources is deprecated` 경고**
  - `mtcnn` 내부에서 발생하는 경고이며 기능에는 영향 없습니다.

- **`PyMuPDF` 설치 실패**
  - `pip install --upgrade pip setuptools wheel` 후 재시도.

---

## 🔐 보안 유의사항

- 로컬 환경에서만 테스트하세요(127.0.0.1). 외부 노출 시 인증/인가, HTTPS, 비밀정보 관리(.env), 로깅 마스킹 등을 반드시 적용하십시오.

---

## 📜 라이선스

MIT (예시). 회사/프로젝트 정책에 맞게 수정하세요.

---

## 🤝 기여

PR/이슈 환영합니다. 재현 가능한 환경 정보(OS/CPU, Python, 패키지 버전, 에러 로그 앞 30~50줄)를 포함해 주세요.
