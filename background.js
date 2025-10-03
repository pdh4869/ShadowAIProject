// ===== background.js (LocalServer 연동 전용) =====

// 서버 엔드포인트
const SERVER_EVENT_ENDPOINT = "http://127.0.0.1:8000/mask-text/";
const SERVER_FILE_ENDPOINT  = "http://127.0.0.1:8000/mask-files/";
const MARK_HEADER = "X-LLM-Collector";

// payload 정규화
function normalizePayload(p = {}, sender) {
  const url  = p.source_url || p.url || sender?.url || (sender?.tab && sender.tab.url) || "";
  const text = p.text || p.raw_text || "";
  let files  = p.files;
  if (typeof files === "string") {
    try {
      const parsed = JSON.parse(files);
      files = Array.isArray(parsed) ? parsed : [String(parsed)];
    } catch { files = [files]; }
  }
  if (!Array.isArray(files)) files = [];
  const llm  = p.llm || undefined;
  const tab  = p.tab || undefined;
  return { url, text, files, llm, tab };
}

// 파일 전송
async function forwardFileContent(contentPayload) {
  try {
    const byteCharacters = atob(contentPayload.data_b64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: contentPayload.mime });

    const formData = new FormData();
    formData.append("Files", blob, contentPayload.name);

// 브라우저/에이전트 메타데이터 추가
    if (contentPayload.tab) {
	formData.append("tab", JSON.stringify(contentPayload.tab));
    }
    if (contentPayload.agent_id) {
	formData.append("agent_id", contentPayload.agent_id);
    }
    if (contentPayload.origin_url) {
	formData.append("source_url", contentPayload.origin_url);
    }

    const res = await fetch(SERVER_FILE_ENDPOINT, { method: "POST", body: formData });
    if (!res.ok) throw new Error("HTTP " + res.status);
    console.log("[server] file forwarded ok", { file: contentPayload.name });
  } catch (e) {
    console.error("[server] file forward failed:", e?.message || e);
  }
}

// 텍스트/메타데이터 전송
async function forwardToServerFromContent(contentPayload, sender) {
  try {
    const formData = new FormData();
    const raw = contentPayload.raw_text || contentPayload.text || "";
    const lengthInfo = raw ? `(text length=${raw.length})` : "(no text)";
    formData.append("text", lengthInfo);

    if (contentPayload.tab) {
      formData.append("tab", JSON.stringify(contentPayload.tab));
    }
    if (contentPayload.agent_id) {
      formData.append("agent_id", contentPayload.agent_id);
    }
    if (contentPayload.source_url) {
      formData.append("source_url", contentPayload.source_url);
    }

    const res = await fetch(SERVER_EVENT_ENDPOINT, { method: "POST", body: formData });
    if (!res.ok) throw new Error("HTTP " + res.status);
    console.log("[server] text forwarded ok");
  } catch (e) {
    console.error("[server] text forward failed:", e?.message || e);
  }
}

// 허용 LLM 도메인
const ALLOWED_LLM_HOSTS = ["chat.openai.com","chatgpt.com","gemini.google.com"];
function isAllowedLLMUrl(url) {
  try {
    if (!url) return false;
    const u = new URL(url);
    const host = u.hostname.toLowerCase();
    return ALLOWED_LLM_HOSTS.some(allowed => host.endsWith(allowed));
  } catch { return false; }
}

// 메시지 리스너
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  const t = msg?.type;
  const payload = msg.payload;
  if (t !== "PII_EVENT" && t !== "FILE_COLLECT") return;

  const url = sender?.tab?.url || sender?.url || payload?.source_url;
  if (!isAllowedLLMUrl(url)) {
    console.log("[bg] blocked: not an allowed host:", url);
    return;
  }
  if (t === "FILE_COLLECT") {
    console.log("[bg] file received:", payload.name);
    forwardFileContent(payload);
    sendResponse({ ok: true });
    return;
  }
  if (t === "PII_EVENT") {
    console.log("[bg] PII event received:", url);
    forwardToServerFromContent(payload || {}, sender);
    return true;
  }
});

// keepalive
setInterval(() => { chrome.runtime.getPlatformInfo(() => {}); }, 20000);