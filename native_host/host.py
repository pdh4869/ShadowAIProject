# host.py (로그 경로 및 IP 획득 로직이 수정된 전체 코드)
import sys
import json
import struct
import socket
import platform
import subprocess
import re

def read_message():
    try:
        raw_length = sys.stdin.buffer.read(4)
        if not raw_length:
            return None
        message_length = struct.unpack("I", raw_length)[0]
        message = sys.stdin.buffer.read(message_length).decode("utf-8", errors="ignore")
        return json.loads(message)
    except Exception:
        return None

def send_message(message):
    try:
        data = json.dumps(message).encode("utf-8")
        sys.stdout.buffer.write(struct.pack("I", len(data)))
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()
    except Exception:
        pass

def get_local_ip():
    # 1. 외부 연결 시도를 통한 아웃바운드 IP 획득 (가장 정확한 인터페이스 IP)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 외부 서버에 연결 시도 (실제 통신은 하지 않음, 경로 확인용)
        s.connect(("8.8.8.8", 80)) 
        ip = s.getsockname()[0]
        s.close()
        # 루프백 주소가 아닌 유효한 IP인 경우 반환
        if not ip.startswith('127.') and ip != '0.0.0.0':
             return ip
    except Exception:
        pass # 실패하면 2차 시도로 넘어감
        
    # 2. 로컬 호스트 이름을 이용한 IP 획득 (fallback)
    try:
        ip = socket.gethostbyname(socket.gethostname())
        # 루프백 주소가 아닌 유효한 IP인 경우 반환
        if not ip.startswith('127.') and ip != '0.0.0.0':
             return ip
    except Exception:
        pass
        
    # 3. 모든 시도 실패 시
    return "Unknown"

def get_gateway_and_dns():
    sysname = platform.system()
    gw = []
    dns = []
    try:
        if sysname == "Windows":
            out = subprocess.check_output(["ipconfig", "/all"], universal_newlines=True, errors='ignore')
            gw = re.findall(r"Default Gateway[.\s:]*([\d\.]+)", out)
            dns = re.findall(r"DNS Servers[.\s:]*([\d\.\n\s]+)", out)
            # flatten dns block
            if dns:
                dns = re.findall(r"(\d+\.\d+\.\d+\.\d+)", dns[0])
        else:
            # Linux / Mac
            try:
                rt = subprocess.check_output(["ip", "route"], universal_newlines=True, errors='ignore')
                gw = re.findall(r"default via (\d+\.\d+\.\d+\.\d+)", rt)
            except Exception:
                gw = []
            try:
                with open("/etc/resolv.conf","r") as f:
                    resolv = f.read()
                dns = re.findall(r"nameserver\s+([\d\.]+)", resolv)
            except Exception:
                dns = []
    except Exception:
        pass
    return {"gateway": gw, "dns": dns}

def gather_network_info():
    ip = get_local_ip()
    gd = get_gateway_and_dns()
    interfaces = [{"name":"local","ips":[ip]}] 
    return {
        "platform": platform.system(),
        "interfaces": interfaces,
        "gateway": gd.get("gateway",[]),
        "dns": gd.get("dns",[])
    }

if __name__ == "__main__":
    import datetime
    
    # [로그 파일 경로 및 에러 처리 수정]
    try:
        # 실행 파일이 있는 곳에 상대 경로로 'host_log.txt'를 생성합니다. (로그 문제 해결)
        log_file = open("host_log.txt", "a", encoding="utf-8") 
    except Exception as e:
        import sys
        print(f"Error opening log file: {e}", file=sys.stderr)
        log_file = None 
    
    if log_file:
        log_file.write(f"\n=== Host started at {datetime.datetime.now()} ===\n")
        log_file.flush()
    
    while True:
        msg = read_message()
        if msg is None:
            continue
            
        # 로그 파일이 열렸을 경우에만 기록
        if log_file:
            log_file.write(f"Received: {msg}\n")
            log_file.flush()
        
        req_id = msg.get("reqId", 0)
        cmd = msg.get("cmd", "")
        if cmd == "get_info":
            network_data = gather_network_info()
            response = {"reqId": req_id, "ok": True, "data": {"network": network_data}}
            if log_file:
                log_file.write(f"Sending: {response}\n")
                log_file.flush()
            send_message(response)
        elif cmd == "get_ip":
            ip = get_local_ip()
            response = {"reqId": req_id, "ok": True, "data": {"ip": ip}}
            if log_file:
                log_file.write(f"Sending IP: {response}\n")
                log_file.flush()
            send_message(response)
        else:
            response = {"reqId": req_id, "ok": False, "error": "Unknown command"}
            if log_file:
                log_file.write(f"Unknown command: {response}\n")
                log_file.flush()
            send_message(response)