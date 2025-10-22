# =============================
# File: LocalServer_Final.py (JSON 직렬화 오류 수정 및 터미널 로그 개선 버전)
# Desc: float32 타입 JSON 변환 오류를 해결하기 위해 사용자 정의 JSON 인코더를 추가했습니다.
#       이제 NER 모델의 신뢰도 점수(score)가 포함된 탐지 결과도 정상적으로 처리됩니다.
#
# [수정] 2025-10-22:
# 1. 조합 위험도를 터미널 로그에도 출력 (logging.warning)
# 2. 준식별자 필터링 로직 변경 (사용자 요청 반영)
#    - (1 quasi): 터미널 O, 대시보드 X
#    - (2 quasi, ORG+LC): 터미널 X, 대시보드 X
#    - (2 quasi, Other): 터미널 O, 대시보드 O
#    - (ID 또는 Risk): 터미널 O, 대시보드 O
# =============================

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

import uvicorn
import base64
import secrets
import hmac
import hashlib
import time
import logging
import json
import numpy as np
from collections import deque

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
    categorize_detection, # [수정] 서버 필터링을 위해 import
)

# 로깅 기본 설정
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(asctime)s - %(message)s')

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
    html = """
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
        .log-entry.risk { border-left-color:#ef4444; }
        .log-time { color:#94a3b8; font-size:0.9rem; }
        .type { display:inline-block; background:#667eea; padding:2px 10px; border-radius:12px; margin-right:8px; font-size:0.85rem; }
        .type-risk { background:#ef4444; }
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
                    d.items.map(it=>{
                        const isRisk = it.type === 'combination_risk';
                        return `<div style="margin:4px 0"><span class="type ${isRisk ? 'type-risk' : ''}">${escapeHtml(it.type)}</span><strong>${escapeHtml(it.value||'')}</strong>${it.status? (it.status==='valid'?'<span class="status-valid">(valid)</span>':`<span class="status-invalid">(${escapeHtml(it.status)})</span>`):''}</div>`
                    }).join('')+
                    `${d.file_name?`<div class="netinfo">파일명: ${escapeHtml(d.file_name)}</div>`:''}`+
                    `${d.url?`<div class="netinfo">출처: ${d.url}</div>`:''}`+
                    `${d.network_info&&d.network_info.ip?`<div class="netinfo">IPs: ${d.network_info.ip}</div>`:''}`+
                    `${d.network_info&&d.network_info.hostname?`<div class="netinfo">컴퓨터: ${d.network_info.hostname}</div>`:''}`+
                    `${d.tab&&d.tab.ua?(()=>{const i=parseUA(d.tab.ua);return `<div class=\"netinfo\">Browser: ${i.browser}</div><div class=\"netinfo\">OS: ${i.os}</div>`})():''}`+
                  `</div>`
                }
                const isRisk = d.type === 'combination_risk';
                return `<div class="log-entry ${d.type==='image_face'?'face':''} ${isRisk ? 'risk' : ''}"><div class="log-time">${new Date(d.timestamp).toLocaleString('ko-KR')}</div><div><span class="type ${isRisk ? 'type-risk' : ''}">${escapeHtml(d.type)}</span><strong>${escapeHtml(d.value||'(파일)')}</strong>${d.status?(d.status==='valid'?'<span class="status-valid">(valid)</span>':`<span class="status-invalid">(${escapeHtml(d.status)})</span>`):''}</div>${d.file_name?`<div class=\"netinfo\">파일명: ${escapeHtml(d.file_name)}</div>`:''}${d.url?`<div class=\"netinfo\">출처: ${d.url}</div>`:''}${d.network_info&&d.network_info.ip?`<div class=\"netinfo\">IPs: ${d.network_info.ip}</div>`:''}${d.network_info&&d.network_info.hostname?`<div class=\"netinfo\">컴퓨터: ${d.network_info.hostname}</div>`:''}${d.tab&&d.tab.ua?(()=>{const i=parseUA(d.tab.ua);return `<div class=\"netinfo\">Browser: ${i.browser}</div><div class=\"netinfo\">OS: ${i.os}</div>`})():''}</div>`
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

        # 파일명 자체의 PII는 항상 터미널+대시보드에 보고 (규칙 예외)
        masked_name, pii_type = mask_pii_in_filename(file_name)
        display_name = masked_name if masked_name != file_name else file_name
        if pii_type:
            logging.info(f"✓ [파일명] 탐지: {pii_type} = {display_name}")
            detection_history.append({
                "timestamp": processed_at,
                "type": f"파일명_{pii_type}",
                "value": display_name,
                "url": origin_url,
                "network_info": network_info,
                "file_name": display_name,
                "tab": data.get("tab", {})
            })

        file_bytes = base64.b64decode(file_b64)
        
        # [수정] handle_input_raw는 이제 모든 항목을 반환
        detected_file_all, _, _, _ = handle_input_raw(file_bytes, extension, file_name)

        if detected_file_all:
            # --- [수정] 파일에 대한 필터링 로직 적용 ---
            detected_for_dashboard_file = []
            detected_for_terminal_file = []

            comb_file = None
            for it in detected_file_all:
                if it.get('type') == 'combination_risk':
                    comb_file = it
                    break
            
            real_items_file = [i for i in detected_file_all if i.get('type') != 'combination_risk']
            
            identifiers_file = [i for i in real_items_file if categorize_detection(i.get('type')) == 'identifier']
            sensitives_file = [i for i in real_items_file if categorize_detection(i.get('type')) == 'sensitive']
            quasi_items_file = [i for i in real_items_file if categorize_detection(i.get('type')) == 'quasi']
            quasi_types_file = set(i.get('type') for i in quasi_items_file)
            num_quasi_types_file = len(quasi_types_file)

            if comb_file:
                detected_for_dashboard_file = list(detected_file_all)
                detected_for_terminal_file = list(detected_file_all)
            
            elif identifiers_file or sensitives_file: # 식별자 또는 민감정보(얼굴)
                detected_for_dashboard_file = list(real_items_file)
                detected_for_terminal_file = list(real_items_file)
            
            else:
                # (조직, 주소) 그룹 정의
                org_lc_types = {'ORG', 'OG', 'LC', 'LOC'}
                is_only_org_lc_file = all(t in org_lc_types for t in quasi_types_file)

                if num_quasi_types_file == 1:
                    detected_for_dashboard_file = [] # 대시보드 X
                    detected_for_terminal_file = list(real_items_file) # 터미널 O
                elif num_quasi_types_file == 2:
                    if is_only_org_lc_file:
                        detected_for_dashboard_file = [] # 대시보드 X
                        detected_for_terminal_file = [] # 터미널 X
                    else:
                        detected_for_dashboard_file = list(real_items_file) # 대시보드 O
                        detected_for_terminal_file = list(real_items_file) # 터미널 O
                elif num_quasi_types_file > 2:
                    detected_for_dashboard_file = list(real_items_file)
                    detected_for_terminal_file = list(real_items_file)
            # --- [수정] 필터링 로직 끝 ---

            # 대시보드에 전송
            if detected_for_dashboard_file:
                detection_history.append({
                    "timestamp": processed_at,
                    "type": "group",
                    "items": detected_for_dashboard_file,
                    "url": origin_url,
                    "network_info": network_info,
                    "file_name": display_name,
                    "original_file_name": file_name if display_name!=file_name else None,
                    "tab": data.get("tab", {})
                })
            
            # 터미널에 로그 출력
            if detected_for_terminal_file:
                for it in detected_for_terminal_file:
                    st = f" [{it.get('status')}]" if 'status' in it else ""
                    log_msg = f"✓ [파일: {file_name}] 탐지: {it.get('type')} = {it.get('value')}{st}"
                    if it.get('type') == 'combination_risk':
                        logging.warning(log_msg)
                    else:
                        logging.info(log_msg)

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
        
        # --- [수정] 필터링 로직 적용 ---
        detected_for_dashboard = []
        detected_for_terminal = []

        identifiers = [i for i in all_detected if categorize_detection(i.get('type')) == 'identifier']
        # (민감정보는 파일에만 있으므로 텍스트에서는 체크 제외)
        quasi_items = [i for i in all_detected if categorize_detection(i.get('type')) == 'quasi']
        quasi_types = set(i.get('type') for i in quasi_items)
        num_quasi_types = len(quasi_types)

        if comb:
            # 1. 조합 위험도 발견 시
            detected_for_dashboard = list(all_detected)
            risk_item = {
                "type":"combination_risk",
                "value": comb['message'],
                "risk_level": comb['level'],
                "risk_items": comb['items'],
                "counts": comb['counts']
            }
            detected_for_dashboard.append(risk_item)
            detected_for_terminal = list(detected_for_dashboard)
        
        elif identifiers:
            # 2. 식별자 발견 시 (조합 위험은 없을 때)
            detected_for_dashboard = list(all_detected)
            detected_for_terminal = list(all_detected)
        
        else:
            # 3. 준식별자만 있을 때
            # (조직, 주소) 그룹 정의
            org_lc_types = {'ORG', 'OG', 'LC', 'LOC'}
            is_only_org_lc = all(t in org_lc_types for t in quasi_types)

            if num_quasi_types == 1:
                # (1 quasi): 터미널 O, 대시보드 X
                detected_for_dashboard = [] 
                detected_for_terminal = list(all_detected)
            
            elif num_quasi_types == 2:
                if is_only_org_lc:
                    # (2 quasi, ORG+LC): 터미널 X, 대시보드 X
                    detected_for_dashboard = []
                    detected_for_terminal = []
                else:
                    # (2 quasi, Other): 터미널 O, 대시보드 O
                    detected_for_dashboard = list(all_detected)
                    detected_for_terminal = list(all_detected)
            
            elif num_quasi_types > 2:
                # (3+ quasi): (comb가 처리했어야 하지만) 터미널 O, 대시보드 O
                detected_for_dashboard = list(all_detected)
                detected_for_terminal = list(all_detected)
        # --- [수정] 필터링 로직 끝 ---


        if detected_for_dashboard:
            detection_history.append({
                "timestamp": processed_at,
                "type": "group",
                "items": detected_for_dashboard,
                "url": url,
                "network_info": network_info,
                "tab": data.get("tab", {})
            })
        
        if detected_for_terminal:
            # 위치순으로 정렬 (터미널 출력용)
            sorted_for_logging = sorted(
                detected_for_terminal, 
                key=lambda x: x.get('span', (9999, 9999))[0] if x.get('span') else 9999
            )
            
            addr_detected = [it for it in sorted_for_logging if it.get('type') in {'LC', 'LOC'}]
            risk_detected = [it for it in sorted_for_logging if it.get('type') == 'combination_risk']
            non_addr_detected = [it for it in sorted_for_logging if it.get('type') not in {'LC', 'LOC', 'combination_risk'}]
            
            # 주소 먼저 출력
            for it in addr_detected:
                st = f" [{it.get('status')}]" if 'status' in it else ""
                logging.info(f"✓ 탐지: {it.get('type')} = {it.get('value')}{st}")
                
            # 나머지 항목 출력
            for it in non_addr_detected:
                st = f" [{it.get('status')}]" if 'status' in it else ""
                logging.info(f"✓ 탐지: {it.get('type')} = {it.get('value')}{st}")
            
            # 조합 위험도 항목을 마지막에 logging.warning으로 강조하여 출력
            for it in risk_detected:
                logging.warning(f"✓ 탐지: {it.get('type')} = {it.get('value')}")

        return JSONResponse(content={"result":{"status":"처리 완료","detected_count": len(detected_for_dashboard)}}, status_code=200)
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

        logging.info("========== 통합 이벤트 수신 ==========")
        logging.info(f"URL: {url}")
        logging.info(f"네트워크 정보: {network_info}")
        logging.info(f"텍스트: {len(text)}글자, 파일: {len(files_data)}개")

        # 1. 텍스트 처리
        if text.strip():
            ner_results   = detect_by_ner(text)
            regex_results = detect_by_regex(text)
            quasi_results = detect_quasi_identifiers(text)
            all_detected = regex_results + ner_results + quasi_results
            
            comb = analyze_combination_risk(all_detected, text)

            # --- [수정] 텍스트 필터링 로직 적용 ---
            detected_for_dashboard_text = []
            detected_for_terminal_text = []

            identifiers = [i for i in all_detected if categorize_detection(i.get('type')) == 'identifier']
            quasi_items = [i for i in all_detected if categorize_detection(i.get('type')) == 'quasi']
            quasi_types = set(i.get('type') for i in quasi_items)
            num_quasi_types = len(quasi_types)

            if comb:
                detected_for_dashboard_text = list(all_detected)
                risk_item = {
                    "type":"combination_risk",
                    "value": comb['message'],
                    "risk_level": comb['level'],
                    "risk_items": comb['items'],
                    "counts": comb['counts']
                }
                detected_for_dashboard_text.append(risk_item)
                detected_for_terminal_text = list(detected_for_dashboard_text)
            
            elif identifiers:
                detected_for_dashboard_text = list(all_detected)
                detected_for_terminal_text = list(all_detected)
            
            else:
                org_lc_types = {'ORG', 'OG', 'LC', 'LOC'}
                is_only_org_lc = all(t in org_lc_types for t in quasi_types)

                if num_quasi_types == 1:
                    detected_for_dashboard_text = [] 
                    detected_for_terminal_text = list(all_detected)
                elif num_quasi_types == 2:
                    if is_only_org_lc:
                        detected_for_dashboard_text = []
                        detected_for_terminal_text = []
                    else:
                        detected_for_dashboard_text = list(all_detected)
                        detected_for_terminal_text = list(all_detected)
                elif num_quasi_types > 2:
                    detected_for_dashboard_text = list(all_detected)
                    detected_for_terminal_text = list(all_detected)
            # --- [수정] 텍스트 필터링 로직 끝 ---

            # 대시보드에 텍스트 결과 전송
            if detected_for_dashboard_text:
                detection_history.append({
                    "timestamp": processed_at,
                    "type": "group",
                    "items": detected_for_dashboard_text,
                    "url": url,
                    "network_info": network_info,
                    "tab": data.get("tab", {})
                })

            # 터미널에 텍스트 결과 출력
            if detected_for_terminal_text:
                sorted_text_logs = sorted(
                    detected_for_terminal_text, 
                    key=lambda x: x.get('span', (9999, 9999))[0] if x.get('span') else 9999
                )
                for it in sorted_text_logs:
                    st = f" [{it.get('status')}]" if 'status' in it else ""
                    log_msg = f"✓ [텍스트] 탐지: {it.get('type')} = {it.get('value')}{st}"
                    if it.get('type') == 'combination_risk':
                        logging.warning(log_msg)
                    else:
                        logging.info(log_msg)
        
        # 2. 파일 처리
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
            
            # 파일명 자체 PII (항상 터미널+대시보드)
            masked_name, pii_type = mask_pii_in_filename(fname)
            display = masked_name if masked_name != fname else fname
            if pii_type:
                logging.info(f"✓ [파일명] 탐지: {pii_type} = {display}")
                detection_history.append({
                    "timestamp": processed_at,
                    "type": f"파일명_{pii_type}",
                    "value": display,
                    "url": url,
                    "network_info": network_info,
                    "file_name": display,
                    "tab": data.get("tab", {})
                })
            
            fbytes = base64.b64decode(b64)
            
            # [수정] Logic_Final이 모든 항목을 반환
            detected_file_all, _, _, _ = handle_input_raw(fbytes, ext, fname)
            
            if detected_file_all:
                # --- [수정] 파일 필터링 로직 적용 ---
                detected_for_dashboard_file = []
                detected_for_terminal_file = []

                comb_file = None
                for it in detected_file_all:
                    if it.get('type') == 'combination_risk':
                        comb_file = it
                        break
                
                real_items_file = [i for i in detected_file_all if i.get('type') != 'combination_risk']
                
                identifiers_file = [i for i in real_items_file if categorize_detection(i.get('type')) == 'identifier']
                sensitives_file = [i for i in real_items_file if categorize_detection(i.get('type')) == 'sensitive']
                quasi_items_file = [i for i in real_items_file if categorize_detection(i.get('type')) == 'quasi']
                quasi_types_file = set(i.get('type') for i in quasi_items_file)
                num_quasi_types_file = len(quasi_types_file)

                if comb_file:
                    detected_for_dashboard_file = list(detected_file_all)
                    detected_for_terminal_file = list(detected_file_all)
                
                elif identifiers_file or sensitives_file: # 식별자 또는 민감정보(얼굴)
                    detected_for_dashboard_file = list(real_items_file)
                    detected_for_terminal_file = list(real_items_file)
                
                else:
                    org_lc_types = {'ORG', 'OG', 'LC', 'LOC'}
                    is_only_org_lc_file = all(t in org_lc_types for t in quasi_types_file)

                    if num_quasi_types_file == 1:
                        detected_for_dashboard_file = []
                        detected_for_terminal_file = list(real_items_file)
                    elif num_quasi_types_file == 2:
                        if is_only_org_lc_file:
                            detected_for_dashboard_file = []
                            detected_for_terminal_file = []
                        else:
                            detected_for_dashboard_file = list(real_items_file)
                            detected_for_terminal_file = list(real_items_file)
                    elif num_quasi_types_file > 2:
                        detected_for_dashboard_file = list(real_items_file)
                        detected_for_terminal_file = list(real_items_file)
                # --- [수정] 파일 필터링 로직 끝 ---

                # 파일 결과 터미널 출력
                if detected_for_terminal_file:
                    for it in detected_for_terminal_file:
                        st = f" [{it.get('status')}]" if 'status' in it else ""
                        log_msg = f"✓ [파일: {fname}] 탐지: {it.get('type')} = {it.get('value')}{st}"
                        if it.get('type') == 'combination_risk':
                            logging.warning(log_msg)
                        else:
                            logging.info(log_msg)
                
                # 파일 결과 대시보드 전송
                if detected_for_dashboard_file:
                    detection_history.append({
                        "timestamp": processed_at,
                        "type": "group",
                        "items": detected_for_dashboard_file,
                        "url": url,
                        "network_info": network_info,
                        "file_name": display,
                        "original_file_name": fname if display!=fname else None,
                        "tab": data.get("tab", {})
                    })

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
    # [수정] LocalServer_Final:app 으로 실행, 포트 9000
    uvicorn.run("LocalServer_Final:app", host="127.0.0.1", port=9000, reload=False)