# app.py
import json, sqlite3, datetime, os, platform, subprocess, socket, re
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

# ---- native host (optional) ----
try:
    from native_host import host  # native_host/host.py 존재 가정
except Exception:
    host = None  # import 실패해도 서버는 동작

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
        return os.path.basename(str(data))
    except Exception:
        return os.path.basename(str(raw))

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
    """ipconfig /all에서 IPv4 주소들을 뽑는다 (한글/영문 모두 대응)."""
    ips = []
    try:
        out = subprocess.check_output(["ipconfig", "/all"], encoding="cp437", errors="ignore")
        for line in out.splitlines():
            # 예) "IPv4 주소 . . . . . . . : 192.168.0.64(기본값)"
            #     "IPv4 Address. . . . . . . . . . : 192.168.0.64(Preferred)"
            if ("IPv4" in line) and (":" in line):
                m = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
                if m:
                    ips.append(m.group(1))
    except Exception:
        pass
    # 중복 제거, 사설망/루프백 우선 정렬
    ips = list(dict.fromkeys(ips))
    if ips:
        # 루프백 제외, 169.254 APIPA 제외
        ips = [ip for ip in ips if not ip.startswith(("127.", "169.254."))]
    return ips        

def _get_gateway_dns_windows():
    gw, dns = [], []
    try:
        out = subprocess.check_output(["ipconfig", "/all"], encoding="cp437", errors="ignore")
        lines = out.splitlines()
        # 게이트웨이
        for line in lines:
            if ("기본 게이트웨이" in line) or ("Default Gateway" in line):
                # 같은 줄 또는 다음 줄에 IP가 나옴
                m = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
                if m: gw.append(m.group(1))
        # DNS (같은 줄/다음 줄 연속)
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
                    # 공백 줄/섹션 바뀌면 종료
                    if line.strip() == "" or ":" in line:
                        capture_dns = False
        # 정리
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

    # 2) 폴백: 인터페이스/IP
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

# ---- API ----
@app.post("/api/event")
async def api_event(payload: dict):
    url   = payload.get("source_url") or payload.get("url")
    title = payload.get("page_title") or payload.get("title")
    text  = payload.get("raw_text")  or payload.get("text")
    files = payload.get("files")

    net = safe_gather_network_with_os()
    if not net:
        net = payload.get("network_info") or payload.get("native_meta") or payload.get("network")
        if not isinstance(net, dict):
            net = {"raw": net} if net is not None else {}
        if "os" not in net and "os" in payload:
            net["os"] = payload["os"]

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

# ---- Admin ----
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
            ip = None
            if isinstance(d.get("interfaces"), list) and d["interfaces"]:
                first = d["interfaces"][0]
                if isinstance(first, dict):
                    ips = first.get("ips")
                    if ips:
                        ip = ips[0]
            gw = d.get("gateway")
            dns = d.get("dns")
            parts = []
            if ip:
                parts.append(ip)
            if isinstance(gw, list) and gw:
                parts.append("gw:" + str(gw[0]))
            if isinstance(dns, list) and dns:
                parts.append("dns:" + str(dns[0]))
            return " / ".join(parts) if parts else json.dumps(d, ensure_ascii=False)[:100]
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
        "<div id='overlay' class='overlay' onclick='hidePopup()'></div>",
        "<div id='popup' class='popup'></div>",
        "<table><tr><th>시간</th><th>URL</th><th>LLM</th><th>텍스트</th><th>네트워크 정보</th><th>파일</th><th>OS</th></tr>",
    ]

    for r in rows:
        net_summary = summarize_net(r["network_info"])
        net_full = r["network_info"] or "-"
        files_cell = render_files_cell(r["files"])
        os_cell = render_os_cell(r["network_info"])

        html.append(
            f"<tr>"
            f"<td>{to_kst(r['ts'])}</td>"
            f"<td>{(r['url'] or '-')}</td>"
            f"<td>{llm_from_url(r['url'])}</td>"
            f"<td>{(r['text'] or '-')[:120]}</td>"
            f"<td><a href='#' onclick='showPopup({json.dumps(net_full, ensure_ascii=False)})'>{net_summary}</a></td>"
            f"<td>{files_cell}</td>"
            f"<td>{os_cell}</td>"
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

# ---- dev helper: request log (optional)
# from fastapi import Request
# @app.middleware("http")
# async def log_requests(request: Request, call_next):
#     if request.url.path == "/api/event":
#         body = await request.body()
#         print("[POST /api/event]", body.decode("utf-8", "ignore")[:400])
#     return await call_next(request)

# ---- run on dedicated port ----
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8123)
