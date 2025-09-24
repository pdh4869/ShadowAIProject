from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import sqlite3, os, json
from datetime import datetime

app = FastAPI()

# ---- 경로 고정 ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "pii.db")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
COLLECTED_DIR = os.path.join(BASE_DIR, "collected")
os.makedirs(COLLECTED_DIR, exist_ok=True)

templates = Jinja2Templates(directory=TEMPLATE_DIR)

# ---- CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- DB 초기화 ----
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT DEFAULT CURRENT_TIMESTAMP,
            source TEXT,
            type TEXT,
            value TEXT,
            page_url TEXT,
            extra TEXT
        );
    """)
    conn.commit()
    conn.close()

init_db()

# ---- 유틸 ----
def insert_detection_row(ts, source, typ, value, page_url, extra_obj):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO detections (ts, source, type, value, page_url, extra) VALUES (?, ?, ?, ?, ?, ?)",
        (ts, source, typ, value, page_url, json.dumps(extra_obj, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()

def write_jsonl(obj):
    path = os.path.join(COLLECTED_DIR, "detections.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

# ---- 대시보드 ----
def _fetch_items():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, ts, source, type, value, page_url FROM detections ORDER BY id DESC")
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            init_db()
            cur.execute("SELECT id, ts, source, type, value, page_url FROM detections ORDER BY id DESC")
        else:
            raise
    rows = cur.fetchall()
    conn.close()
    return [
        {"id": r[0], "ts": r[1], "source": r[2], "type": r[3], "value": r[4], "page_url": r[5]}
        for r in rows
    ]

@app.get("/", response_class=HTMLResponse)
def dashboard_root(request: Request):
    items = _fetch_items()
    return templates.TemplateResponse("dashboard.html", {"request": request, "items": items})

@app.get("/admin", response_class=HTMLResponse)
def dashboard_admin(request: Request):
    items = _fetch_items()
    return templates.TemplateResponse("dashboard.html", {"request": request, "items": items})

@app.get("/admin/api/detections")
def api_detections():
    items = _fetch_items()
    return JSONResponse({"items": items})

@app.post("/admin/reset")
def reset_detections():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM detections;")
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "cleared"}

# ---- 수집 엔드포인트 ----
@app.post("/collect")
async def collect(payload: dict, background_tasks: BackgroundTasks):
    ts = payload.get("시각") or datetime.utcnow().isoformat()
    page = payload.get("페이지") or ""
    kind = payload.get("종류") or "입력전송"
    items = payload.get("항목들") or []

    if not items:  # 개인정보 없으면 기록 안 함
        return {"status": "skipped", "reason": "no pii detected"}

    # 사람이 읽기 좋은 문자열로 변환
    pretty_value = "\n".join([f"{it.get('유형')} : {it.get('값')}" for it in items])

    log_obj = {
        "ts": ts,
        "page": page,
        "kind": kind,
        "items": items,
        "raw": payload,
        "received_at": datetime.utcnow().isoformat()
    }
    write_jsonl(log_obj)

    background_tasks.add_task(
        insert_detection_row,
        ts, "client", kind, pretty_value, page, payload
    )
    return {"status": "ok"}

# ---- 파일 업로드 메타 엔드포인트 ----
@app.post("/upload_meta")
async def upload_meta(payload: dict, background_tasks: BackgroundTasks):
    ts = payload.get("시각") or datetime.utcnow().isoformat()
    page = payload.get("페이지","")

    log_obj = {
        "ts": ts,
        "page": page,
        "kind": "파일",
        "raw": payload,
        "received_at": datetime.utcnow().isoformat()
    }
    write_jsonl(log_obj)

    background_tasks.add_task(
        insert_detection_row,
        ts, "client", "파일", "파일 업로드", page, payload
    )
    return {"status":"ok"}
