import json
import struct
import subprocess

def send_message(proc, message):
    data = json.dumps(message).encode('utf-8')
    proc.stdin.write(struct.pack('I', len(data)))
    proc.stdin.write(data)
    proc.stdin.flush()

def read_message(proc):
    raw_length = proc.stdout.read(4)
    if not raw_length:
        return None
    message_length = struct.unpack('I', raw_length)[0]
    message = proc.stdout.read(message_length).decode('utf-8')
    return json.loads(message)

# host.py 실행
proc = subprocess.Popen(
    ['python', 'host.py'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# get_ip 명령 테스트
test_msg = {"cmd": "get_ip", "args": {}, "reqId": 123}
print(f"전송: {test_msg}")
send_message(proc, test_msg)

response = read_message(proc)
print(f"응답: {response}")

proc.terminate()
