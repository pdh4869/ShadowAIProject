// background.js
// 역할: content.js / pagehooks.js에서 보내오는 COLLECT / DETECT / file_meta 메시지를 서버로 포워딩

const SERVER_URL = "http://127.0.0.1:18080"; // 서버 포트(통일)

/**
 * 메시지 구조:
 * - COLLECT: { kind: 'text' | 'file' | 'file_meta', ... }
 * - DETECT:  { url, timestamp, context, detections, snippet }
 */
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!msg || !msg.type) return;

  if (msg.type === "COLLECT" || msg.type === "DETECT") {
    // 기본 경로 결정
    let path;
    if (msg.type === "DETECT") {
      path = "detections";
    } else if (msg.type === "COLLECT") {
      // 파일 업로드 메타는 별도 엔드포인트로 전달
      if (msg.payload?.kind === "file_meta") {
        path = "upload_meta";
      } else {
        path = "collect";
      }
    }

    fetch(`${SERVER_URL}/${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(msg.payload)
    })
      .then(async (res) => {
        sendResponse({ ok: res.ok });
      })
      .catch((err) => {
        console.error("[BG] 서버 전송 실패", err);
        sendResponse({ ok: false, error: String(err) });
      });

    return true; // 비동기 응답을 사용함을 chrome에 알림
  }
});
