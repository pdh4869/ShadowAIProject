# ===== app.py (최종 통합본: 공인 IP 및 지리 정보 수집 적용) =====
import json, sqlite3, datetime, os, platform, subprocess, socket, re, base64 
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware 
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import requests # <--- 공인 IP 수집을 위해 필요

# ---- native host (optional) ----
try:
    import native_host.host as host  
except Exception as e:
    host = None

# ---- 파일 저장 설정 ----
SAVE_DIR = "collected_files"
os.makedirs(SAVE_DIR, exist_ok=True)
print(f"[file] using save dir: {SAVE_DIR}")

# ---- Pydantic 모델 정의 (파일 수집 요청용) ----
class FileCollectRequest(BaseModel):
    kind: str                    # "file"
    name: Optional[str] = None
    mime: Optional[str] = None
    origin_url: Optional[str] = None
    data_b64: Optional[str] = None   # Base64 파일 데이터
    size: Optional[int] = None       # 파일 크기 정보

# ---- display utils: time/LLM/files/OS ----
from datetime import datetime as dt, timezone, timedelta
from urllib.parse import urlparse

KST = timezone(timedelta(hours=9))

VENDOR_MAP = {
    "chat.openai.com": "ChatGPT",
    "chatgpt.com":     "ChatGPT",
    "gemini.google.com": "Google Gemini",
    "claude.ai":       "Claude",
    "poe.com":         "Poe",
}

def to_kst(ts_str: str) -> str:
    try:
        if not ts_str:
            return "-"
        s = ts_str.rstrip("Z")
        base = dt.fromisoformat(s)
        if base.tzinfo is None:
            base = base.replace(tzinfo=timezone.utc)
        return base.astimezone(KST).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ts_str or "-"

def llm_from_url(u: str) -> str:
    if not u:
        return "-"
    h = urlparse(u).netloc.lower()
    if h.startswith("www."):
        h = h[4:]
    for k, v in VENDOR_MAP.items():
        if h.endswith(k):
            return v
    return "기타"

def render_files_cell(raw) -> str:
    if not raw:
        return "-"
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            names = [os.path.basename(str(x)) for x in data if x]
            return "<br/>".join(names) if names else "-"
        return os.path.basename(str(raw))
    except Exception:
        return os.path.basename(str(raw))

def render_ua_cell(js) -> str:
    if not js:
        return "-"
    try:
        d = json.loads(js)
        ua = (d.get("tab") or {}).get("ua")
        if not ua:
            return "-"
        
        return ua
    except Exception:
        return "-"

def render_os_cell(js) -> str:
    if not js:
        return "-"
    try:
        d = json.loads(js)
        osd = d.get("os") or {}
        name = osd.get("name")
        rel  = osd.get("release")
        ver  = osd.get("version")
        mach = osd.get("machine")
        parts = [p for p in [name, rel, ver] if p]
        tail = f" ({mach})" if mach else ""
        return (" ".join(parts) + tail) if parts else "-"
    except Exception:
        return "-"

# ---- DB (separate) ----
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = str(BASE_DIR / "pii_sidecar.db")  # 분리된 DB 파일
print(f"[events] using db: {DB_PATH}")

app = FastAPI()

# ★ CORS 미들웨어 추가 (파일 저장 문제 해결) ★
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 출처 허용
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts TEXT,
      url TEXT,
      title TEXT,
      text TEXT,
      network_info TEXT,
      files TEXT
    )
    """)
    cols = [r[1] for r in cur.execute("PRAGMA table_info(events)").fetchall()]
    if "network_info" not in cols:
        cur.execute("ALTER TABLE events ADD COLUMN network_info TEXT")
    if "files" not in cols:
        cur.execute("ALTER TABLE events ADD COLUMN files TEXT")
    conn.commit()
    conn.close()

init_db()

# ---- network fallbacks ----
def _get_public_ip_geo():
    """외부 API를 통해 공인 IP 및 지리 정보(국가 코드/이름)를 가져옵니다."""
    try:
        # ipapi.co API 사용
        response = requests.get('https://ipapi.co/json/', timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                "public_ip": data.get("ip"),
                "country_code": data.get("country_code"),
                "country_name": data.get("country_name")
            }
    except Exception as e:
        print(f"[Network] Failed to get public IP geo: {e}")
    return {}


def _get_local_ipv4():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return None
        
def _get_ipv4s_from_ipconfig():
    ips = []
    try:
        out = subprocess.check_output(["ipconfig", "/all"], encoding="cp437", errors="ignore")
        for line in out.splitlines():
            if ("IPv4" in line) and (":" in line):
                m = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
                if m:
                    ips.append(m.group(1))
    except Exception:
        pass
    ips = list(dict.fromkeys(ips))
    if ips:
        ips = [ip for ip in ips if not ip.startswith(("127.", "169.254."))]
    return ips        

def _get_gateway_dns_windows():
    gw, dns = [], []
    try:
        out = subprocess.check_output(["ipconfig", "/all"], encoding="cp437", errors="ignore")
        lines = out.splitlines()
        for line in lines:
            if ("기본 게이트웨이" in line) or ("Default Gateway" in line):
                m = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
                if m: gw.append(m.group(1))
        capture_dns = False
        for line in lines:
            if ("DNS 서버" in line) or ("DNS Servers" in line):
                capture_dns = True
                m = re.findall(r"(\d+\.\d+\.\d+\.\d+)", line)
                dns.extend(m)
                continue
            if capture_dns:
                m = re.findall(r"(\d+\.\d+\.\d+\.\d+)", line)
                if m:
                    dns.extend(m)
                else:
                    if line.strip() == "" or ":" in line:
                        capture_dns = False
        gw  = list(dict.fromkeys(gw))
        dns = [d for d in dict.fromkeys(dns) if not d.startswith("0.0.0.")]
    except Exception:
        pass
    return gw or None, dns or None

def _get_gateway_dns_linux():
    gw, dns = [], []
    try:
        out = subprocess.check_output(["ip", "route"], encoding="utf-8", errors="ignore")
        for line in out.splitlines():
            if line.startswith("default via "):
                m = re.search(r"default via (\d+\.\d+\.\d+\.\d+)", line)
                if m: gw.append(m.group(1))
    except Exception:
        pass
    try:
        if os.path.exists("/etc/resolv.conf"):
            with open("/etc/resolv.conf", "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.strip().startswith("nameserver"):
                        m = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
                        if m: dns.append(m.group(1))
    except Exception:
        pass
    return gw or None, dns or None

def safe_gather_network_with_os():
    os_info = {
        "name": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
    }
    net = {}
    
    # ★ 공인 IP 및 지리 정보 수집 로직 추가 ★
    public_geo_data = _get_public_ip_geo()
    if public_geo_data.get("public_ip"):
        net.update(public_geo_data) # public_ip, country_code, country_name 추가
        
    # 1) native_host 우선
    try:
        if host and hasattr(host, "gather_network_info"):
            n = host.gather_network_info()
            if isinstance(n, dict):
                net.update(n)
            elif n is not None:
                net["raw"] = n
    except Exception as e:
        print("[native_host] gather_network_info error:", e)

    # 2) 폴백: 인터페이스/IP (사설 IP)
    if "interfaces" not in net or not net.get("interfaces"):
        ip = None
        if platform.system().lower().startswith("win"):
            ipv4s = _get_ipv4s_from_ipconfig()
            if ipv4s:
                ip = ipv4s[0]
        if not ip:
            ip = _get_local_ipv4()
        if ip:
            net["interfaces"] = [{"name": "primary", "ips": [ip]}]

    # 3) 폴백: gateway/DNS
    if platform.system().lower().startswith("win"):
        gw, dns = _get_gateway_dns_windows()
    else:
        gw, dns = _get_gateway_dns_linux()
    if "gateway" not in net or not net.get("gateway"):
        if gw: net["gateway"] = gw
    if "dns" not in net or not net.get("dns"):
        if dns: net["dns"] = dns

    net["os"] = os_info
    return net

# ---- API: 파일 내용 저장 엔드포인트 ----
@app.post("/api/file_collect")
async def api_file_collect(req: FileCollectRequest):
    """
    Base64 파일을 받아 디코딩하여 로컬 디스크에 저장합니다.
    """
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    if req.kind == "file" and req.data_b64:
        try:
            raw = base64.b64decode(req.data_b64)
            safe_name = (req.name or "unnamed").replace("/", "_")
            # 경로: collected_files/타임스탬프_파일명
            path = os.path.join(SAVE_DIR, f"{ts}_{safe_name}")
            with open(path, "wb") as f:
                f.write(raw)
            print(f"[+] FILE  {len(raw)} bytes saved -> {path}  from={req.origin_url}")
            return {"ok": True, "saved": path}
        except Exception as e:
            print(f"[!] FILE SAVE ERROR: {e}") 
            return {"ok": False, "reason": f"file save error: {str(e)}"}
    
    print(f"[!] INVALID file payload: {req.dict()}")
    return {"ok": False, "reason": "invalid payload"}


# ---- API: 메타데이터 DB 저장 엔드포인트 ----
@app.post("/api/event")
async def api_event(payload: dict):
    url   = payload.get("source_url") or payload.get("url")
    title = payload.get("page_title") or payload.get("title")
    text  = payload.get("raw_text")  or payload.get("text")
    files = payload.get("files")
    tab   = payload.get("tab") 

    net = safe_gather_network_with_os()
    if not net:
        net = payload.get("network_info") or payload.get("native_meta") or payload.get("network")
        if not isinstance(net, dict):
            net = {"raw": net} if net is not None else {}
        if "os" not in net and "os" in payload:
            net["os"] = payload["os"]
            
    if tab:
        net["tab"] = tab

    ts = datetime.datetime.utcnow().isoformat() + "Z"
    net_s = json.dumps(net, ensure_ascii=False) if net is not None else None
    files_s = (
        json.dumps(files, ensure_ascii=False)
        if isinstance(files, (list, dict))
        else (files if isinstance(files, str) else None)
    )

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO events (ts, url, title, text, network_info, files) VALUES (?,?,?,?,?,?)",
        (ts, url, title, text, net_s, files_s)
    )
    conn.commit()
    conn.close()
    return {"ok": True}

# ---- Admin (대시보드) ----
@app.get("/admin", response_class=HTMLResponse)
async def admin():
    conn = get_conn()
    rows = conn.execute(
        "SELECT ts,url,title,text,network_info,files FROM events ORDER BY id DESC LIMIT 200"
    ).fetchall()
    conn.close()

    def summarize_net(js):
        if not js:
            return "-"
        try:
            d = json.loads(js)
            ip_parts = []
            
            # 1. 공인 IP 및 국가 정보 추가 (수정됨)
            public_ip = d.get("public_ip")
            country_code = d.get("country_code")
            country_name = d.get("country_name")

            if public_ip:
                 geo_info = f"({country_code} {country_name})" if country_code and country_name else ""
                 ip_parts.append(f"Public: {public_ip} {geo_info}".strip())
            
            # 2. 사설 IP 추가 (기존 로직 유지)
            local_ip = None
            if isinstance(d.get("interfaces"), list) and d["interfaces"]:
                first = d["interfaces"][0]
                if isinstance(first, dict):
                    ips = first.get("ips")
                    if ips:
                        local_ip = ips[0]
            if local_ip:
                ip_parts.append(local_ip)
                
            gw = d.get("gateway")
            dns = d.get("dns")
            parts = []
            if ip_parts:
                parts.append(" / ".join(ip_parts))

            if isinstance(gw, list) and gw:
                parts.append("gw:" + str(gw[0]))
            if isinstance(dns, list) and dns:
                parts.append("dns:" + str(dns[0]))
                
            return " | ".join(parts) if parts else json.dumps(d, ensure_ascii=False)[:100]
        except Exception:
            return str(js)[:100]

    html = [
        "<html><head><meta charset='utf-8'><title>탐지 이벤트 로그</title>",
        "<style>",
        "table{border-collapse:collapse;width:100%}",
        "th,td{border:1px solid #ddd;padding:8px;vertical-align:top}",
        "th{background:#f5f5f5}",
        ".popup{position:fixed;top:10%;left:10%;width:80%;height:80%;background:#fff;border:2px solid #333;padding:10px;overflow:auto;z-index:1000;display:none}",
        ".overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:999;display:none}",
        "td a{word-break:break-all}",
        "</style>",
        "</head><body><h2>탐지 이벤트 로그</h2>",
        "<p>파일 내용은 서버 실행 폴더의 <b>collected_files</b> 폴더에 저장됩니다.</p>", 
        "<div id='overlay' class='overlay' onclick='hidePopup()'></div>",
        "<div id='popup' class='popup'></div>",
        "<table><tr><th>시간</th><th>URL</th><th>LLM</th><th>텍스트</th><th>네트워크 정보</th><th>OS</th><th>User-Agent</th><th>파일</th></tr>",
    ]

    for r in rows:
        net_summary = summarize_net(r["network_info"])
        net_full = r["network_info"] or "-"
        files_cell = render_files_cell(r["files"])
        os_cell = render_os_cell(r["network_info"])
        ua_cell = render_ua_cell(r["network_info"])

        html.append(
            f"<tr>"
            f"<td>{to_kst(r['ts'])}</td>"
            f"<td>{(r['url'] or '-')}</td>"
            f"<td>{llm_from_url(r['url'])}</td>"
            f"<td>{(r['text'] or '-')[:120]}</td>"
            f"<td><a href='#' onclick='showPopup({json.dumps(net_full, ensure_ascii=False)})'>{net_summary}</a></td>"
            f"<td>{os_cell}</td>"      
            f"<td>{ua_cell}</td>"      
            f"<td>{files_cell}</td>"
            f"</tr>"
        )

    html.append("</table>")
    html.append("""
    <script>
    function showPopup(content){
        document.getElementById('overlay').style.display='block';
        document.getElementById('popup').style.display='block';
        try{
            let parsed = JSON.parse(content);
            document.getElementById('popup').innerText = JSON.stringify(parsed, null, 2);
        }catch(e){
            document.getElementById('popup').innerText = content;
        }
    }
    function hidePopup(){
        document.getElementById('overlay').style.display='none';
        document.getElementById('popup').style.display='none';
        document.getElementById('popup').innerText = "";
    }
    </script>
    </body></html>
    """)
    return "".join(html)

# ---- run on dedicated port ----
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8123)