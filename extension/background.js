// ===== background.js (최종 완성본: 파일 내용 8123/9090 듀얼 전송 및 Native Host JSON 전송) =====

// ===== Native host / Server Endpoints =====
const HOST_NAME = "com.example.pii_host";
let nativePort = null;
let reqSeq = 1;
const pending = new Map();

// 메타데이터 전송 엔드포인트 (기존 PII_EVENT)
const SERVER_EVENT_ENDPOINT = "http://127.0.0.1:8123/api/event"; 
// 파일 내용 전송 엔드포인트 (FastAPI 디스크 저장용)
const SERVER_FILE_ENDPOINT = "http://127.0.0.1:8123/api/file_collect"; 
// ★ NEW: 파일 내용 전송 엔드포인트 (외부 탐지 모듈용) ★
const FILE_DETECT_ENDPOINT = "http://127.0.0.1:9090/file_detect"; 

const MARK_HEADER = "X-LLM-Collector"; // 파일 전송 시 사용

function connectNative() {
  try {
    console.log("[native] connectNative ->", HOST_NAME);
    nativePort = chrome.runtime.connectNative(HOST_NAME);

    nativePort.onMessage.addListener((msg) => {
      const id = msg && msg.reqId;
      if (id && pending.has(id)) {
        const { resolve, reject } = pending.get(id);
        pending.delete(id);
        msg.ok ? resolve(msg) : reject(new Error(msg.error || "native error"));
      } else {
        console.log("[native] unsolicited:", msg);
      }
    });

    nativePort.onDisconnect.addListener(() => {
      const err = chrome.runtime.lastError?.message || "disconnected";
      console.warn("[native] disconnected:", err);
      nativePort = null;
      for (const [, p] of pending) p.reject(new Error("native disconnected"));
      pending.clear();
      setTimeout(connectNative, 1200); // 재연결 시도
    });
  } catch (e) {
    console.error("[native] connect error:", e);
    setTimeout(connectNative, 2000);
  }
}
connectNative();

function callNative(cmd, payload = {}, timeoutMs = 5000) { // 타임아웃 5초로 약간 여유
  return new Promise((resolve, reject) => {
    if (!nativePort) return reject(new Error("nativePort not connected"));
    const reqId = reqSeq++;
    pending.set(reqId, { resolve, reject });
    try {
      nativePort.postMessage({ reqId, cmd, payload }); // JSON 객체를 전송
    } catch (e) {
      pending.delete(reqId);
      return reject(e);
    }
    setTimeout(() => {
      if (pending.has(reqId)) {
        pending.delete(reqId);
        reject(new Error("native call timeout"));
      }
    }, timeoutMs);
  });
}

function normalizePayload(p = {}, sender) {
  const url =
    p.source_url || p.url || sender?.url || (sender?.tab && sender.tab.url) || "";
  const text = p.text || p.raw_text || "";
  let files = p.files;
  if (typeof files === "string") {
    try {
      const parsed = JSON.parse(files);
      files = Array.isArray(parsed) ? parsed : [String(parsed)];
    } catch {
      files = [files];
    }
  }
  if (!Array.isArray(files)) files = [];

  const llm = p.llm || undefined;
  const tab = p.tab || undefined; 

  return { url, text, files, llm, tab };
}

// --- 파일 내용 전송 함수 (파일 내용 8123/9090 동시 전송) ---
async function forwardFileContent(contentPayload) {
    const fetchOptions = {
        method: "POST",
        headers: { 
            "Content-Type": "application/json",
            [MARK_HEADER]: "1"
        },
        body: JSON.stringify(contentPayload),
    };

    // 1. FastAPI 서버 (8123)로 전송 (디스크 저장용)
    try {
        const res = await fetch(SERVER_FILE_ENDPOINT, fetchOptions);
        if (!res.ok) throw new Error("HTTP " + res.status);
        console.log("[server:8123] file content forwarded ok (disk save)", { file: contentPayload.name });
    } catch (e) {
        console.error("[server:8123] file content forward failed:", e?.message || e);
    }
    
    // 2. 외부 탐지 모듈 (9090)로 전송 (분석용)
    try {
        const res = await fetch(FILE_DETECT_ENDPOINT, fetchOptions);
        if (!res.ok) throw new Error("HTTP " + res.status);
        console.log("[detector:9090] file content forwarded ok (analysis)", { file: contentPayload.name });
    } catch (e) {
        console.error("[detector:9090] file content forward failed:", e?.message || e);
    }
}


async function forwardToServerFromContent(contentPayload, sender) {
  let networkInfo = {};
  try {
    // ★ MODIFIED: Native Host에 'process_event' 명령과 JSON 페이로드 전체를 전송 ★
    const nativeResp = await callNative("process_event", contentPayload); 
    console.log("[native] process_event response:", nativeResp);

    if (nativeResp?.ok && nativeResp.data?.network) {
      networkInfo = nativeResp.data.network;
    }
  } catch (e) {
    console.warn("[native] process_event failed (Host might be down):", e?.message || e);
  }

  const norm = normalizePayload(contentPayload, sender);

  const finalPayload = {
    url: norm.url,
    text: norm.text,
    files: norm.files,
    network_info: networkInfo,   // Native Host에서 받은 네트워크 정보
    llm: norm.llm,
    tab: norm.tab
  };

  try {
    const res = await fetch(SERVER_EVENT_ENDPOINT, { 
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(finalPayload),
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    console.log("[server] event forwarded ok", { files: finalPayload.files.length });
  } catch (e) {
    console.error("[server] event forward failed:", e?.message || e);
  }
}

const ALLOWED_LLM_HOSTS = [
    "chat.openai.com",
    "chatgpt.com",
    "gemini.google.com"
];

function isAllowedLLMUrl(url) {
    try {
        if (!url) return false;
        const u = new URL(url);
        const host = u.hostname.toLowerCase();
        for (const allowedHost of ALLOWED_LLM_HOSTS) {
            if (host.endsWith(allowedHost)) {
                return true;
            }
        }
    } catch (e) {
        console.error("URL 파싱 오류:", e);
    }
    return false;
}


chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    const t = msg?.type;
    const payload = msg.payload;

    if (t !== "PII_EVENT" && t !== "FILE_COLLECT") return;
    
    const url = sender?.tab?.url || sender?.url || payload?.source_url;

    if (!isAllowedLLMUrl(url)) {
        console.log("[bg] event blocked: not an allowed LLM host:", url);
        return; 
    }

    if (t === "FILE_COLLECT") {
        forwardFileContent(payload);
        sendResponse({ ok: true }); 
        return;
    }
    
    if (t === "PII_EVENT") {
        forwardToServerFromContent(payload || {}, sender);
        return true; 
    }
});

// ===== keepalive (service worker 종료 방지) =====
setInterval(() => {
  chrome.runtime.getPlatformInfo(() => {});
  console.debug("[bg] keepalive ping");
}, 20000);