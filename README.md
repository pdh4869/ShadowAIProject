# PII Scan Host (Native Messaging + FastAPI Wrapper)

**버전:** 1.3.1-ooxml+ole+pdf-strict

이 프로젝트는 두 가지 방식으로 PII(개인정보) 후보를 스캔합니다.

1) **`host.py` (Native Messaging Host)** — `stdin/stdout`로 길이(4바이트, little-endian) + JSON 메시지를 주고받는 호스트.  
2) **`server.py` (FastAPI HTTP 래퍼)** — 위 `host.py`의 `handle_scan`을 HTTP API로 감싸서 쉽게 호출.

> 지원 기능(요약): 이메일/전화/주민등록번호 후보/사업자등록번호 후보/카드번호 Luhn 검증 등 정규식/휴리스틱 기반 탐지, OOXML(DOCX/XLSX) & OLE(DOC/XLS) 암호파일 감지, PDF 암호 감지(`/Encrypt` 스캔 및 PyPDF2 옵션), 평문 보존하지 않음(옵션: 해시만 반환). 최대 파일 크기 기본값 **25MB**.

---

## 0) 요구사항

- Python 3.9+
- 권장 패키지:
  ```bash
  pip install pdfminer.six python-docx openpyxl regex chardet msoffcrypto-tool olefile PyPDF2
  ```
- **HTTP 서버로 쓸 경우**:
  ```bash
  pip install "fastapi[standard]" uvicorn pydantic
  ```

---

## 1) 빠른 시작 (HTTP API 추천)

### 1-1) 서버 실행
```bash
# (선택) 가상환경
python3 -m venv .venv && source .venv/bin/activate

# 의존성 설치
pip install "fastapi[standard]" uvicorn pydantic
pip install pdfminer.six python-docx openpyxl regex chardet msoffcrypto-tool olefile PyPDF2

# 실행 (server.py와 host.py가 같은 폴더에 있어야 함)
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
# 브라우저: http://localhost:8000/docs (자동 문서)
```

### 1-2) API 스펙

- `GET /health` → 서버/버전 확인
- `POST /scan`
  - 요청(JSON)
    ```jsonc
    {
      "parts": [
        { "filename": "sample.txt", "bytes_base64": "<BASE64>" },
        { "filename": "report.pdf", "bytes_base64": "<BASE64>" }
      ],
      "options": { "include_hashes": false },
      "limits":  { "max_bytes": 26214400 },
      "req_id":  "optional-id"
    }
    ```
  - 응답(JSON)
    ```jsonc
    {
      "ok": true,
      "version": "1.3.1-ooxml+ole+pdf-strict",
      "req_id": "optional-id",
      "summary": {
        "phone": 0, "email": 0, "rrn_candidate": 0, "rrn_valid": 0,
        "bizreg_candidate": 0, "bizreg_valid": 0,
        "card_candidate": 0, "card_luhn": 0,
        "account": 0, "ip": 0, "zip": 0, "dob": 0,
        "secrets_prefix": 0, "secrets_entropy": 0
      },
      "files": [
        {
          "name": "sample.txt",
          "size": 123,
          "sha256": "…",
          "ext": "txt",
          "error": null
        }
      ],
      "errors": [],
      "details": {
        "hashes": { "sha256": ["…"] }
      }
    }
    ```
    - `details.hashes`는 `options.include_hashes=true`일 때 포함됩니다.
    - 암호 걸린 파일은 `files[].error="password_protected"`로 표기됩니다.

#### 예시: `curl`로 호출
```bash
# 파일을 Base64로 읽어 환경변수에 담아 호출 (macOS)
B64=$(base64 -i sample.txt)
curl -sS -X POST http://localhost:8000/scan   -H "Content-Type: application/json"   -d "{
        "parts": [
          {
            "filename": "sample.txt",
            "bytes_base64": "$B64"
          }
        ],
        "options": { "include_hashes": true },
        "limits":  { "max_bytes": 26214400 },
        "req_id":  "demo-1"
      }" | jq .
```

#### 예시: Python 클라이언트
```python
import base64, json, requests

def encode_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")

payload = {
    "parts": [
        {"filename": "sample.txt", "bytes_base64": encode_b64("sample.txt")}
    ],
    "options": {"include_hashes": True},
    "limits": {"max_bytes": 25 * 1024 * 1024},
    "req_id": "py-demo-1"
}

r = requests.post("http://localhost:8000/scan", json=payload, timeout=60)
print(r.status_code, json.dumps(r.json(), ensure_ascii=False, indent=2))
```

---

## 2) `host.py` 직접 사용 (Native Messaging 프로토콜)

브라우저/호스트 통신 규격: **[4바이트 little-endian 길이] + [JSON 바이트]**.  
`host.py`는 JSON 요청 배열이 아니라 **단일 메시지**로 `parts` 목록을 받아 처리합니다.

- **요청 예시(JSON)**
  ```jsonc
  {
    "parts": [
      {"type": "file", "name": "sample.txt", "bytes_base64": "<BASE64>"}
    ],
    "options": {"include_hashes": false},
    "limits":  {"max_bytes": 26214400},
    "req_id":  "optional-id"
  }
  ```

- **테스트 헬퍼 스크립트** (길이 프레임 + JSON 전송)
  ```python
  # send_to_host.py
  import sys, json, struct, base64, subprocess

  def frame(b: bytes) -> bytes:
      return struct.pack("<I", len(b)) + b

  def encode_b64(path: str) -> str:
      return base64.b64encode(open(path, "rb").read()).decode("ascii")

  payload = {
      "parts": [{"type": "file", "name": "sample.txt", "bytes_base64": encode_b64("sample.txt")}],
      "options": {"include_hashes": True},
      "limits":  {"max_bytes": 25*1024*1024},
      "req_id":  "native-demo-1"
  }
  p = subprocess.Popen(["python", "host.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
  msg = json.dumps(payload).encode("utf-8")
  p.stdin.write(frame(msg)); p.stdin.flush()

  # 응답 읽기
  raw_len = p.stdout.read(4)
  n = struct.unpack("<I", raw_len)[0]
  resp = p.stdout.read(n).decode("utf-8")
  print(resp)
  ```

실행:
```bash
python send_to_host.py
```

---

## 3) 설계/제한/보안 고려사항

- **대용량 제한:** 기본 25MB(`MAX_FILE_BYTES`). `limits.max_bytes`로 조정 가능.
- **평문 보존 최소화:** 반환은 카운트/메타/해시 중심. 텍스트 본문은 저장/반환하지 않음.
- **암호 파일 처리:** OOXML/OLE/PDF 암호는 `password_protected`로 표기하고 내용 추출 시도하지 않음.
- **호환 모듈:** 선택 모듈이 설치되지 않은 경우 해당 포맷은 스킵될 수 있음(오류 목록에 기록).
- **확장자 화이트리스트:** txt/csv/md/json/xml/html … (필요 시 코드 내 `FILE_EXT_WHITELIST` 수정).

---

## 4) 개발 팁

- 가상환경 권장: `python3 -m venv .venv && source .venv/bin/activate`
- 형식 검사/정리: `ruff`, `black` 등 도구 사용 권장
- 단위 테스트 예시(추천): `pytest`로 `scan_text`, OOXML/OLE 암호 파일 핸들링 케이스 추가
- 운영 환경: FastAPI + Uvicorn 뒤에 Nginx 리버스 프록시 구성 고려

---

## 5) 라이선스

사내/개인 용도에 맞춰 선택 후 `LICENSE` 파일을 추가하세요.

---

## 6) 변경 이력

- 1.3.1-ooxml+ole+pdf-strict: OOXML/OLE/PDF 암호 감지 강화, 엄격 모드 기본값 유지
