import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

import uvicorn
import base64
import secrets
import hmac
import hashlib
import time
from collections import deque

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from Logic import handle_input_raw, detect_by_ner, detect_by_regex
from fastapi.middleware.cors import CORSMiddleware

# 보안: Extension ID 화이트리스트
ALLOWED_EXTENSION_ID = os.getenv("ALLOWED_EXTENSION_ID", "hblalecgjndcjeaineacembpdfmmjaoa")
ALLOWED_ORIGINS = [
    f"chrome-extension://{ALLOWED_EXTENSION_ID}"
]

# 보안: 인증 기본 비활성화 (간편 모드)
REQUIRE_AUTH = os.getenv("PII_REQUIRE_AUTH", "false").lower() == "true"

if REQUIRE_AUTH:
    API_SECRET = os.getenv("PII_API_SECRET", secrets.token_hex(32))
    print(f"[SECURITY] ✓ 인증 활성화")
    print(f"[SECURITY] 개발자 도구 콘솔에서 setApiSecret() 함수로 Secret 설정")
else:
    API_SECRET = None
    print("[SECURITY] ⚠ 인증 비활성화 (개발 모드)")

# 파일 크기 제한 (바이트)
SOFT_LIMIT = 20 * 1024 * 1024   # 20MB
HARD_LIMIT = 100 * 1024 * 1024  # 100MB

app = FastAPI()

# 메모리 누수 방지: deque로 최대 1000개만 유지
detection_history = deque(maxlen=1000)

# 보안: CORS 화이트리스트 적용
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Auth-Token", "X-Timestamp"],
)

# 보안: 인증 검증 함수
def verify_auth(request: Request) -> bool:
    """HMAC 기반 요청 인증 검증 (선택적)"""
    # 인증 비활성화 시 항상 통과
    if not REQUIRE_AUTH:
        return True
    
    token = request.headers.get("X-Auth-Token", "")
    timestamp = request.headers.get("X-Timestamp", "")
    
    if not token or not timestamp:
        return False
    
    # 타임스탬프 검증 (5분 이내, 밀리초 단위)
    try:
        req_time = int(timestamp)
        current_time = int(time.time() * 1000)
        if abs(current_time - req_time) > 300000:  # 5분 (밀리초)
            print(f"[SECURITY] 타임스탬프 만료: {abs(current_time - req_time)}ms 차이")
            return False
    except:
        return False
    
    # HMAC 검증
    expected = hmac.new(
        API_SECRET.encode(),
        timestamp.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return secrets.compare_digest(token, expected)

@app.get("/")
def root():
    return {"message": "PII Detection Server Running", "status": "ok"}

@app.get("/dashboard")
async def dashboard():
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>개인정보 탐지 모니터</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', sans-serif;
                background: #0f172a;
                color: white;
                padding: 20px;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 40px;
                border-radius: 20px;
                margin-bottom: 30px;
                text-align: center;
            }
            h1 { font-size: 3em; margin-bottom: 10px; }
            .status {
                display: inline-block;
                background: #10b981;
                padding: 10px 30px;
                border-radius: 50px;
                font-size: 1.2em;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.7; }
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 25px;
                margin-bottom: 30px;
            }
            .card {
                background: #1e293b;
                padding: 30px;
                border-radius: 15px;
                border: 2px solid #334155;
                transition: all 0.3s;
            }
            .card:hover {
                border-color: #667eea;
                transform: translateY(-5px);
            }
            .card h2 {
                color: #667eea;
                font-size: 1.5em;
                margin-bottom: 20px;
            }
            .metric {
                font-size: 4em;
                font-weight: bold;
                color: #10b981;
                margin: 20px 0;
            }
            .list {
                list-style: none;
                line-height: 2.5;
            }
            .list li:before {
                content: "✓ ";
                color: #10b981;
                font-weight: bold;
                margin-right: 10px;
            }
            .realtime {
                background: #1e293b;
                padding: 30px;
                border-radius: 15px;
                border: 2px solid #334155;
                max-height: 600px;
                overflow-y: auto;
            }
            .realtime h2 {
                color: #667eea;
                margin-bottom: 20px;
                font-size: 1.8em;
            }
            .log-entry {
                background: #0f172a;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 10px;
                border-left: 4px solid #10b981;
            }
            .log-entry.face {
                border-left-color: #f59e0b;
            }
            .log-time {
                color: #94a3b8;
                font-size: 0.9em;
            }
            .empty {
                text-align: center;
                color: #64748b;
                padding: 40px;
                font-size: 1.1em;
            }
            .type-badge {
                display: inline-block;
                background: #667eea;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 0.85em;
                margin-right: 8px;
            }
            .netinfo {
                color: #94a3b8;
                font-size: 0.85em;
                margin-top: 5px;
                line-height: 1.6;
            }
        </style>
        <script>
            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
            function parseUA(ua) {
                let browser = 'Unknown', os = 'Unknown';
                if (ua.includes('Chrome')) browser = 'Chrome ' + (ua.match(/Chrome\/(\d+)/) || [])[1];
                else if (ua.includes('Firefox')) browser = 'Firefox ' + (ua.match(/Firefox\/(\d+)/) || [])[1];
                else if (ua.includes('Safari') && !ua.includes('Chrome')) browser = 'Safari';
                if (ua.includes('Windows NT 10.0')) os = 'Windows 10';
                else if (ua.includes('Windows NT 11.0')) os = 'Windows 11';
                else if (ua.includes('Mac OS X')) os = 'macOS';
                else if (ua.includes('Linux')) os = 'Linux';
                return { browser, os };
            }
            async function fetchDetections() {
                try {
                    const response = await fetch('/api/detections');
                    const data = await response.json();
                    
                    document.getElementById('total-count').textContent = data.total_detections || 0;
                    
                    const logContainer = document.getElementById('detection-logs');
                    if (data.detections && data.detections.length > 0) {
                        logContainer.innerHTML = data.detections.map(d => {
                            if (d.type === 'group' && d.items) {
                                return `
                                <div class="log-entry">
                                    <div class="log-time">${new Date(d.timestamp).toLocaleString('ko-KR')} - ${d.items.length}개 탐지</div>
                                    ${d.items.map(item => `
                                        <div style="margin: 5px 0;">
                                            <span class="type-badge">${escapeHtml(item.type)}</span>
                                            <strong>${escapeHtml(item.value)}</strong>
                                        </div>
                                    `).join('')}
                                    ${d.url ? `<div class="netinfo">출처: ${d.url}</div>` : ''}
                                    ${d.network_info && d.network_info.ip ? `<div class="netinfo">IPs: ${d.network_info.ip}</div>` : ''}
                                    ${d.network_info && d.network_info.hostname ? `<div class="netinfo">컴퓨터: ${d.network_info.hostname}</div>` : ''}
                                    ${d.tab && d.tab.ua ? (() => { const i = parseUA(d.tab.ua); return `<div class="netinfo">Browser: ${i.browser}</div><div class="netinfo">OS: ${i.os}</div>`; })() : ''}
                                </div>
                                `;
                            } else {
                                return `
                                <div class="log-entry ${d.type === 'image_face' ? 'face' : ''}">
                                    <div class="log-time">${new Date(d.timestamp).toLocaleString('ko-KR')}</div>
                                    <div>
                                        <span class="type-badge">${escapeHtml(d.type)}</span>
                                        <strong>${escapeHtml(d.value || '(파일)')}</strong>
                                    </div>
                                    ${d.file_name ? `<div class="netinfo">파일명: ${d.file_name}</div>` : ''}
                                    ${d.url ? `<div class="netinfo">출처: ${d.url}</div>` : ''}
                                    ${d.network_info && d.network_info.ip ? `<div class="netinfo">IPs: ${d.network_info.ip}</div>` : ''}
                                    ${d.network_info && d.network_info.hostname ? `<div class="netinfo">컴퓨터: ${d.network_info.hostname}</div>` : ''}
                                    ${d.tab && d.tab.ua ? (() => { const i = parseUA(d.tab.ua); return `<div class="netinfo">Browser: ${i.browser}</div><div class="netinfo">OS: ${i.os}</div>`; })() : ''}
                                </div>
                                `;
                            }
                        }).join('');
                    } else {
                        logContainer.innerHTML = '<div class="empty">아직 탐지된 내역이 없습니다.<br><br>ChatGPT나 Claude에서<br>개인정보를 입력하거나 파일을 업로드해보세요.</div>';
                    }
                } catch (error) {
                    console.error('탐지 내역 로드 실패:', error);
                }
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
            <div class="card">
                <h2>📊 총 탐지 건수</h2>
                <div class="metric" id="total-count">0</div>
                <p style="color: #94a3b8;">누적 개인정보 탐지 횟수</p>
            </div>

            <div class="card">
                <h2>🔍 탐지 항목</h2>
                <ul class="list">
                    <li>전화번호</li>
                    <li>이메일 주소</li>
                    <li>주민등록번호</li>
                    <li>카드번호</li>
                    <li>계좌번호</li>
                    <li>인명 (NER)</li>
                    <li>얼굴 이미지</li>
                </ul>
            </div>

            <div class="card">
                <h2>📁 지원 파일</h2>
                <ul class="list">
                    <li>PDF 문서</li>
                    <li>Word 문서 (DOCX)</li>
                    <li>텍스트 파일 (TXT)</li>
                    <li>이미지 (PNG, JPG, JPEG)</li>
                    <li>기타 (BMP, WEBP, GIF, TIFF)</li>
                </ul>
            </div>
        </div>

        <div class="realtime">
            <h2>🔴 실시간 탐지 내역 (최근 50개)</h2>
            <div id="detection-logs">
                <div class="empty">데이터 로딩 중...</div>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/api/file_collect")
async def handle_file_collect(request: Request):
    """Extension에서 파일 데이터를 받아 처리"""
    # 보안: 인증 검증
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
            return JSONResponse(content={"status": "에러", "message": "파일 데이터 없음"}, status_code=400)
        
        # 파일 크기 체크 (Base64 디코딩 전)
        estimated_size = len(file_b64) * 3 // 4
        
        if estimated_size > HARD_LIMIT:
            return JSONResponse(
                content={"status": "에러", "message": f"파일이 너무 큽니다 (최대 100MB)"},
                status_code=413
            )
        
        if estimated_size > SOFT_LIMIT:
            print(f"[WARN] 큰 파일 처리 중: {estimated_size / 1024 / 1024:.1f}MB - {file_name}")
        
        print(f"[INFO] 파일 수신: {file_name} ({estimated_size / 1024:.1f}KB)")
        print(f"[INFO] 출처 URL: {origin_url}")
        
        file_bytes = base64.b64decode(file_b64)
        extension = file_name.split('.')[-1].lower() if '.' in file_name else ""
        
        try:
            detected, _, _, _ = handle_input_raw(file_bytes, extension)
            
            for item in detected:
                detection_history.append({
                    "timestamp": processed_at,
                    "type": item["type"],
                    "value": item["value"],
                    "url": origin_url,
                    "network_info": network_info,
                    "file_name": file_name
                })
            
            return JSONResponse(content={"result": {"status": "처리 완료"}}, status_code=200)

        except Exception as e:
            return JSONResponse(content={"status": "에러", "message": str(e)}, status_code=500)

    except Exception as e:
        return JSONResponse(content={"status": "에러", "message": str(e)}, status_code=500)

@app.post("/api/event")
async def handle_text_event(request: Request):
    """Extension에서 텍스트 이벤트"""
    # 보안: 인증 검증
    if not verify_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        data = await request.json()
        text = data.get("text", "")
        url = data.get("url", "")
        network_info = data.get("network_info", {})
        processed_at = data.get("processed_at", "")

        print(f"[INFO] ========== 텍스트 이벤트 수신 ==========")
        print(f"[INFO] URL: {url}")
        print(f"[INFO] 네트워크 정보: {network_info}")
        print(f"[INFO] 텍스트 길이: {len(text)} 글자")

        if not text.strip():
            print("[WARN] 전송된 텍스트가 비어있음")
            return JSONResponse(content={"result": {"status": "텍스트 없음"}}, status_code=200)

        # NER 먼저 실행
        ner_results = detect_by_ner(text)
        regex_results = detect_by_regex(text)
        
        # NER로 탐지된 이름 목록
        ner_names = {d["value"] for d in ner_results if d["type"].upper() in ["PER", "PS"]}
        
        # 정규식에서 korean_name 중복 제거
        filtered_regex = [d for d in regex_results if not (d["type"] == "korean_name" and d["value"] in ner_names)]
        
        detected = filtered_regex + ner_results
        
        print(f"[INFO] 탐지 결과: {len(detected)}개")
        
        for item in detected:
            detection_history.append({
                "timestamp": processed_at,
                "type": item["type"],
                "value": item["value"],
                "url": url,
                "network_info": network_info,
                "tab": data.get("tab", {})
            })
            print(f"[INFO] ✓ 탐지: {item['type']} = {item['value']}")

        return JSONResponse(content={"result": {"status": "처리 완료", "detected_count": len(detected)}}, status_code=200)

    except Exception as e:
        print(f"[ERROR] 텍스트 이벤트 처리 실패: {e}")
        return JSONResponse(content={"status": "에러", "message": str(e)}, status_code=500)

@app.post("/api/combined")
async def handle_combined(request: Request):
    """파일+텍스트 통합 처리"""
    # 보안: 인증 검증
    if not verify_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        data = await request.json()
        text = data.get("text", "")
        files_data = data.get("files_data", [])
        url = data.get("url", "")
        network_info = data.get("network_info", {})
        processed_at = data.get("processed_at", "")

        print(f"[INFO] ========== 통합 이벤트 수신 ==========")
        print(f"[INFO] URL: {url}")
        print(f"[INFO] 네트워크 정보: {network_info}")
        print(f"[INFO] 텍스트: {len(text)}글자, 파일: {len(files_data)}개")

        # 텍스트 탐지
        if text.strip():
            # NER 먼저 실행
            ner_results = detect_by_ner(text)
            regex_results = detect_by_regex(text)
            
            # NER로 탐지된 이름 목록
            ner_names = {d["value"] for d in ner_results if d["type"].upper() in ["PER", "PS"]}
            
            # 정규식에서 korean_name 중복 제거
            filtered_regex = [d for d in regex_results if not (d["type"] == "korean_name" and d["value"] in ner_names)]
            
            detected = filtered_regex + ner_results
            if detected:
                detection_history.append({
                    "timestamp": processed_at,
                    "type": "group",
                    "items": detected,
                    "url": url,
                    "network_info": network_info,
                    "tab": data.get("tab", {})
                })
                for item in detected:
                    print(f"[INFO] ✓ 텍스트 탐지: {item['type']} = {item['value']}")

        # 파일 탐지
        for file_info in files_data:
            file_name = file_info.get("name", "unknown")
            file_b64 = file_info.get("data_b64", "")
            if file_b64:
                file_bytes = base64.b64decode(file_b64)
                extension = file_name.split('.')[-1].lower() if '.' in file_name else ""
                detected, _, _, _ = handle_input_raw(file_bytes, extension)
                for item in detected:
                    detection_history.append({
                        "timestamp": processed_at,
                        "type": item["type"],
                        "value": item["value"],
                        "url": url,
                        "network_info": network_info,
                        "file_name": file_name,
                        "tab": data.get("tab", {})
                    })
                    print(f"[INFO] ✓ 파일 탐지: {item['type']} = {item['value']}")

        return JSONResponse(content={"result": {"status": "처리 완료"}}, status_code=200)

    except Exception as e:
        print(f"[ERROR] 통합 이벤트 처리 실패: {e}")
        return JSONResponse(content={"status": "에러", "message": str(e)}, status_code=500)

@app.get("/api/detections")
async def get_detections():
    history_list = list(detection_history)
    data = {
        "status": "success",
        "total_detections": len(history_list),
        "detections": list(reversed(history_list[-50:]))
    }
    return JSONResponse(content=data)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9000, reload=False)
