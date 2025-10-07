# README — PII 탐지 에이전트 (Chrome 확장 + 로컬 FastAPI 서버)

이 프로젝트는 **브라우저에서 입력/전송하려는 텍스트와 업로드한 파일**을 감지해, **개인정보(전화/이메일/주민번호/카드/계좌/IP/인명 NER/얼굴 이미지)**를 로컬에서 탐지하고, **대시보드**로 실시간 표시하는 도구입니다.  
구성은 다음 3가지로 이뤄집니다.

1) **Chrome 확장**: 전송 이벤트/파일 업로드를 가로채어 백그라운드로 넘김.  
2) **Native Messaging Host**: 로컬 IP 등 네트워크 정보를 안전하게 조회.  
3) **FastAPI 로컬 서버**: 텍스트/파일 분석, OCR/NER/얼굴탐지, 대시보드 제공.

---

## 1. 폴더/파일 개요

- `manifest.json` — 확장 설정(권한/스크립트/네이티브 권한).  
- `content.js` — 페이지 내 전송/업로드 감지 + 파일 수집/직렬화 + 포트 통신.  
- `background.js` — 허용 URL 필터링, 네이티브 호스트 호출(IP), 로컬 서버로 전송.  
- `com.example.pii_host.json` — **네이티브 호스트 매니페스트(설치 경로/허용 확장 ID)**.  
- `host.py` — 네이티브 호스트(표준 입력/출력으로 메시지 교환, IP/네트워크 조회).  
- `LocalServer.py` — FastAPI 서버/대시보드/REST API.  
- `Logic.py` — 파일 파싱, 정규식 탐지, NER, OCR, 얼굴탐지(MTCNN).

---

## 2. 사전 준비 (Python & 패키지)

```bash
pip install fastapi uvicorn[standard] pillow numpy opencv-python pymupdf python-docx             pycryptodome requests easyocr mtcnn transformers torch torchvision sentencepiece
```

---

## 3. 로컬 서버 실행

```bash
python LocalServer.py
```

- 대시보드: **http://127.0.0.1:9000/dashboard**  
- 주요 API: `/api/event`, `/api/file_collect`, `/api/combined`, `/api/detections`

---

## 4. Chrome 확장 설치

1) **개발자 모드** → `chrome://extensions`  
2) **압축해제된 확장 프로그램 로드** → `manifest.json` 폴더 선택  
3) 설치 후 확장 **ID** 확인

---

## 5. Native Messaging Host 설정

### 매니페스트 수정
`com.example.pii_host.json`에서 `"path"`를 host.exe 절대경로로 수정,  
`"allowed_origins"`에 확장 ID 추가.

### 빌드 예시
```bash
pyinstaller --onefile host.py --name host
```

---

## 6. 동작 흐름

1) **content.js** — 텍스트/파일 감지 → COMBINED_EVENT 전송  
2) **background.js** — IP 조회 → FastAPI로 POST 전송  
3) **LocalServer.py** — 텍스트+파일 분석 → 대시보드 표시

---

## 7. 탐지 항목

- 전화번호, 이메일, 주민번호, 여권, 계좌, 카드, IP, 인명, 조직, 위치  
- 이미지 내 OCR + 얼굴탐지(MTCNN)  
- PDF/DOCX 내 이미지·텍스트 추출

---

## 8. 테스트

1) 서버 실행  
2) 확장 설치 후 예시 텍스트 입력  
3) 파일 업로드 시 탐지 로그 확인  
4) 대시보드에서 결과 확인

---

## 9. 보안

- 전송 대상: **127.0.0.1:9000 (로컬 전용)**  
- `send_to_backend`는 기본 비활성화 (원격 전송 없음)

---

## 10. 커스터마이징

- 허용 URL: `background.js`의 `isAllowedLLMUrl`  
- 지원 파일형식: `content.js`의 `allowed` 배열  
- 정규식/NER: `Logic.py` 함수 내부

---

## 11. 트러블슈팅

- 대시보드 미표시 → 허용 URL 확인, 서버 로그 확인  
- IP가 unknown → `com.example.pii_host.json` 설정 확인  
- 파일 미탐지 → OCR, MTCNN 라이브러리 설치 확인

---

## 12. 라이선스

- 연구/로컬용 예시 코드입니다. 상용 사용 시 개인정보보호법을 준수하세요.
<<<<<<< HEAD

---

# 네이티브 메시징 호스트 적용 가이드 (Windows 중심, Chrome MV3)

> 이 문서는 **네이티브 호스트( `host.py` / `host.exe` )를 Chrome 확장과 연결**하는 전 과정을 **정확하고 재현 가능하게** 정리했습니다.  
> 핵심은 ① **호스트 실행 파일 준비**, ② **매니페스트(JSON) 작성**, ③ **레지스트리 등록**, ④ **확장에서 연결/테스트** 입니다.

---

## 0) 용어 요약
- **네이티브 호스트**: 로컬 OS에서 실행되는 프로그램(여기서는 `host.py`를 `host.exe`로 빌드한 것). 확장과 **표준입출력(StdIO)** 으로 JSON 메시지를 주고받습니다.
- **호스트 매니페스트(JSON)**: Chrome이 “어떤 실행 파일을 어떤 확장에 허용할지” 아는 **등록 카드**입니다.
- **호스트 이름**: 예) `com.example.pii_host`. 확장에서 이 이름으로 연결합니다.

---

## 1) 호스트 실행 파일 준비 (권장: PyInstaller)
1. Python 패키지 설치(필요 시)
   ```bash
   pip install pyinstaller
   ```
2. 빌드
   ```bash
   pyinstaller --onefile host.py --name host
   ```
   - 결과물: `dist/host.exe`  
   - **매니페스트의 `"path"`는 이 `host.exe`의 절대경로**를 가리켜야 합니다.

> 참고: `.py` 그대로도 실행은 가능하지만, **매니페스트의 `"path"`는 반드시 실행 가능한 파일**을 가리켜야 합니다. (*.bat*로 래핑하는 방식도 가능하지만, 운영 안정성/권장 관행상 `.exe` 빌드를 추천합니다.)

---

## 2) 호스트 매니페스트(JSON) 작성
예시 파일명: `com.example.pii_host.json`
```json
{
  "name": "com.example.pii_host",
  "description": "PII Agent Native Host",
  "type": "stdio",
  "path": "C:/YOUR/ABSOLUTE/PATH/TO/dist/host.exe",
  "allowed_origins": ["chrome-extension://__YOUR_EXTENSION_ID__/"]
}
```
- `"name"`: **호스트 이름**. 확장에서 이 문자열로 연결합니다.
- `"type": "stdio"`: 표준입출력 방식 고정.
- `"path"`: **절대경로**. 백슬래시는 `\\` 혹은 슬래시(`/`)로 표기.
- `"allowed_origins"`: 이 호스트 사용을 허용할 **확장 ID** 배열. 개발자 모드에서 `chrome://extensions` → 해당 확장 카드의 **ID**를 복사해 넣으세요.

> **중요**: `"allowed_origins"`가 확장 ID와 일치하지 않으면 **Access forbidden** 에러가 납니다.

---

## 3) Windows 레지스트리 등록 (Chrome이 매니페스트를 찾도록)
Chrome(또는 Edge)은 **레지스트리 키**에 등록된 경로에서 **매니페스트(JSON)** 를 찾습니다.  
다음 중 하나를 사용하세요.

### 3-1) 사용자 단위 등록(HKCU) — 권장
PowerShell(관리자 권한 불필요)에서 아래 실행:
```powershell
# 경로는 본인 환경에 맞게 수정
$manifest = "C:\YOUR\ABSOLUTE\PATH\com.example.pii_host.json"
reg add "HKCU\Software\Google\Chrome\NativeMessagingHosts\com.example.pii_host" /ve /t REG_SZ /d "$manifest" /f
```
- 키가 생성되고 **기본값(Default)** 이 매니페스트 파일 경로로 설정됩니다.

### 3-2) 시스템 단위 등록(HKLM) — 모든 사용자 공통
관리자 권한 PowerShell:
```powershell
$manifest = "C:\YOUR\ABSOLUTE\PATH\com.example.pii_host.json"
reg add "HKLM\Software\Google\Chrome\NativeMessagingHosts\com.example.pii_host" /ve /t REG_SZ /d "$manifest" /f
```
> 회사 PC처럼 다중 사용자 환경이면 HKLM을 사용할 수 있습니다.

### 3-3) Microsoft Edge를 사용하는 경우
```powershell
# 사용자
reg add "HKCU\Software\Microsoft\Edge\NativeMessagingHosts\com.example.pii_host" /ve /t REG_SZ /d "C:\...\com.example.pii_host.json" /f
# 또는 시스템
reg add "HKLM\Software\Microsoft\Edge\NativeMessagingHosts\com.example.pii_host" /ve /t REG_SZ /d "C:\...\com.example.pii_host.json" /f
```

> **레지스트리 경로만 등록**하면 매니페스트(JSON)는 **어디에 있어도** 됩니다(네트워크 드라이브보다는 로컬 권장).

---

## 4) Chrome 확장 측 준비(확인 포인트)
- `manifest.json`에 **권한** 포함:
  ```json
  {
    "manifest_version": 3,
    "name": "...",
    "version": "1.0.0",
    "permissions": ["nativeMessaging", "storage", "scripting", "activeTab", "alarms"],
    "...": "..."
  }
  ```
- 실제 연결은 `chrome.runtime.sendNativeMessage` 또는 `chrome.runtime.connectNative` 사용.
  - **단발 요청**(요청→응답 1회): `sendNativeMessage`
  - **장기 연결**(스트림/여러 메시지): `connectNative`

### 예시(개발자 콘솔에서 바로 테스트)
1) `chrome://extensions` → 대상 확장 → **서비스 워커(백그라운드)** “검사” 클릭 → Console 탭
2) 아래 코드로 테스트:
```js
// 단발 요청
chrome.runtime.sendNativeMessage(
  'com.example.pii_host',
  { cmd: 'get_ip' },
  (resp) => { console.log('lastError=', chrome.runtime.lastError, 'resp=', resp); }
);

// 장기 연결
const port = chrome.runtime.connectNative('com.example.pii_host');
port.onMessage.addListener(msg => console.log('host->ext', msg));
port.onDisconnect.addListener(() => console.log('port disconnected', chrome.runtime.lastError));
port.postMessage({ cmd: 'get_info' });
```
- 정상이라면 `lastError`가 `undefined`이고, `resp`에 IP/네트워크 정보가 찍힙니다.

---

## 5) 통신 프로토콜(매우 중요)
네이티브 메시징은 **메시지 앞에 4바이트(리틀엔디언) 길이**를 붙여 StdIO로 주고받습니다.
- 호스트는 **stdin**에서 [4바이트 길이]→[길이만큼의 JSON]을 읽고, 처리 후 **stdout**으로 같은 포맷으로 응답합니다.
- JSON **최대 크기 1MB** 권장(Chrome 한도).
- UTF-8, BOM 없이.

> 본 프로젝트의 `host.py`는 위 규칙을 준수하며, 모든 I/O를 `host_log.txt`에 남기도록 되어 있습니다(디버깅에 유용).

---

## 6) 체크리스트 (한 번에 점검)
- [ ] `dist/host.exe` 생성 완료 (직접 실행 시 콘솔 에러 없음)
- [ ] `com.example.pii_host.json`의 `"path"`가 **절대경로**로 `host.exe`를 가리킴
- [ ] `"allowed_origins"`에 **현재 확장 ID**가 정확히 들어감(맨 뒤 `/` 포함)
- [ ] 레지스트리 키가 정확히 생성됨(HKCU/HKLM 중 택1)
- [ ] `manifest.json`에 `"nativeMessaging"` 권한 존재
- [ ] 백그라운드 콘솔에서 `sendNativeMessage` 테스트 성공

---

## 7) 자주 나는 오류 & 해법
| 증상/메시지 | 원인 | 해결 |
|---|---|---|
| `Specified native messaging host not found.` | **레지스트리 미등록** 또는 **호스트 이름 오타** | 레지스트리 키(`...NativeMessagingHosts\com.example.pii_host`) 존재/오타 점검 |
| `Access to the specified native messaging host is forbidden.` | `allowed_origins`에 **확장 ID 불일치** | 확장 ID 재확인, 매니페스트 JSON 수정 후 Chrome 재시작 |
| `Error when communicating with the native messaging host.` | 프로토콜 불일치(4바이트 길이 prefix 누락/깨짐), JSON 파싱 실패 | `host.py` 표준 I/O 구현 확인, 로그 확인, 메시지 크기/인코딩 점검 |
| `Native host has exited.` | 호스트 크래시/예외 종료 | `host_log.txt` 확인, 독립 실행 테스트(직접 `host.exe` 실행) |
| 응답이 오랜 지연/타임아웃 | 호스트 내부 처리 지연 | 네트워크/파일 I/O 동기 처리 개선, 필요 시 비동기/스레딩 고려 |

> Chrome/Edge를 **재시작**해야 변경(레지스트리/매니페스트)이 반영되는 경우가 많습니다.

---

## 8) (선택) .reg 파일로 간편 등록
`register_host.reg` 파일로 아래 내용을 저장 후 **더블클릭**:
```reg
Windows Registry Editor Version 5.00

[HKEY_CURRENT_USER\Software\Google\Chrome\NativeMessagingHosts\com.example.pii_host]
@="C:\\YOUR\\ABSOLUTE\\PATH\\com.example.pii_host.json"
```
> 역슬래시는 `\\`로 이스케이프해야 합니다.

---

## 9) macOS / Linux 참고(요약)
- **macOS 매니페스트 경로(유저)**: `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/`  
- **Linux 매니페스트 경로(유저)**: `~/.config/google-chrome/NativeMessagingHosts/`  
- 위 경로에 `com.example.pii_host.json`을 두면 별도 레지스트리 없이 동작합니다.  
- `"path"`는 실행 가능 파일(예: `./host` 또는 `python3 /abs/path/host.py`)의 **절대경로**를 적어주세요. 실행 권한(`chmod +x`) 확인 필수.

---

## 10) 운영 팁
- **확장 ID 고정**이 필요하면(배포 시) MV3에서 `key` 속성을 활용해 ID를 고정하는 방법이 있습니다. 다만 개발 단계에서는 불필요하며, 조직 배포 정책과 함께 검토하세요.
- 서비스워커는 유휴 시 중단됩니다. **장기 연결(port)** 을 쓰면 필요 시 자동 재기동되지만, 중요한 초기화는 메시지 수신 시 처리하세요.
- 호스트에서 민감정보를 다룰 경우, **호스트 실행 경로/권한**을 제한하고 로그 파일 접근 권한을 관리하세요.
=======
>>>>>>> 8051987319073d1c9d454d049afb8312df363b25
