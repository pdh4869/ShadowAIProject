// background.js — 페이지 CSP 우회해서 로컬 에이전트로 전송
const AGENT_URL = "http://127.0.0.1:18080/collect";
const MARK_HEADER = "X-LLM-Collector";

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (!msg || msg.type !== "COLLECT") return;

  (async () => {
    try {
      const res = await fetch(AGENT_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json", [MARK_HEADER]: "1" },
        body: JSON.stringify(msg.payload)
      });
      sendResponse({ ok: res.ok, status: res.status });
    } catch (e) {
      sendResponse({ ok: false, error: String(e) });
    }
  })();

  return true; // async 응답 허용
});
