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

// IP 수집
async function getPublicIP() { 
  try {
    const res = await fetch("https://api.ipify.org?format=json");
    const data = await res.json();
    return data.ip;
  } catch {
    return null;
  }
}

// 어떤 AI 서비스를 쓰고 있냐?
function detectAIService(url) {
  if (!url) return "unknown";
  const u = url.toLowerCase();
  if (u.includes("chat.openai.com") || u.includes("chatgpt.com")) return "ChatGPT";
  if (u.includes("bard.google.com") || u.includes("gemini.google.com")) return "Gemini";
  if (u.includes("claude.ai")) return "Claude";
  if (u.includes("copilot.microsoft.com")) return "Copilot";
  if (u.includes("perplexity.ai")) return "Perplexity";
  if (u.includes("poe.com")) return "Poe";
  if (u.includes("huggingface.co")) return "HuggingChat";
  return "unknown";
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
    const ip = await getPublicIP();
    if (ip) formData.append("client_ip", ip);
    formData.append("Files", blob, contentPayload.name);

// 브라우저/에이전트 메타데이터 추가
    const currentUrl = contentPayload.source_url || contentPayload.origin_url || "";
    const currentService = detectAIService(currentUrl);
    const tabData = contentPayload.tab || {};
    tabData.service = currentService;  // ← 서비스명 추가
    formData.append("tab", JSON.stringify(tabData));
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
    const ip = await getPublicIP();
    if (ip) formData.append("client_ip", ip);
    formData.append("text", raw || "(no text)");
    // const lengthInfo = raw ? `(text length=${raw.length})` : "(no text)";
    // formData.append("text", lengthInfo);

    const currentUrl = contentPayload.source_url || contentPayload.origin_url || "";
    const currentService = detectAIService(currentUrl);
    const tabData = contentPayload.tab || {};
    tabData.service = currentService;  // ← 서비스명 추가
    formData.append("tab", JSON.stringify(tabData));
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
    const keepAlive = setInterval(() => {}, 1000);
    // --- 추가: raw_text가 없을 때 대비 ---
    if (!payload.raw_text && !payload.text) {
      console.warn("[bg] empty payload text; skipping send");
      clearInterval(keepAlive);
      sendResponse({ ok: false, error: "empty text" });
      return;
    }
    forwardToServerFromContent(payload || {}, sender)
      .then(() => {
        console.log("[bg] text forwarded ok");
        clearInterval(keepAlive);
        sendResponse({ ok: true });
      })
      .catch(e => {
        console.error("[bg] text forward failed:", e.message || e);
        clearInterval(keepAlive);
        sendResponse({ ok: false, error: e.message });
      });
    return true;
  }
});

// keepalive
setInterval(() => { chrome.runtime.getPlatformInfo(() => {}); }, 20000);