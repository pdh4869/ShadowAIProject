import sys
import json
import struct
import socket
import winreg
import requests
import subprocess

SERVER_URL = "http://127.0.0.1:8123/api/event"

# ---- Native Messaging I/O ----
def read_message():
    try:
        raw_length = sys.stdin.buffer.read(4)
        if not raw_length:
            return None
        message_length = struct.unpack("I", raw_length)[0]
        message = sys.stdin.buffer.read(message_length).decode("utf-8", errors="ignore")
        return json.loads(message)
    except Exception as e:
        print(f"[host] read_message error: {e}", file=sys.stderr)
        return None

def send_message(message: dict):
    try:
        data = json.dumps(message, ensure_ascii=False).encode("utf-8")
        sys.stdout.buffer.write(struct.pack("I", len(data)))
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()
    except Exception as e:
        print(f"[host] send_message error: {e}", file=sys.stderr)

# ---- 네트워크 정보 수집 ----
_TCPIP_IFACES = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"

def _reg_query_str(key, name):
    try:
        val, _ = winreg.QueryValueEx(key, name)
        if isinstance(val, list):
            return [v for v in val if v]
        if isinstance(val, str):
            return [v for v in val.split(",") if v]
    except Exception:
        return []
    return []

def get_dns_servers():
    servers = set()
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _TCPIP_IFACES) as root:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(root, i); i += 1
                    with winreg.OpenKey(root, sub) as k:
                        for nm in ("NameServer", "DhcpNameServer"):
                            for s in _reg_query_str(k, nm):
                                if s.strip():
                                    servers.update([x.strip() for x in s.split(",") if x.strip()])
                except OSError:
                    break
    except Exception:
        pass
    return sorted(servers)

def get_default_gateways():
    gws = set()
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _TCPIP_IFACES) as root:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(root, i); i += 1
                    with winreg.OpenKey(root, sub) as k:
                        for nm in ("DefaultGateway", "DhcpDefaultGateway"):
                            for gw in _reg_query_str(k, nm):
                                if gw.strip():
                                    gws.update([x.strip() for x in gw.split(",") if x.strip()])
                except OSError:
                    break
    except Exception:
        pass
    return sorted(gws)

def get_interface_ips():
    interfaces = []
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _TCPIP_IFACES) as root:
            i = 0
            while True:
                try:
                    guid = winreg.EnumKey(root, i); i += 1
                    with winreg.OpenKey(root, guid) as k:
                        ips = _reg_query_str(k, "IPAddress") or _reg_query_str(k, "DhcpIPAddress")
                        ips = [ip for ip in ips if ip and ip not in ("0.0.0.0", "127.0.0.1")]
                        if ips:
                            interfaces.append({"guid": guid, "ips": ips})
                except OSError:
                    break
    except Exception:
        pass

    # active IP 최소 보장
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        active_ip = s.getsockname()[0]
        s.close()
        if active_ip:
            interfaces.insert(0, {"guid": "active", "ips": [active_ip]})
    except Exception:
        pass

    # fallback: ipconfig
    if not interfaces:
        try:
            out = subprocess.check_output("ipconfig", shell=True, encoding="cp437", errors="ignore")
            lines = out.splitlines()
            ips = []
            for line in lines:
                if "IPv4" in line and ":" in line:
                    ip = line.split(":")[-1].strip()
                    if ip and not ip.startswith("127."):
                        ips.append(ip)
            if ips:
                interfaces.append({"guid": "ipconfig", "ips": ips})
        except Exception:
            pass

    return interfaces

def gather_network_info():
    return {
        "interfaces": get_interface_ips(),
        "gateway": get_default_gateways(),
        "dns": get_dns_servers(),
    }

# ---- 서버 전송 ----
def forward_to_server(payload):
    try:
        resp = requests.post(SERVER_URL, json=payload, timeout=5)
        return {"ok": True, "status": resp.status_code}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ---- 메인 루프 ----
if __name__ == "__main__":
    print("[host] Native host started, waiting for messages...", file=sys.stderr)
    while True:
        msg = read_message()
        if msg is None:
            continue
        try:
            req_id = msg.get("reqId")
            cmd = msg.get("cmd")

            if cmd == "get_info":
                data = {"network": gather_network_info()}
                resp = {"reqId": req_id, "ok": True, "data": data}
                send_message(resp)
            else:
                result = forward_to_server(msg)
                resp = {"reqId": req_id, "ok": True, "result": result}
                send_message(resp)

        except Exception as e:
            error_resp = {
                "reqId": msg.get("reqId") if msg else None,
                "ok": False,
                "error": f"{type(e).__name__}: {e}"
            }
            send_message(error_resp)
