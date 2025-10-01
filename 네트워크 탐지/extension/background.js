// ===== background.js (통합본: PII 메타데이터 + 파일 내용 중계) =====

// ===== Native host / Server Endpoints =====
const HOST_NAME = "com.example.pii_host";
let nativePort = null;
let reqSeq = 1;
const pending = new Map();

// 메타데이터 전송 엔드포인트 (기존 PII_EVENT)
const SERVER_EVENT_ENDPOINT = "http://127.0.0.1:8123/api/event"; 
// 파일 내용 전송 엔드포인트 (새로 추가)
const SERVER_FILE_ENDPOINT = "http://127.0.0.1:8123/api/file_collect"; 
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
      nativePort.postMessage({ reqId, cmd, payload });
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

// --- 들어온 payload를 정규화: url/text/files 키 통일, 빈 값 방어 ---
function normalizePayload(p = {}, sender) {
  const url =
    p.source_url || p.url || sender?.url || (sender?.tab && sender.tab.url) || "";
  const text = p.text || p.raw_text || "";
  // files: 문자열 1개든, JSON 문자열이든, 배열이든 전부 배열로 통일
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

  // llm (있으면 그대로 전달)
  const llm = p.llm || undefined;
  
  // tab 정보 추가 (User-Agent 포함)
  const tab = p.tab || undefined; 

  return { url, text, files, llm, tab }; // tab 반환
}

// --- 파일 내용 전송 함수 (Native Host 우회) ---
async function forwardFileContent(contentPayload) {
    try {
        const res = await fetch(SERVER_FILE_ENDPOINT, {
            method: "POST",
            headers: { 
                "Content-Type": "application/json",
                [MARK_HEADER]: "1" // 수집 에이전트임을 표시
            },
            body: JSON.stringify(contentPayload),
        });
        if (!res.ok) throw new Error("HTTP " + res.status);
        console.log("[server] file content forwarded ok", { file: contentPayload.name });
    } catch (e) {
        console.error("[server] file content forward failed:", e?.message || e);
    }
}


async function forwardToServerFromContent(contentPayload, sender) {
  let networkInfo = {};
  try {
    const nativeResp = await callNative("get_info", {});
    console.log("[native] get_info response:", nativeResp);
    if (nativeResp?.ok && nativeResp.data?.network) {
      networkInfo = nativeResp.data.network;
    }
  } catch (e) {
    console.warn("[native] get_info failed:", e?.message || e);
  }

  const norm = normalizePayload(contentPayload, sender);

  const finalPayload = {
    // 서버가 기대하는 키 이름들 (app.py에서 모두 처리)
    url: norm.url,
    text: norm.text,
    files: norm.files,           // 파일명 배열 그대로 전달
    network_info: networkInfo,   // 네이티브에서 얻은 네트워크 정보
    // 필요시 추가 전달 필드
    llm: norm.llm,
    tab: norm.tab             // 브라우저 탭 정보 (user-agent 포함)
  };

  try {
    const res = await fetch(SERVER_EVENT_ENDPOINT, { // SERVER_EVENT_ENDPOINT 사용
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

// 허용된 LLM 도메인 목록 및 검사 함수 (ChatGPT 및 Gemini만)
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
            // host가 allowedHost로 끝나면 허용
            if (host.endsWith(allowedHost)) {
                return true;
            }
        }
    } catch (e) {
        console.error("URL 파싱 오류:", e);
    }
    return false;
}


// 메시지 타입 2종을 모두 수신: PII_EVENT (메타데이터) + FILE_COLLECT (파일 내용)
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    const t = msg?.type;
    const payload = msg.payload;

    if (t !== "PII_EVENT" && t !== "FILE_COLLECT") return;
    
    const url = sender?.tab?.url || sender?.url || payload?.source_url;

    // URL 검사 로직 추가 (ChatGPT/Gemini만 통과)
    if (!isAllowedLLMUrl(url)) {
        console.log("[bg] event blocked: not an allowed LLM host:", url);
        return; 
    }

    if (t === "FILE_COLLECT") {
        console.log("[bg] file content received for disk storage:", payload.name);
        forwardFileContent(payload);
        // 비동기 응답이 필요 없으므로 false 반환 (또는 sendResponse 호출)
        sendResponse({ ok: true }); 
        return;
    }
    
    if (t === "PII_EVENT") {
        console.log("[bg] PII event received for metadata:", url);
        forwardToServerFromContent(payload || {}, sender);
        return true; // async 응답 허용 (Native Host 통신 대기)
    }
});

// ===== keepalive (service worker 종료 방지) =====
setInterval(() => {
  chrome.runtime.getPlatformInfo(() => {});
  console.debug("[bg] keepalive ping");
}, 20000);