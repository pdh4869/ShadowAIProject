# 텍스트 탐지 문제 해결 가이드

## 증상: "Fetch API cannot load" CSP 오류

### 원인
ChatGPT의 Content Security Policy가 페이지에서 직접 외부 서버로 fetch 요청을 차단합니다.

### 해결 확인 사항

#### 1. 확장 프로그램 상태 확인
```
chrome://extensions
→ PII Traffic Hook 확장이 "활성화" 상태인지 확인
→ "새로고침" 버튼 클릭
→ ChatGPT 페이지 완전 새로고침 (Ctrl+Shift+R)
```

#### 2. 콘솔 로그 확인

**ChatGPT 페이지 콘솔 (F12)**:
```
[content] ========== PII Agent 활성화 ==========
[content] URL: https://chatgpt.com/...
[content] 탐지 상태: 활성
```

**텍스트 입력 후 Enter 시**:
```
[content] ✓ Enter 키 전송
[content] 텍스트만 전송 (XX글자) -> TEXT_EVENT
```

**Background 콘솔 (chrome://extensions → 서비스 워커 "검사")**:
```
[bg] 메시지 수신: TEXT_EVENT (reqId: ...)
[bg] ✓ 네트워크 정보: {ip: "...", hostname: "..."}
[bg] 서버로 전송: http://127.0.0.1:9000/api/event
[bg] ✓ 서버 전송 성공
```

#### 3. 로컬 서버 확인
```bash
# 서버가 실행 중인지 확인
python LocalServer.py

# 브라우저에서 대시보드 접속
http://127.0.0.1:9000/dashboard
```

#### 4. 네트워크 탭 확인
```
F12 → Network 탭
→ "127.0.0.1" 필터 적용
→ 텍스트 전송 시 /api/event 요청이 보이는지 확인
```

**주의**: Network 탭에서는 background.js가 보내는 요청이므로 
"Initiator"가 "Service Worker"로 표시됩니다.

#### 5. 일반적인 문제들

**문제**: 콘솔에 [content] 로그가 전혀 없음
**해결**: 
- 확장 프로그램 재로드
- ChatGPT 페이지 완전 새로고침
- manifest.json의 content_scripts matches 확인

**문제**: [content] 로그는 있지만 [bg] 로그가 없음
**해결**:
- Service Worker가 sleep 상태일 수 있음
- chrome://extensions → 서비스 워커 "검사" 클릭하여 깨우기
- background.js 콘솔에서 직접 테스트:
  ```javascript
  chrome.runtime.sendMessage({type: "ping"}, (r) => console.log(r));
  ```

**문제**: [bg] 로그는 있지만 서버 전송 실패
**해결**:
- LocalServer.py가 실행 중인지 확인
- 방화벽이 9000 포트를 차단하는지 확인
- 서버 콘솔에서 요청 로그 확인

**문제**: CSP 오류가 계속 발생
**해결**:
- 이것은 정상입니다! 
- 현재 코드는 fetch를 사용하지 않습니다
- 다른 확장이나 스크립트가 간섭하는지 확인
- 시크릿 모드에서 테스트 (다른 확장 비활성화)

#### 6. 수동 테스트

**Background 콘솔에서 직접 테스트**:
```javascript
// 텍스트 이벤트 테스트
chrome.runtime.sendMessage({
  type: "TEXT_EVENT",
  payload: {
    source_url: "https://chatgpt.com/test",
    page_title: "Test",
    raw_text: "테스트 010-1234-5678",
    tab: { ua: navigator.userAgent }
  }
}, (response) => {
  console.log("응답:", response);
});
```

#### 7. Native Host 문제

**증상**: networkInfo가 "unknown"으로 표시
**해결**:
- README.md의 "Native Messaging Host 설정" 섹션 참조
- host.exe가 빌드되었는지 확인
- 레지스트리 등록 확인
- Chrome 완전 재시작

## 정상 동작 시나리오

1. ChatGPT에서 텍스트 입력
2. Enter 키 또는 전송 버튼 클릭
3. content.js가 텍스트 감지 → background.js로 전달
4. background.js가 Native Host 호출 → IP/호스트명 수집
5. background.js가 로컬 서버로 POST 요청
6. 서버가 PII 탐지 후 응답
7. 대시보드에 실시간 표시

**중요**: 모든 통신은 chrome.runtime API를 통해 이루어지며,
페이지에서 직접 fetch를 사용하지 않습니다!
