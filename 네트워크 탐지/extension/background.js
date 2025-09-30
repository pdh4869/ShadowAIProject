// ===== Native host =====
const HOST_NAME = "com.example.pii_host";
let nativePort = null;
let reqSeq = 1;
const pending = new Map();

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

const SERVER_ENDPOINT = "http://127.0.0.1:8123/api/event";

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

  return { url, text, files, llm };
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
    files: norm.files,           // ★ 파일명 배열 그대로 전달
    network_info: networkInfo,   // 네이티브에서 얻은 네트워크 정보
    // 필요시 추가 전달 필드
    llm: norm.llm
  };

  try {
    const res = await fetch(SERVER_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(finalPayload),
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    console.log("[server] forwarded ok", { files: finalPayload.files.length });
  } catch (e) {
    console.error("[server] forward failed:", e?.message || e);
  }
}

// 메시지 타입 2종을 모두 수신: 기존 "PII_EVENT" + 내가 준 "pii:collect"
chrome.runtime.onMessage.addListener((msg, sender) => {
  const t = msg?.type;
  if (t !== "PII_EVENT" && t !== "pii:collect") return;
  console.log("[bg] event from content:", sender?.tab?.url || sender?.url);
  forwardToServerFromContent(msg.payload || {}, sender);
});

// ===== keepalive (service worker 종료 방지) =====
setInterval(() => {
  chrome.runtime.getPlatformInfo(() => {});
  console.debug("[bg] keepalive ping");
}, 20000);
