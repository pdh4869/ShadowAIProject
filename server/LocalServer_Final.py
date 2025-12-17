# =============================
# File: LocalServer_Final.py (JSON 직렬화 오류 수정 버전)
# Desc: float32 타입 JSON 변환 오류를 해결하기 위해 사용자 정의 JSON 인코더를 추가했습니다.
#       이제 NER 모델의 신뢰도 점수(score)가 포함된 탐지 결과도 정상적으로 처리됩니다.
# =============================
import uvicorn
import base64
import secrets
import hmac
import hashlib
import time
import logging
import json
import os
import re
import numpy as np
import requests
from collections import deque, Counter

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# 동일 디렉토리의 Logic_Final 에서 import
from Logic_Final import (
    handle_input_raw,
    detect_by_ner,
    detect_by_regex,
    detect_quasi_identifiers,
    analyze_combination_risk,
    mask_pii_in_filename,
)

# 로거 및 포맷터 기본 설정(정의되지 않은 fmt/logger 참조 문제 해결)
logger = logging.getLogger('pii_server')
logger.setLevel(logging.INFO)
fmt = logging.Formatter('[%(levelname)s] %(message)s')
sh = logging.StreamHandler()
sh.setLevel(logging.INFO)
sh.setFormatter(fmt)
logger.addHandler(sh)
try:
    fh = logging.FileHandler('server_debug.log', encoding='utf-8')
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
except Exception:
    # 파일 핸들러 생성 실패 시에도 동작에 지장 없도록 무시
    logging.warning('[WARN] server_debug.log 파일 핸들러를 생성할 수 없습니다. 콘솔로만 기록됩니다.')
    # ensure at least console handler is present and set to INFO
    sh.setLevel(logging.INFO)

# --- [오류 수정] ---
# NumPy 데이터 타입을 Python 기본 타입으로 변환하는 사용자 정의 JSON 인코더
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)

# 보안: Extension ID 화이트리스트
ALLOWED_EXTENSION_ID = os.getenv("ALLOWED_EXTENSION_ID", "hblalecgjndcjeaineacembpdfmmjaoa")
ALLOWED_ORIGINS = [f"chrome-extension://{ALLOWED_EXTENSION_ID}"]

# 인증 토글 (true면 HMAC 인증 필요)
REQUIRE_AUTH = os.getenv("PII_REQUIRE_AUTH", "false").lower() == "true"
if REQUIRE_AUTH:
    API_SECRET = os.getenv("PII_API_SECRET", secrets.token_hex(32))
    logging.info("[SECURITY] ✓ 인증 활성화")
else:
    API_SECRET = None
    logging.warning("[SECURITY] ⚠ 인증 비활성화 (개발 모드)")

# 파일 크기 제한
SOFT_LIMIT = 20 * 1024 * 1024   # 20MB
HARD_LIMIT = 100 * 1024 * 1024  # 100MB

app = FastAPI()

# 최근 로그 저장 (메모리)
detection_history = deque(maxlen=1000)

# Dashboard forwarding 설정
DASHBOARD_URL = os.getenv('DASHBOARD_URL', 'http://127.0.0.1:5000/api/log-pii')
DASHBOARD_REQUIRE_AUTH = os.getenv('DASHBOARD_REQUIRE_AUTH', 'false').lower() == 'true'
DASHBOARD_API_SECRET = os.getenv('DASHBOARD_API_SECRET', '')

def send_to_dashboard(payload: dict, timeout: int = 5) -> dict:
    headers = {'Content-Type': 'application/json'}
    max_retries = 2
    for attempt in range(0, max_retries + 1):
        try:
            if DASHBOARD_REQUIRE_AUTH and DASHBOARD_API_SECRET:
                ts = str(int(time.time() * 1000))
                token = hmac.new(DASHBOARD_API_SECRET.encode(), ts.encode(), hashlib.sha256).hexdigest()
                headers['X-Auth-Token'] = token
                headers['X-Timestamp'] = ts

            resp = requests.post(DASHBOARD_URL, json=payload, headers=headers, timeout=timeout)
            # Try to parse JSON body if possible
            body = None
            try:
                body = resp.json()
            except Exception:
                body = None

            # Treat non-2xx as error
            if resp.status_code >= 400:
                # If last attempt, inspect for duplicate-type DB errors and treat as ignored success
                err_text = (body or resp.text or "")
                if attempt >= max_retries and isinstance(err_text, (str,)) and ("Duplicate entry" in err_text or "IntegrityError" in err_text):
                    logging.warning(f"[WARN] 대시보드 중복 삽입 오류 무시: {resp.status_code} - {err_text}")
                    return {'status': 'ok_ignored_duplicate', 'code': resp.status_code, 'body': body or resp.text}

                logging.error(f"[ERROR] 대시보드 응답 코드 오류 (attempt {attempt}): {resp.status_code} - {resp.text}")
                # short backoff before retry
                if attempt < max_retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                return {'status': 'error', 'code': resp.status_code, 'body': body or resp.text}

            # If dashboard returns a JSON with status:'error', surface it as error
            if isinstance(body, dict) and body.get('status') == 'error':
                logging.error(f"[ERROR] 대시보드 내부 오류 응답: {body}")
                # If last attempt and internal error mentions IntegrityError, ignore similarly
                if attempt >= max_retries and any(k in str(body) for k in ("IntegrityError", "Duplicate entry")):
                    logging.warning(f"[WARN] 대시보드 내부 오류(중복) 무시: {body}")
                    return {'status': 'ok_ignored_duplicate', 'code': resp.status_code, 'body': body}
                if attempt < max_retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                return {'status': 'error', 'code': resp.status_code, 'body': body}

            return {'status': 'ok', 'code': resp.status_code, 'body': body or resp.text}

        except Exception as e:
            logging.error(f"[ERROR] 대시보드 전송 실패 (attempt {attempt}): {e}")
            if attempt < max_retries:
                time.sleep(0.5 * (attempt + 1))
                continue
            return {'status': 'error', 'error': str(e)}


def _forward_payload_for_items(pii_items, file_type_name=None, filename=None, network_info=None, url=None, status='success', llm_type_name=None, validation_statuses=None, tab=None, reason=None, comb=None):
    """Build a payload compatible with the dashboard Flask API (PiiLog schema).

    - filters out items of type 'LC' (address-only)
    - returns None if nothing should be forwarded
    """
    # 필터: 주소(LC)만 있는 경우는 전송하지 않음
    forwarded = [i for i in pii_items if i.get('type') != 'LC']
    if not forwarded:
        return None

    types = [i.get('type') for i in forwarded if i.get('type')]
    # Normalize types to strings and preserve order while making unique
    # normalize to lowercase to match backend canonical names
    norm_types = [str(t).lower() for t in types]
    unique_types = list(dict.fromkeys(norm_types))
    counts = {str(k).lower(): int(v) for k, v in Counter(norm_types).items()}

    ip = None
    user_agent = None
    os_info = None
    hostname = None
    if isinstance(network_info, dict):
        ip = network_info.get('ip') or network_info.get('ip_address') or None
        user_agent = network_info.get('user_agent') or network_info.get('ua') or None
        os_info = network_info.get('os') or network_info.get('os_info') or None
        hostname = network_info.get('hostname') or None

    # Ensure required minimal fields
    if not file_type_name:
        file_type_name = 'unknown'
    if not ip:
        # prefer url host if available, else loopback
        ip = '127.0.0.1'

    payload = {
        'file_type_name': file_type_name,
        'filename': filename,
        'llm_type_name': llm_type_name,
        'tab': tab,
        'status': 'success' if status == 'success' else ('failure' if status == 'failure' else status),
        'reason': reason,
        'session_url': url,
        'user_agent': user_agent,
        'os_info': os_info,
        'hostname': hostname,
        'ip_address': ip,
        'validation_statuses': validation_statuses,
        'pii_types': unique_types,
        'pii_type_counts': counts,
    }
    # Include combination risk metadata separately (do not treat as a detection item)
    if comb:
        try:
            payload['combination_risk'] = comb
        except Exception:
            payload['combination_risk'] = str(comb)
    # Log as warning to increase chance of visibility in case file handler was not created
    logging.warning(f"[PAYLOAD] {json.dumps(payload, default=str, ensure_ascii=False)}")
    return payload


def _normalize_and_filter_detections(detected):
    """Normalize detection types and filter out items that should not be shown on dashboard.

    - Normalize legacy 'OG' -> 'ORG'
    - Remove internal-only items like 'combination_risk'
    - Deduplicate by (type, normalized value)
    """
    if not detected:
        return []
    out = []
    seen = set()
    for it in detected:
        t = it.get('type')
        v = it.get('value', '')
        # Normalize OG -> ORG to avoid duplicate org entries
        if t == 'OG':
            t = 'ORG'
            it['type'] = 'ORG'

        # Skip combination risk entries entirely (internal-only)
        if t == 'combination_risk':
            continue

        # Normalize value for deduping (strip spaces, lowercase)
        try:
            norm_v = re.sub(r"\s+", "", str(v)).lower()
        except Exception:
            norm_v = str(v)

        key = (t, norm_v)
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def _parse_user_agent_for_os(ua: str):
    """Very small UA heuristic to infer OS when explicit os_info is missing."""
    if not ua or not isinstance(ua, str):
        return None
    ua = ua.lower()
    if 'windows nt 10' in ua or 'windows nt 10.0' in ua:
        return 'Windows 10'
    if 'windows nt 11' in ua or 'windows nt 10.1' in ua:
        return 'Windows 11'
    if 'mac os x' in ua or 'macintosh' in ua:
        return 'macOS'
    if 'linux' in ua:
        return 'Linux'
    if 'android' in ua:
        return 'Android'
    if 'iphone' in ua or 'ipad' in ua or 'ios' in ua:
        return 'iOS'
    return None


def infer_llm_from_url(url: str):
    """Infer LLM name from a URL string using simple heuristics.

    Returns a short name like 'ChatGPT', 'Gemini', 'Claude', 'Bard', or None if unknown.
    """
    if not url or not isinstance(url, str):
        logging.info(f"infer_llm_from_url: no url provided")
        return None
    u = url.lower()
    logging.info(f"infer_llm_from_url: checking url={u}")
    # common patterns
    if 'chatgpt' in u or 'openai' in u or 'openai.com' in u:
        return 'ChatGPT'
    if 'google' in u or 'gemini' in u or 'assistant.google' in u or 'bard' in u:
        # prefer Gemini for google-hosted LLM endpoints
        if 'gemini' in u:
            return 'Gemini'
        if 'bard' in u:
            return 'Bard'
        return 'Gemini'
    if 'anthropic' in u or 'claude' in u:
        return 'Claude'
    if 'cohere' in u:
        return 'Cohere'
    if 'ai21' in u:
        return 'AI21'
    if 'huggingface' in u or 'hf.co' in u:
        return 'HuggingFace'
    # generic provider hints
    if 'azure' in u and 'openai' in u:
        return 'AzureOpenAI'
    logging.info(f"infer_llm_from_url: no match for url={u}")
    return None


def build_merged_metadata(data: dict, request: Request):
    """Return (merged_net, llm_type, tab) ensuring user_agent, os_info and tab.llm are filled when possible."""
    network_info = data.get('network_info') or {}
    tab = data.get('tab') or {}
    header_ua = request.headers.get('user-agent') if request else None

    merged_net = dict(network_info or {})
    # Determine user_agent with fallbacks
    ua = merged_net.get('user_agent') or merged_net.get('ua') or tab.get('ua') or header_ua
    merged_net['user_agent'] = ua

    # Determine os_info: explicit fields or infer from UA
    os_info = merged_net.get('os_info') or merged_net.get('os') or tab.get('os') or _parse_user_agent_for_os(ua)
    # default to 'Unknown' rather than None so UI/display always has a value
    merged_net['os_info'] = os_info or 'Unknown'

    # Normalize ip/hostname fields
    merged_net['ip'] = merged_net.get('ip') or merged_net.get('ip_address') or None
    merged_net['hostname'] = merged_net.get('hostname') or None

    # llm type: prefer explicit top-level keys, fallback to tab.llm
    llm_type = data.get('llm_type_name') or data.get('llm') or tab.get('llm') or None
    # Try to infer from URL if still unknown
    if not llm_type or llm_type == 'unknown':
        # check common URL fields in payload
        url_candidates = [data.get('url'), data.get('origin_url'), data.get('session_url')]
        logging.info(f"build_merged_metadata: url_candidates={url_candidates}")
        inferred = None
        for u in url_candidates:
            inferred = infer_llm_from_url(u)
            logging.info(f"build_merged_metadata: infer for {u} -> {inferred}")
            if inferred:
                llm_type = inferred
                break
    # default llm string so UI and forwarding always include a value
    if not llm_type:
        llm_type = 'unknown'
    # Ensure tab.llm is populated so local UI (which reads tab.llm) always sees it
    tab = dict(tab or {})
    tab['llm'] = tab.get('llm') or llm_type

    return merged_net, llm_type, tab

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Auth-Token", "X-Timestamp"],
)

# 인증 검사
def verify_auth(request: Request) -> bool:
    if not REQUIRE_AUTH:
        return True
    token = request.headers.get("X-Auth-Token", "")
    ts = request.headers.get("X-Timestamp", "")
    if not token or not ts:
        return False
    try:
        req_time = int(ts)
        now_ms = int(time.time() * 1000)
        if abs(now_ms - req_time) > 300000:  # 5분
            logging.warning(f"[SECURITY] 타임스탬프 만료: {abs(now_ms-req_time)}ms")
            return False
    except:
        return False
    expected = hmac.new(API_SECRET.encode(), ts.encode(), hashlib.sha256).hexdigest()
    return secrets.compare_digest(token, expected)

@app.get("/")
def root():
    return {"message": "PII Detection Server Running", "status": "ok"}

@app.get("/dashboard")
async def dashboard():
    # 대시보드 HTML 코드는 변경 없이 그대로 유지됩니다.
    html = r"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>개인정보 탐지 모니터</title>
      <style>
        * { box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background:#0f172a; color:#fff; padding:20px; }
        .header { background:linear-gradient(135deg,#667eea 0%,#764ba2 100%); padding:40px; border-radius:20px; margin-bottom:30px; text-align:center; }
        h1 { font-size:2.4rem; margin:0 0 12px; }
        .status { display:inline-block; background:#10b981; padding:8px 18px; border-radius:999px; font-weight:600; }
        .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:20px; margin:24px 0; }
        .card { background:#1e293b; border:2px solid #334155; border-radius:14px; padding:22px; }
        .card h2 { color:#8da2fb; font-size:1.2rem; margin-bottom:12px; }
        .metric { font-size:3rem; font-weight:800; color:#10b981; }
        .list { line-height:2; color:#cbd5e1; }
        .list li::before { content:'✓ '; color:#10b981; }
        .realtime { background:#1e293b; border:2px solid #334155; border-radius:14px; padding:22px; }
        .log-entry { background:#0f172a; border-left:4px solid #10b981; margin:10px 0; padding:12px; border-radius:8px; }
        .log-entry.face { border-left-color:#f59e0b; }
        .log-time { color:#94a3b8; font-size:0.9rem; }
        .type { display:inline-block; background:#667eea; padding:2px 10px; border-radius:12px; margin-right:8px; font-size:0.85rem; }
        .status-valid { color:#10b981; font-weight:700; margin-left:6px; }
        .status-invalid { color:#f59e0b; margin-left:6px; }
        .netinfo { color:#94a3b8; font-size:0.85rem; margin-top:6px; }
        .empty { color:#64748b; text-align:center; padding:36px; }
      </style>
      <script>
        function escapeHtml(t){const d=document.createElement('div');d.textContent=t;return d.innerHTML}
        function parseUA(ua){let b='Unknown',o='Unknown'; if(ua.includes('Chrome')) b='Chrome '+(ua.match(/Chrome\/(\d+)/)||[])[1]; else if(ua.includes('Firefox')) b='Firefox '+(ua.match(/Firefox\/(\d+)/)||[])[1]; else if(ua.includes('Safari')&&!ua.includes('Chrome')) b='Safari'; if(ua.includes('Windows NT 10.0')) o='Windows 10'; else if(ua.includes('Windows NT 11.0')) o='Windows 11'; else if(ua.includes('Mac OS X')) o='macOS'; else if(ua.includes('Linux')) o='Linux'; return {browser:b, os:o}}
        async function fetchDetections(){
          try{
            const r = await fetch('/api/detections');
            const data = await r.json();
            document.getElementById('total-count').textContent = data.total_detections||0;
            const box = document.getElementById('logs');
            if(data.detections && data.detections.length){
              box.innerHTML = data.detections.map(d=>{
                if(d.type==='group' && d.items){
                  return `<div class="log-entry"><div class="log-time">${new Date(d.timestamp).toLocaleString('ko-KR')} - ${d.items.length}개 탐지</div>`+
                    d.items.map(it=>`<div style="margin:4px 0"><span class="type">${escapeHtml(it.type)}</span><strong>${escapeHtml(it.value||'')}</strong>${it.status? (it.status==='valid'?'<span class="status-valid">(valid)</span>':`<span class="status-invalid">(${escapeHtml(it.status)})</span>`):''}</div>`).join('')+
                    `${d.file_name?`<div class="netinfo">파일명: ${escapeHtml(d.file_name)}</div>`:''}`+
                    `${d.url?`<div class="netinfo">출처: ${d.url}</div>`:''}`+
                    `${d.network_info&&d.network_info.ip?`<div class="netinfo">IPs: ${d.network_info.ip}</div>`:''}`+
                    `${d.network_info&&d.network_info.hostname?`<div class="netinfo">컴퓨터: ${d.network_info.hostname}</div>`:''}`+
                    `${d.tab&&d.tab.ua?(()=>{const i=parseUA(d.tab.ua);return `<div class=\"netinfo\">Browser: ${i.browser}</div><div class=\"netinfo\">OS: ${i.os}</div>`})():''}`+
                  `</div>`
                }
                return `<div class="log-entry ${d.type==='image_face'?'face':''}"><div class="log-time">${new Date(d.timestamp).toLocaleString('ko-KR')}</div><div><span class="type">${escapeHtml(d.type)}</span><strong>${escapeHtml(d.value||'(파일)')}</strong>${d.status?(d.status==='valid'?'<span class="status-valid">(valid)</span>':`<span class="status-invalid">(${escapeHtml(d.status)})</span>`):''}</div>${d.file_name?`<div class=\"netinfo\">파일명: ${escapeHtml(d.file_name)}</div>`:''}${d.url?`<div class=\"netinfo\">출처: ${d.url}</div>`:''}${d.network_info&&d.network_info.ip?`<div class=\"netinfo\">IPs: ${d.network_info.ip}</div>`:''}${d.network_info&&d.network_info.hostname?`<div class=\"netinfo\">컴퓨터: ${d.network_info.hostname}</div>`:''}${d.tab&&d.tab.ua?(()=>{const i=parseUA(d.tab.ua);return `<div class=\"netinfo\">Browser: ${i.browser}</div><div class=\"netinfo\">OS: ${i.os}</div>`})():''}</div>`
              }).join('');
            }else{
              box.innerHTML = '<div class="empty">아직 탐지된 내역이 없습니다.</div>'
            }
          }catch(e){console.error(e)}
        }
        setInterval(fetchDetections, 3000);
        window.addEventListener('DOMContentLoaded', fetchDetections);
      </script>
    </head>
    <body>
      <div class="header">
        <h1>🛡️ 개인정보 탐지 모니터</h1>
        <div class="status">● 실시간 모니터링 중</div>
      </div>
      <div class="grid">
        <div class="card"><h2>📊 총 탐지 건수</h2><div class="metric" id="total-count">0</div></div>
        <div class="card"><h2>🔍 탐지 항목</h2><ul class="list"><li>전화번호</li><li>이메일</li><li>주민등록번호</li><li>카드번호</li><li>계좌번호</li><li>인명 (NER)</li><li>얼굴 이미지</li></ul></div>
        <div class="card"><h2>📁 지원 파일</h2><ul class="list"><li>PDF</li><li>DOCX</li><li>TXT</li><li>이미지 (PNG/JPG 등)</li><li>HWP/HWPX, PPT/PPTX, XLS/XLSX</li></ul></div>
      </div>
      <div class="realtime">
        <h2>🔴 실시간 탐지 내역 (최근 50개)</h2>
        <div id="logs"><div class="empty">데이터 로딩 중...</div></div>
      </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.post("/api/file_collect")
async def handle_file_collect(request: Request):
    if not verify_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        data = await request.json()
        file_name = data.get("name", "unknown")
        file_b64 = data.get("data_b64", "")
        network_info = data.get("network_info", {})
        origin_url = data.get("origin_url", "")
        processed_at = data.get("processed_at", "")
        # header fallback
        header_ua = request.headers.get('user-agent') if request else None

        if not file_b64:
            return JSONResponse(content={"status":"에러","message":"파일 데이터 없음"}, status_code=400)

        est = len(file_b64) * 3 // 4
        if est > HARD_LIMIT:
            return JSONResponse(content={"status":"에러", "message":f"파일이 너무 큽니다 (최대 {HARD_LIMIT // 1024 // 1024}MB)"}, status_code=413)
        if est > SOFT_LIMIT:
            logging.warning(f"큰 파일 처리 중: {est/1024/1024:.1f}MB - {file_name}")

        if not file_name or not isinstance(file_name, str):
            logging.error(f"잘못된 파일명(name)을 수신했습니다: {file_name}")
            return JSONResponse(content={"status":"에러","message":"잘못된 파일명"}, status_code=400)

        file_name = file_name.strip()
        extension = file_name.split('.')[-1].lower() if '.' in file_name else ""
        logging.info(f"파일 수신: '{file_name}' ({est/1024:.1f}KB), 출처: {origin_url}, 추출된 확장자: '{extension}'")

        masked_name, pii_type = mask_pii_in_filename(file_name)
        display_name = masked_name if masked_name != file_name else file_name
        if pii_type:
            logging.info(f"✓ 파일명 탐지: {pii_type} in '{display_name}'")

            file_bytes = base64.b64decode(file_b64)
            detected, masked_filename, backend_status, image_detections, comb = handle_input_raw(file_bytes, extension, file_name)

        if detected:
            # build merged metadata consistently
            merged_net, llm_type, tab = build_merged_metadata(data, request)

            detection_history.append({
                "timestamp": processed_at,
                "type": "group",
                "items": detected,
                "url": origin_url,
                "network_info": merged_net,
                "file_name": display_name,
                "original_file_name": file_name if display_name!=file_name else None,
                "tab": tab,
                "combination_risk": comb
            })
            for it in detected:
                st = f" [{it.get('status')}]" if 'status' in it else ""
                logging.info(f"✓ 파일 탐지: {it.get('type')} = {it.get('value')}{st}")

            # Determine status and optional reason when parse failed
            forward_status = 'success'
            forward_reason = None
            if not backend_status:
                forward_status = 'failure'
            # if parse returned explicit parse error item, include reason
            for it in detected:
                if it.get('type') == 'file_parse_error':
                    forward_status = 'failure'
                    forward_reason = it.get('value')
                    break

            # Forward summary to dashboard (skip LC addresses)
            # Forward masked/display name instead of original filename to avoid leaking PII in dashboard
            payload = _forward_payload_for_items(detected, file_type_name=extension or 'unknown', filename=display_name, network_info=merged_net, url=origin_url or None, llm_type_name=llm_type, tab=tab, status=forward_status, reason=forward_reason, comb=comb)
            if payload:
                res = send_to_dashboard(payload)
                logging.info(f"대시보드 전송 결과: {res}")

        return JSONResponse(content={"result":{"status":"처리 완료"}}, status_code=200)
    except Exception as e:
        logging.error(f"파일 처리 실패: {e}", exc_info=True)
        return JSONResponse(content={"status":"에러","message":str(e)}, status_code=500)

@app.post("/api/event")
async def handle_text_event(request: Request):
    if not verify_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        data = await request.json()
        text = data.get("text", "")
        url = data.get("url", "")
        network_info = data.get("network_info", {})
        processed_at = data.get("processed_at", "")
        header_ua = request.headers.get('user-agent') if request else None

        logging.info("========== 텍스트 이벤트 수신 ==========")
        logging.info(f"URL: {url}")
        logging.info(f"네트워크 정보: {network_info}")
        logging.info(f"텍스트 길이: {len(text)} 글자")

        if not text.strip():
            return JSONResponse(content={"result":{"status":"텍스트 없음"}}, status_code=200)

        ner_results   = detect_by_ner(text)
        regex_results = detect_by_regex(text)
        quasi_results = detect_quasi_identifiers(text)
        all_detected = regex_results + ner_results + quasi_results
        comb = analyze_combination_risk(all_detected, text)
        # comb (combination risk) is kept as separate metadata and NOT appended
        # into the detection items list. Keep all_detected for internal audit,
        # but filter out noisy types for forwarding when no comb is present.
        if comb:
            detected = list(all_detected)
        else:
            detected = [i for i in all_detected if i.get('type') not in ['ORG','OG','student_id','birth','LC']]

        if detected:
            # Normalize & filter detections for storage/forwarding
            cleaned = _normalize_and_filter_detections(detected)
            merged_net, llm_type, tab = build_merged_metadata(data, request)

            detection_history.append({
                "timestamp": processed_at,
                "type": "group",
                "items": cleaned,
                "url": url,
                "network_info": merged_net,
                "tab": tab,
                "combination_risk": comb
            })
            for it in cleaned:
                st = f" [{it.get('status')}]" if 'status' in it else ""
                logging.info(f"✓ 탐지: {it.get('type')} = {it.get('value')}{st}")

            # Forward text summary to dashboard (skip LC addresses)
            try:
                payload = _forward_payload_for_items(cleaned, file_type_name='text', filename=None, network_info=merged_net, url=url or None, llm_type_name=llm_type, tab=tab, comb=comb)
                if payload:
                    res = send_to_dashboard(payload)
                    logging.info(f"대시보드 전송 결과(텍스트): {res}")
            except Exception as e:
                logging.error(f"대시보드 전송 실패(텍스트): {e}")

        return JSONResponse(content={"result":{"status":"처리 완료","detected_count": len(detected)}}, status_code=200)
    except Exception as e:
        logging.error(f"텍스트 이벤트 실패: {e}", exc_info=True)
        return JSONResponse(content={"status":"에러","message":str(e)}, status_code=500)

@app.post("/api/combined")
async def handle_combined(request: Request):
    if not verify_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        data = await request.json()
        text = data.get("text", "")
        files_data = data.get("files_data", [])
        url = data.get("url", "")
        network_info = data.get("network_info", {})
        processed_at = data.get("processed_at", "")
        header_ua = request.headers.get('user-agent') if request else None

        logging.info("========== 통합 이벤트 수신 ==========")
        logging.info(f"URL: {url}")
        logging.info(f"네트워크 정보: {network_info}")
        logging.info(f"텍스트: {len(text)}글자, 파일: {len(files_data)}개")

        if text.strip():
            ner_results   = detect_by_ner(text)
            regex_results = detect_by_regex(text)
            quasi_results = detect_quasi_identifiers(text)
            all_detected = regex_results + ner_results + quasi_results
            comb = analyze_combination_risk(all_detected, text)
            # Keep comb as metadata; do not append as detection item
            if comb:
                detected_text = list(all_detected)
            else:
                detected_text = [i for i in all_detected if i.get('type') not in ['ORG','OG','student_id','birth','LC']]
            if detected_text:
                # Normalize & filter for storage/forwarding
                cleaned_text = _normalize_and_filter_detections(detected_text)
                merged_net, llm_type, tab = build_merged_metadata(data, request)

                detection_history.append({
                    "timestamp": processed_at,
                    "type": "group",
                    "items": cleaned_text,
                    "url": url,
                    "network_info": merged_net,
                    "tab": tab,
                    "combination_risk": comb
                })
                # Forward text summary
                payload = _forward_payload_for_items(cleaned_text, file_type_name='text', filename=None, network_info=merged_net, url=url or None, llm_type_name=llm_type, tab=tab, comb=comb)
                if payload:
                    res = send_to_dashboard(payload)
                    logging.info(f"대시보드 전송 결과(텍스트): {res}")

        for f in files_data:
            fname = f.get("name", "unknown")
            b64 = f.get("data_b64", "")
            if not b64:
                continue

            if not fname or not isinstance(fname, str):
                logging.error(f"잘못된 파일명(name)을 수신했습니다: {fname}")
                continue
            
            fname = fname.strip()
            ext = fname.split('.')[-1].lower() if '.' in fname else ""
            logging.info(f"통합 이벤트 - 파일 처리: '{fname}', 추출된 확장자: '{ext}'")
            
            masked_name, pii_type = mask_pii_in_filename(fname)
            display = masked_name if masked_name != fname else fname
            if pii_type:
                logging.info(f"✓ 파일명 탐지: {pii_type} in '{display}'")
            fbytes = base64.b64decode(b64)
            detected_file, _, _, _, comb_file = handle_input_raw(fbytes, ext, fname)
            if detected_file:
                # Normalize & filter file detections
                cleaned_file = _normalize_and_filter_detections(detected_file)
                merged_net_file, llm_type_file, tab = build_merged_metadata(data, request)

                detection_history.append({
                    "timestamp": processed_at,
                    "type": "group",
                    "items": cleaned_file,
                    "url": url,
                    "network_info": merged_net_file,
                    "file_name": display,
                    "original_file_name": fname if display!=fname else None,
                    "tab": tab,
                    "combination_risk": comb_file
                })
                # 파일 탐지 결과 로그 출력
                for it in cleaned_file:
                    st = f" [{it.get('status')}]" if 'status' in it else ""
                    logging.info(f"✓ 탐지: {it.get('type')} = {it.get('value')}{st}")

                # Forward masked/display name instead of original filename to avoid leaking PII in dashboard
                payload = _forward_payload_for_items(cleaned_file, file_type_name=ext or 'unknown', filename=display, network_info=merged_net_file, url=url or None, llm_type_name=llm_type_file, tab=tab, comb=comb_file)
                if payload:
                    res = send_to_dashboard(payload)
                    logging.info(f"대시보드 전송 결과(파일): {res}")

        return JSONResponse(content={"result": {"status":"처리 완료"}}, status_code=200)
    except Exception as e:
        logging.error(f"통합 이벤트 실패: {e}", exc_info=True)
        return JSONResponse(content={"status":"에러","message":str(e)}, status_code=500)

@app.get("/api/detections")
async def get_detections():
    hist = list(detection_history)
    data = {"status":"success","total_detections": len(hist), "detections": list(reversed(hist[-50:]))}
    
    # --- [오류 수정] ---
    # 사용자 정의 인코더를 사용하여 JSONResponse 생성
    # 이렇게 하면 Numpy의 float32나 int64 같은 타입을 자동으로 Python 기본 타입으로 변환해줍니다.
    json_str = json.dumps(data, cls=NumpyEncoder)
    return HTMLResponse(content=json_str, media_type="application/json")


if __name__ == "__main__":

    uvicorn.run("LocalServer_Final:app", host="127.0.0.1", port=9000, reload=False)
