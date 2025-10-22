// background.js – Service Worker 안정성 강화
const PORT_NAME = "pii_port";

const SERVER_EVENT_ENDPOINT = "http://127.0.0.1:9500/api/event";
const SERVER_FILE_ENDPOINT  = "http://127.0.0.1:9500/api/file_collect";
const MARK_HEADER = "X-From-Extension";

// 보안: API Secret 관리 (chrome.storage 사용)
let API_SECRET = null;

// Secret 초기화
async function initSecret() {
  return new Promise((resolve) => {
    chrome.storage.local.get(['pii_api_secret'], (result) => {
      if (result.pii_api_secret) {
        API_SECRET = result.pii_api_secret;
        console.log("[bg] ✓ API Secret 로드 완료");
      } else {
        console.warn("[bg] ⚠ API Secret 미설정 - 인증 비활성화 모드");
      }
      resolve();
    });
  });
}

// Secret 설정 함수 (개발자 도구 콘솔에서 호출)
globalThis.setApiSecret = function(secret) {
  chrome.storage.local.set({ pii_api_secret: secret }, () => {
    API_SECRET = secret;
    console.log("[bg] ✓ API Secret 설정 완료");
  });
};

// 보안: HMAC-SHA256 생성
async function generateAuthHeaders() {
  if (!API_SECRET) {
    return {}; // Secret 없으면 빈 헤더 반환
  }
  
  const timestamp = Date.now().toString();
  const encoder = new TextEncoder();
  const keyData = encoder.encode(API_SECRET);
  const msgData = encoder.encode(timestamp);
  
  const key = await crypto.subtle.importKey(
    "raw", keyData, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]
  );
  const signature = await crypto.subtle.sign("HMAC", key, msgData);
  const token = Array.from(new Uint8Array(signature))
    .map(b => b.toString(16).padStart(2, '0')).join('');
  
  return {
    "X-Auth-Token": token,
    "X-Timestamp": timestamp
  };
}

// Service Worker 활성 상태 유지 (alarms 사용)
chrome.alarms.create("keepAlive", { periodInMinutes: 0.5 }); // 30초마다
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "keepAlive") {
    console.log("[bg] KeepAlive: Service Worker 활성 상태");
  }
});

// 확장프로그램 설치/업데이트 시
chrome.runtime.onInstalled.addListener(async () => {
  console.log("[bg] ✓ 확장프로그램 설치/업데이트됨");
  await initSecret();
});

// 시작 시 Secret 초기화
initSecret();

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
          const errMsg = chrome.runtime.lastError.message || "";
          if (errMsg.includes("host not found")) {
            reject(new Error("Native Host 미설치: manifest.json 확인 필요"));
          } else if (errMsg.includes("disconnected")) {
            reject(new Error("Native Host 연결 끊김: 프로세스 종료됨"));
          } else {
            reject(new Error(`Native 에러: ${errMsg}`));
          }
          return;
        }
        
        // 응답 검증
        if (!resp || typeof resp !== 'object') {
          reject(new Error("잘못된 응답 형식: 객체가 아님"));
          return;
        }
        if (!resp.hasOwnProperty('ok')) {
          reject(new Error("잘못된 응답 형식: 'ok' 필드 없음"));
          return;
        }
        
        resolve(resp);
      });
    } catch (e) {
      reject(new Error(`Native 호출 실패: ${e.message}`));
    }
  });
}

async function fetchWithTimeoutAndRetry(url, options, timeoutMs = 30000, fallbackUrl = null) {
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
    let networkInfo = { ip: "unknown" };
    try {
      console.log(`[bg] Native Host 호출: get_info`);
      const nativeResp = await callNative("get_info", {});
      console.log(`[bg] Native 응답:`, nativeResp);
      if (nativeResp?.ok && nativeResp.data?.network) {
        const net = nativeResp.data.network;
        networkInfo.ip = net.interfaces?.[0]?.ips?.[0] || "unknown";
        networkInfo.hostname = net.hostname || "unknown";
        console.log(`[bg] ✓ 네트워크 정보:`, networkInfo);
      }
    } catch (e) {
      console.error(`[bg] Native Host 에러:`, e);
    }

    const combinedPayload = {
      url: senderUrl || payload?.source_url,
      text: payload?.raw_text || "",
      files_data: payload?.files_data || [],
      network_info: networkInfo,
      tab: payload?.tab || {},
      processed_at: new Date().toISOString()
    };

    const authHeaders = await generateAuthHeaders();
    const options = {
      method: "POST",
      headers: { 
        "Content-Type": "application/json", 
        [MARK_HEADER]: "1",
        ...authHeaders
      },
      body: JSON.stringify(combinedPayload)
    };

    console.log(`[bg] 통합 전송: http://127.0.0.1:9500/api/combined`);
    
    fetch("http://127.0.0.1:9500/api/combined", options)
      .then(async res => {
        if (!res.ok) {
          const errText = await res.text().catch(() => "응답 없음");
          if (res.status === 401) throw new Error("인증 실패: API Secret 확인 필요");
          throw new Error(`서버 에러 ${res.status}: ${errText}`);
        }
        return res.json();
      })
      .then(() => console.log(`[bg] ✓ 서버 응답 완료`))
      .catch(e => {
        if (e.message.includes("fetch")) {
          console.error(`[bg] 서버 연결 실패: 서버가 실행 중인지 확인하세요`);
        } else {
          console.error(`[bg] 서버 에러: ${e.message}`);
        }
      });
    
    console.log(`[bg] ✓ 전송 요청 완료 (백그라운드 처리)`);
    return { ok: true };
  }

  const forText = (t === "PII_EVENT");
  let networkInfo = { ip: "unknown" };
  
  console.log(`[bg] 네트워크 정보 수집 중...`);
  try {
    const nativeResp = await callNative("get_info", {});
    if (nativeResp?.ok && nativeResp.data?.network) {
      const net = nativeResp.data.network;
      networkInfo.ip = net.interfaces?.[0]?.ips?.[0] || "unknown";
      networkInfo.hostname = net.hostname || "unknown";
      console.log(`[bg] ✓ 네트워크 정보 수집 완료:`, networkInfo);
    } else {
      console.warn(`[bg] Native Host 응답 없음`);
    }
  } catch (e) {
    console.error(`[bg] Native Host 수집 실패:`, e);
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
    const authHeaders = await generateAuthHeaders();
    const options = {
      method: "POST",
      headers: { 
        "Content-Type": "application/json", 
        [MARK_HEADER]: "1",
        ...authHeaders
      },
      body: JSON.stringify(finalPayload)
    };
    
    console.log(`[bg] 서버로 전송 중: ${SERVER_EVENT_ENDPOINT}`);
    const res = await fetchWithTimeoutAndRetry(
      SERVER_EVENT_ENDPOINT, options, 5000, SERVER_EVENT_ENDPOINT.replace("127.0.0.1","localhost")
    );
    
    if (!res.ok) {
      const errText = await res.text().catch(() => "응답 없음");
      if (res.status === 401) throw new Error("인증 실패: API Secret 확인 필요");
      if (res.status === 403) throw new Error("접근 거부: 권한 없음");
      throw new Error(`서버 에러 ${res.status}: ${errText}`);
    }
    
    const result = await res.json().catch(() => null);
    if (!result || typeof result !== 'object') {
      throw new Error("잘못된 서버 응답 형식");
    }
    
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
    
    const authHeaders = await generateAuthHeaders();
    const options = {
      method: "POST",
      headers: { 
        "Content-Type": "application/json", 
        [MARK_HEADER]: "1",
        ...authHeaders
      },
      body: JSON.stringify(finalFilePayload)
    };
    
    console.log(`[bg] 서버로 전송 중: ${SERVER_FILE_ENDPOINT}`);
    const res = await fetchWithTimeoutAndRetry(
      SERVER_FILE_ENDPOINT, options, 10000, SERVER_FILE_ENDPOINT.replace("127.0.0.1","localhost")
    );
    
    if (!res.ok) {
      const errText = await res.text().catch(() => "응답 없음");
      if (res.status === 401) throw new Error("인증 실패: API Secret 확인 필요");
      if (res.status === 403) throw new Error("접근 거부: 권한 없음");
      if (res.status === 413) throw new Error("파일 크기 초과: 서버 제한 초과");
      throw new Error(`서버 에러 ${res.status}: ${errText}`);
    }
    
    const result = await res.json().catch(() => null);
    if (!result || typeof result !== 'object') {
      throw new Error("잘못된 서버 응답 형식");
    }
    
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
        console.warn("[bg] 응답 전송 실패 (포트 재연결됨, 서버 전송은 성공)");
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
  
  if (t === "ping") {
    console.log("[bg] Ping 수신 - Service Worker 활성화");
    sendResponse({ ok: true });
    return true;
  }
  
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