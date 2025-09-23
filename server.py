# server.py
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import importlib.util
import pathlib

# ---------- host.py 동적 import (server.py와 같은 폴더에 host.py가 있다고 가정)
HERE = pathlib.Path(__file__).resolve().parent
HOST_PATH = HERE / "host.py"
spec = importlib.util.spec_from_file_location("host", str(HOST_PATH))
host = importlib.util.module_from_spec(spec)
assert spec and spec.loader, "host.py를 찾을 수 없습니다. server.py와 같은 폴더에 두세요."
spec.loader.exec_module(host)  # type: ignore

# ---------- FastAPI 앱
app = FastAPI(
    title="PII Scan Host Wrapper",
    version=getattr(host, "VERSION", "dev"),
    description="host.py(handle_scan)를 HTTP로 감싸는 래퍼 서버"
)

# ---------- 요청/응답 모델
class Part(BaseModel):
    filename: Optional[str] = None
    bytes_base64: Optional[str] = Field(
        None, description="파일 내용을 base64 문자열로 전달"
    )

class ScanOptions(BaseModel):
    include_hashes: bool = False

class ScanRequest(BaseModel):
    parts: List[Part]
    options: Optional[ScanOptions] = None
    limits: Optional[Dict[str, Any]] = None
    req_id: Optional[str] = None

@app.get("/health")
def health():
    return {"ok": True, "version": getattr(host, "VERSION", "dev")}

@app.post("/scan")
def scan(req: ScanRequest):
    """
    요청 예시:
    {
      "req_id": "demo-1",
      "options": { "include_hashes": false },
      "parts": [
        { "filename": "sample.txt", "bytes_base64": "..." }
      ],
      "limits": { "max_bytes": 20000000 }
    }
    """
    try:
        # host.py 규격에 맞춰 변환: 반드시 {"type":"file","name","bytes_base64"} 여야 함
        parts_payload: List[Dict[str, Any]] = []
        for p in req.parts:
            if p.bytes_base64:
                parts_payload.append({
                    "type": "file",
                    "name": p.filename or "blob",
                    "bytes_base64": p.bytes_base64
                })
            else:
                # 파일 콘텐츠가 없으면 에러 처리
                raise HTTPException(status_code=400, detail="parts[].bytes_base64 is required")

        include_hashes = bool(req.options.include_hashes) if req.options else False

        # host.py의 핵심 함수 호출
        summary, files_meta, errors, total_hashes = host.handle_scan(
            parts_payload,
            include_hashes=include_hashes
        )

        resp: Dict[str, Any] = {
            "ok": True,
            "version": getattr(host, "VERSION", "dev"),
            "req_id": req.req_id,
            "summary": summary,
            "files": files_meta,
            "errors": errors,
        }
        if include_hashes:
            resp["details"] = {"hashes": total_hashes}
        return resp

    except HTTPException:
        raise
    except Exception as e:
        # host.PasswordProtectedError 등 세분화 필요 시 분기 추가 가능
        raise HTTPException(status_code=500, detail=f"scan failed: {e}")
