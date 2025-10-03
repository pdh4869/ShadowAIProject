// background.js – Service Worker 안정성 강화
const PORT_NAME = "pii_port";

const SERVER_EVENT_ENDPOINT = "http://127.0.0.1:9000/api/event";
const SERVER_FILE_ENDPOINT  = "http://127.0.0.1:9000/api/file_collect";
const MARK_HEADER = "X-From-Extension";

// Service Worker 활성 상태 유지 (alarms 사용)
chrome.alarms.create("keepAlive", { periodInMinutes: 0.5 }); // 30초마다
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "keepAlive") {
    console.log("[bg] KeepAlive: Service Worker 활성 상태");
  }
});

// 확장프로그램 설치/업데이트 시
chrome.runtime.onInstalled.addListener(() => {
  console.log("[bg] ✓ 확장프로그램 설치/업데이트됨");
});

function isAllowedLLMUrl(url, payload) {
  if (!url && payload && payload.source_url) url = payload.source_url;
  if (!url) return false;
  const u = url.toLowerCase();
  if (
    u.includes("chat.openai.com") ||
    u.includes("chatgpt.com") ||
    u.includes("claude.ai") ||
    u.includes("bard.google.com") ||
    u.includes("gemini.google.com") ||
    u.includes("localhost") || u.includes("127.0.0.1") ||
    u.startsWith("file://")
  ) return true;
  return false;
}

function callNative(cmd, args = {}) {
  return new Promise((resolve, reject) => {
    try {
      const payload = { cmd, args, reqId: Date.now() };
      chrome.runtime.sendNativeMessage("com.example.pii_host", payload, (resp) => {
        if (chrome.runtime.lastError) {
          console.error("[bg] Native 메시지 에러:", chrome.runtime.lastError);
          reject(chrome.runtime.lastError);
          return;
        }
        resolve(resp);
      });
    } catch (e) {
      console.error("[bg] Native 호출 실패:", e);
      reject(e);
    }
  });
}

async function fetchWithTimeoutAndRetry(url, options, timeoutMs = 5000, fallbackUrl = null) {
  const doFetch = (u) => {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeoutMs);
    return fetch(u, { ...options, signal: controller.signal }).finally(() => clearTimeout(id));
  };
  try {
    const res = await doFetch(url);
    return res;
  } catch (e) {
    console.warn(`[bg] Fetch 실패, fallback 시도: ${e.message}`);
    if (fallbackUrl) return doFetch(fallbackUrl);
    throw e;
  }
}

async function handlePayload(t, payload, senderUrl) {
  console.log(`[bg] ========== 페이로드 처리 시작 ==========`);
  console.log(`[bg] 타입: ${t}`);
  console.log(`[bg] URL: ${senderUrl}`);
  
  if (!isAllowedLLMUrl(senderUrl, payload)) {
    console.warn(`[bg] 허용되지 않은 URL: ${senderUrl}`);
    return { ok: false, reason: "not_allowed_url", checked_url: senderUrl };
  }

  if (t === "COMBINED_EVENT") {
    let networkInfo = {};
    console.log(`[bg] 네트워크 정보 수집 시도...`);
    try {
      const nativeResp = await callNative("get_info", {});
      if (nativeResp?.ok && nativeResp.data?.network) {
        networkInfo = nativeResp.data.network;
        console.log(`[bg] ✓ 네트워크 정보 수집 완료:`, networkInfo);
      } else {
        console.warn(`[bg] Native Host 응답 없음`);
      }
    } catch (e) {
      console.warn(`[bg] Native Host 실패:`, e.message);
    }

    const combinedPayload = {
      url: senderUrl || payload?.source_url,
      text: payload?.raw_text || "",
      files_data: payload?.files_data || [],
      network_info: networkInfo,
      tab: payload?.tab || {},
      processed_at: new Date().toISOString()
    };

    const options = {
      method: "POST",
      headers: { "Content-Type": "application/json", [MARK_HEADER]: "1" },
      body: JSON.stringify(combinedPayload)
    };

    console.log(`[bg] 통합 전송: ${SERVER_EVENT_ENDPOINT.replace('/event', '/combined')}`);
    const res = await fetchWithTimeoutAndRetry(
      "http://127.0.0.1:9000/api/combined", options, 10000, "http://localhost:9000/api/combined"
    );
    const result = await res.json().catch(() => null);
    console.log(`[bg] ✓ 통합 전송 완료`);
    return { ok: true, result };
  }

  const forText = (t === "PII_EVENT");
  let networkInfo = {};
  
  console.log(`[bg] 네트워크 정보 수집 중...`);
  try {
    const nativeResp = await callNative("get_info", {});
    if (nativeResp?.ok && nativeResp.data?.network) {
      networkInfo = nativeResp.data.network;
      console.log(`[bg] ✓ 네트워크 정보 수집 완료:`, networkInfo);
    }
  } catch (e) {
    console.error(`[bg] 네트워크 정보 수집 실패:`, e);
  }

  if (forText) {
    console.log(`[bg] 텍스트 이벤트 처리 중...`);
    const finalPayload = {
      url: senderUrl || payload?.source_url,
      text: payload?.raw_text || "",
      files: payload?.files || [],
      network_info: networkInfo,
      tab: payload?.tab || {},
      processed_at: new Date().toISOString()
    };
    const options = {
      method: "POST",
      headers: { "Content-Type": "application/json", [MARK_HEADER]: "1" },
      body: JSON.stringify(finalPayload)
    };
    
    console.log(`[bg] 서버로 전송 중: ${SERVER_EVENT_ENDPOINT}`);
    const res = await fetchWithTimeoutAndRetry(
      SERVER_EVENT_ENDPOINT, options, 5000, SERVER_EVENT_ENDPOINT.replace("127.0.0.1","localhost")
    );
    const result = await res.json().catch(() => null);
    console.log(`[bg] ✓ 텍스트 이벤트 전송 완료`);
    return { ok: true, result };
    
  } else {
    console.log(`[bg] 파일 이벤트 처리 중: ${payload.name}`);
    const finalFilePayload = {
      kind: payload.kind || "file",
      name: payload.name,
      mime: payload.mime,
      origin_url: payload.origin_url || senderUrl,
      data_b64: payload.data_b64,
      size: payload.size || 0,
      network_info: networkInfo,
      processed_at: new Date().toISOString()
    };
    
    console.log(`[bg] 파일 크기: ${(payload.size/1024).toFixed(2)}KB`);
    
    const options = {
      method: "POST",
      headers: { "Content-Type": "application/json", [MARK_HEADER]: "1" },
      body: JSON.stringify(finalFilePayload)
    };
    
    console.log(`[bg] 서버로 전송 중: ${SERVER_FILE_ENDPOINT}`);
    const res = await fetchWithTimeoutAndRetry(
      SERVER_FILE_ENDPOINT, options, 10000, SERVER_FILE_ENDPOINT.replace("127.0.0.1","localhost")
    );
    const result = await res.json().catch(() => null);
    console.log(`[bg] ✓ 파일 이벤트 전송 완료`);
    return { ok: true, result };
  }
}

/* === Port 기반 처리 (에러 핸들링 강화) === */
chrome.runtime.onConnect.addListener((port) => {
  if (port.name !== PORT_NAME) return;
  
  console.log("[bg] ✓ 포트 연결됨:", port.sender?.tab?.url);
  
  port.onMessage.addListener(async (msg) => {
    const { type, payload, reqId } = msg || {};
    console.log(`[bg] 메시지 수신: ${type} (reqId: ${reqId})`);
    
    try {
      const senderUrl = port.sender?.tab?.url || port.sender?.url || payload?.source_url;
      const out = await handlePayload(type, payload, senderUrl);
      
      // 포트가 여전히 연결되어 있는지 확인
      try {
        port.postMessage({ reqId, ...out });
      } catch (e) {
        console.error("[bg] 응답 전송 실패 (포트 끊김?):", e);
      }
    } catch (e) {
      console.error(`[bg] 처리 중 에러:`, e);
      try {
        port.postMessage({ reqId, ok:false, error: e?.message || String(e) });
      } catch (sendErr) {
        console.error("[bg] 에러 응답 전송 실패:", sendErr);
      }
    }
  });
  
  port.onDisconnect.addListener(() => {
    console.log("[bg] 포트 연결 해제됨");
  });
});

/* === 기존 sendMessage 경로도 유지(콜백) === */
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  const t = msg?.type;
  if (!t || (t !== "PII_EVENT" && t !== "FILE_COLLECT")) return;
  
  console.log(`[bg] (레거시) 메시지 수신: ${t}`);
  
  (async () => {
    try {
      const senderUrl = sender?.tab?.url || sender?.url || msg?.payload?.source_url;
      const out = await handlePayload(t, msg.payload || {}, senderUrl);
      sendResponse(out);
    } catch (e) {
      console.error(`[bg] (레거시) 처리 중 에러:`, e);
      sendResponse({ ok:false, error: e?.message || String(e) });
    }
  })();
  return true;
});

console.log("[bg] ========== Background Script 활성화 ==========");