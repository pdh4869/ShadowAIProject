from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import base64, os
from datetime import datetime

# 저장 폴더(서버 실행 디렉토리 기준)
SAVE_DIR = "collected"
os.makedirs(SAVE_DIR, exist_ok=True)

app = FastAPI()

# PoC: CORS 전부 허용(운영에선 도메인/확장ID 화이트리스트 권장)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CollectRequest(BaseModel):
    kind: str                    # "file" | "text"
    name: Optional[str] = None
    mime: Optional[str] = None
    origin_url: Optional[str] = None
    data_b64: Optional[str] = None   # 파일일 때
    text: Optional[str] = None       # 프롬프트일 때

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/collect")
async def collect(req: CollectRequest):
    """
    검사/DB 없음. 받은 걸 디스크에 저장하고 콘솔 로그만 남김.
    """
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    if req.kind == "file" and req.data_b64:
        raw = base64.b64decode(req.data_b64)
        safe_name = (req.name or "unnamed").replace("/", "_")
        path = os.path.join(SAVE_DIR, f"{ts}_{safe_name}")
        with open(path, "wb") as f:
            f.write(raw)
        print(f"[+] FILE  {len(raw)} bytes  -> {path}  from={req.origin_url}")
        return {"ok": True, "saved": path}

    if req.kind == "text" and req.text:
        path = os.path.join(SAVE_DIR, f"{ts}_prompt.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(req.text)
        print(f"[+] TEXT  {len(req.text)} chars -> {path}  from={req.origin_url}")
        return {"ok": True, "saved": path}

    print(f"[!] INVALID payload: {req.dict()}")
    return {"ok": False, "reason": "invalid payload"}
