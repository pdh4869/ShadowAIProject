# host.py (수정된 최종 코드)
import sys
import json
import struct
import socket
import platform
import subprocess
import re
import datetime

def read_message():
    """크롬 확장 프로그램으로부터 메시지를 읽는 함수"""
    try:
        # 메시지 길이를 나타내는 4바이트를 먼저 읽음
        raw_length = sys.stdin.buffer.read(4)
        if not raw_length:
            return None
        message_length = struct.unpack("I", raw_length)[0]
        # 실제 메시지를 읽고 디코딩
        message = sys.stdin.buffer.read(message_length).decode("utf-8", errors="ignore")
        return json.loads(message)
    except Exception:
        return None

def send_message(message):
    """크롬 확장 프로그램으로 메시지를 보내는 함수"""
    try:
        # 메시지를 JSON 형식으로 인코딩
        data = json.dumps(message).encode("utf-8")
        # 메시지 길이를 4바이트로 패킹하여 먼저 전송
        sys.stdout.buffer.write(struct.pack("I", len(data)))
        # 실제 메시지 전송
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()
    except Exception:
        pass

def get_local_ip():
    """로컬 IP 주소를 얻는 함수"""
    try:
        # 외부 서버(구글 DNS)에 연결을 시도하여 사용하는 네트워크 인터페이스의 IP를 얻음
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if not ip.startswith('127.') and ip != '0.0.0.0':
             return ip
    except Exception:
        pass
    try:
        # 위 방법 실패 시, 호스트 이름을 통해 IP를 얻음
        ip = socket.gethostbyname(socket.gethostname())
        if not ip.startswith('127.') and ip != '0.0.0.0':
             return ip
    except Exception:
        pass
    return "Unknown"

def get_gateway_and_dns():
    """게이트웨이와 DNS 서버 정보를 얻는 함수 (Windows 기준)"""
    sysname = platform.system()
    gw, dns = [], []
    try:
        if sysname == "Windows":
            # 'ipconfig /all' 명령어 실행 결과를 파싱
            out = subprocess.check_output(["ipconfig", "/all"], universal_newlines=True, errors='ignore')
            gw = re.findall(r"Default Gateway[.\s:]*([\d\.]+)", out)
            dns_block = re.findall(r"DNS Servers[.\s:]*([\d\.\n\s]+)", out)
            if dns_block:
                dns = re.findall(r"(\d+\.\d+\.\d+\.\d+)", dns_block[0])
        # (macOS/Linux는 현재 구현에서 제외)
    except Exception:
        pass
    return {"gateway": gw, "dns": dns}

def get_computer_name():
    """컴퓨터의 호스트 이름을 얻는 함수"""
    return platform.node()

def gather_network_info():
    """모든 네트워크 정보를 수집하고 종합하는 함수"""
    ip = get_local_ip()
    gd = get_gateway_and_dns()
    return {
        "platform": platform.system(),
        "hostname": get_computer_name(),
        "interfaces": [{"name":"local","ips":[ip]}],
        "gateway": gd.get("gateway",[]),
        "dns": gd.get("dns",[])
    }

def main():
    """
    프로그램의 메인 로직.
    한 번의 메시지를 처리하고 종료되도록 while 루프를 제거.
    """
    log_file = None
    try:
        # 실행 파일과 같은 위치에 로그 파일 생성
        log_file = open("host_log.txt", "a", encoding="utf-8")
        log_file.write(f"\n=== Host started at {datetime.datetime.now()} ===\n")
    except Exception:
        pass # 로그 파일 생성 실패 시에도 프로그램은 계속 동작

    # 메시지를 한 번만 읽음
    msg = read_message()
    if msg is None:
        if log_file:
            log_file.write("No message received. Exiting.\n")
        return # 메시지가 없으면 바로 종료

    if log_file:
        log_file.write(f"Received: {msg}\n")

    req_id = msg.get("reqId", 0)
    cmd = msg.get("cmd", "")

    response = None
    # 'get_full_info' 명령어에만 응답하도록 로직 단순화
    if cmd == "get_full_info":
        network_data = gather_network_info()
        response = {"reqId": req_id, "ok": True, "data": network_data}
        if log_file:
            log_file.write(f"Sending Full Info: {response}\n")
    # 'get_info', 'get_ip' 등 이전 명령어는 'get_full_info'로 통합되었으므로 제거 가능
    else:
        response = {"reqId": req_id, "ok": False, "error": "Unknown command"}
        if log_file:
            log_file.write(f"Unknown command: {response}\n")

    # 응답이 생성되었으면 전송
    if response:
        send_message(response)

    if log_file:
        log_file.write("=== Host finished ===\n")
        log_file.close() # 프로그램 종료 전 로그 파일 닫기

if __name__ == "__main__":
    # 프로그램 시작 시 main 함수를 한 번만 호출
    main()