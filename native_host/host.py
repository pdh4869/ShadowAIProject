# host.py (붙여넣기 후 기존 파일 덮어쓰기)
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
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
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
    log_file = open("C:\\Users\\USER\\Desktop\\Py_server\\Py_server\\native_host\\host_log.txt", "a", encoding="utf-8")
    log_file.write(f"\n=== Host started at {datetime.datetime.now()} ===\n")
    log_file.flush()
    
    while True:
        msg = read_message()
        if msg is None:
            continue
        log_file.write(f"Received: {msg}\n")
        log_file.flush()
        
        req_id = msg.get("reqId", 0)
        cmd = msg.get("cmd", "")
        if cmd == "get_info":
            network_data = gather_network_info()
            response = {"reqId": req_id, "ok": True, "data": {"network": network_data}}
            log_file.write(f"Sending: {response}\n")
            log_file.flush()
            send_message(response)
        elif cmd == "get_ip":
            ip = get_local_ip()
            response = {"reqId": req_id, "ok": True, "data": {"ip": ip}}
            log_file.write(f"Sending IP: {response}\n")
            log_file.flush()
            send_message(response)
        else:
            response = {"reqId": req_id, "ok": False, "error": "Unknown command"}
            log_file.write(f"Unknown command: {response}\n")
            log_file.flush()
            send_message(response)
