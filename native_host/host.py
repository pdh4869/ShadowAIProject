# ===== native_host/host.py (최종 완성본: 오류 수정 및 JSON 포워딩) =====
import sys
import json
import struct
import socket
import winreg
import requests
import subprocess
import re
from typing import Dict, Any, List, Union # <--- Union 추가 완료

# --- 외부 탐지 모듈 엔드포인트 설정 ---
DETECTION_ENDPOINT = "http://127.0.0.1:9090/detect"

# ---- Native Messaging I/O ----
def read_message() -> Union[Dict[str, Any], None]:
    """Chrome으로부터 메시지를 읽습니다."""
    try:
        raw_length = sys.stdin.buffer.read(4)
        if not raw_length:
            return None
        # ★ 수정: struct 포맷을 '<I' (Little-Endian)로 변경했습니다. ★
        message_length = struct.unpack('<I', raw_length)[0] 
        message = sys.stdin.buffer.read(message_length).decode('utf-8', errors='ignore')
        return json.loads(message)
    except Exception as e:
        print(f"[ERROR] Failed to read message: {e}", file=sys.stderr)
        return None

def send_message(message: Dict[str, Any]):
    """Chrome으로 메시지를 보냅니다."""
    try:
        encoded_content = json.dumps(message, ensure_ascii=False).encode('utf-8')
        # ★ 수정: struct 포맷을 '<I' (Little-Endian)로 변경했습니다. ★
        encoded_length = struct.pack('<I', len(encoded_content))
        sys.stdout.buffer.write(encoded_length)
        sys.stdout.buffer.write(encoded_content)
        sys.stdout.buffer.flush()
    except Exception as e:
        print(f"[ERROR] Failed to send message: {e}", file=sys.stderr)

# ---- Windows 시스템 정보 수집 함수 ----
def get_dns_servers() -> Union[List[str], None]:
    # ... (기존 로직 유지) ...
    try:
        out = subprocess.check_output(["ipconfig", "/all"], encoding="cp437", errors="ignore")
        dns = []
        capture_dns = False
        for line in out.splitlines():
             if ("DNS 서버" in line) or ("DNS Servers" in line):
                capture_dns = True
                m = re.findall(r"(\d+\.\d+\.\d+\.\d+)", line)
                dns.extend(m)
                continue
             if capture_dns:
                 m = re.findall(r"(\d+\.\d+\.\d+\.\d+)", line)
                 if m: dns.extend(m)
                 else:
                     if line.strip() == "" or ":" in line: capture_dns = False
        return list(set(d for d in dns if not d.startswith("0.0.0."))) or None
    except Exception:
        return None

def get_default_gateways() -> Union[List[str], None]:
    # ... (기존 로직 유지) ...
    try:
        out = subprocess.check_output(["ipconfig", "/all"], encoding="cp437", errors="ignore")
        gw = []
        for line in out.splitlines():
            if ("기본 게이트웨이" in line) or ("Default Gateway" in line):
                m = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
                if m: gw.append(m.group(1))
        return list(set(gw)) or None
    except Exception:
        return None

def get_interface_ips() -> Union[List[Dict[str, Any]], None]:
    # ... (기존 로직 유지) ...
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return [{"name": "primary", "ips": [ip]}]
    except Exception:
        return None

def gather_network_info() -> Dict[str, Any]:
    """로컬 시스템 네트워크 정보를 모아 딕셔너리로 반환합니다."""
    info = {}
    
    gateways = get_default_gateways()
    if gateways: info["gateway"] = gateways
        
    dns_servers = get_dns_servers()
    if dns_servers: info["dns"] = dns_servers
        
    interfaces = get_interface_ips()
    if interfaces: info["interfaces"] = interfaces
        
    return info

# ---- JSON 포워딩 로직 ----
def forward_to_detection_module(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    외부 탐지 모듈(9090 포트)로 JSON 페이로드를 전송합니다.
    """
    try:
        resp = requests.post(DETECTION_ENDPOINT, json=payload, timeout=3)
        return {"ok": True, "status": resp.status_code}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ---- 메시지 처리 메인 함수 ----
def process_message(msg: Dict[str, Any]):
    """메시지를 처리하고 응답을 보냅니다."""
    cmd = msg.get("cmd")
    req_id = msg.get("reqId")
    
    if cmd == "process_event":
        # 1. JSON 페이로드 (metadata) 수신
        event_payload = msg.get("payload", {})
        
        # 2. 시스템/네트워크 정보 수집
        net_info = gather_network_info()

        # 3. JSON 페이로드와 네트워크 정보를 결합 (외부 모듈 전송용)
        combined_payload = event_payload.copy()
        combined_payload["network_info"] = net_info # 네트워크 정보를 JSON에 결합

        # 4. 외부 탐지 모듈(9090)로 결합된 JSON 전송
        forward_result = forward_to_detection_module(combined_payload)
        
        # 콘솔에 포워딩 로그 출력 (sys.stderr 사용)
        print(f"[HOST] Forwarded to Detection Module ({forward_result.get('status', forward_result.get('error'))}): {combined_payload.get('raw_text', '')[:50]}...", file=sys.stderr)
        
        # 5. Native Host는 네트워크 정보만 응답으로 반환 (FastAPI 대시보드 저장용)
        send_message({"ok": True, "reqId": req_id, "data": {"network": net_info}})

    elif cmd == "get_info":
        net_info = gather_network_info()
        send_message({"ok": True, "reqId": req_id, "data": {"network": net_info}})

    else:
        send_message({"ok": False, "reqId": req_id, "error": f"Unknown command: {cmd}"})


# ---- 메인 루프 ----
if __name__ == "__main__":
    print(f"[host] Native host started, waiting for messages. DETECTION_ENDPOINT={DETECTION_ENDPOINT}", file=sys.stderr)
    
    while True:
        msg = read_message()
        if msg is None:
            continue 
        try:
            process_message(msg)
        except Exception as e:
            error_resp = {
                "reqId": msg.get("reqId") if msg else None,
                "ok": False,
                "error": f"Host Error: {type(e).__name__}: {e}"
            }
            send_message(error_resp)
            print(f"[FATAL] Exception in main loop: {e}", file=sys.stderr)