// 10.15 ver/extension/background.js

// background.js – Service Worker 안정성 강화
const PORT_NAME = "pii_port";

const SERVER_TEXT_ENDPOINT = "http://127.0.0.1:9000/api/event";
const SERVER_COMBINED_ENDPOINT = "http://127.0.0.1:9000/api/combined";
const SERVER_FILE_ENDPOINT  = "http://127.0.0.1:9000/api/file_collect";
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
    // console.log("[bg] KeepAlive: Service Worker 활성 상태");
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
        
        if (!resp || typeof resp !== 'object' || !resp.hasOwnProperty('ok')) {
          reject(new Error("잘못된 Native Host 응답 형식"));
          return;
        }
        
        resolve(resp);
      });
    } catch (e) {
      reject(new Error(`Native 호출 실패: ${e.message}`));
    }
  });
}

async function fetchWithTimeout(url, options, timeoutMs = 30000) {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const res = await fetch(url, { ...options, signal: controller.signal });
        return res;
    } finally {
        clearTimeout(id);
    }
}

async function handlePayload(type, payload, senderUrl) {
  console.log(`[bg] ========== 페이로드 처리 시작 (타입: ${type}) ==========`);
  
  if (!isAllowedLLMUrl(senderUrl, payload)) {
    console.warn(`[bg] 허용되지 않은 URL: ${senderUrl}`);
    return { ok: false, reason: "not_allowed_url", checked_url: senderUrl };
  }

  // 1. 네트워크 정보 공통 수집
  let networkInfo = { ip: "unknown", hostname: "unknown" };
  try {
    const nativeResp = await callNative("get_info", {});
    console.log(`[bg] Native Host 응답:`, nativeResp);
    
    if (nativeResp?.ok && nativeResp.data?.network) {
      const net = nativeResp.data.network;
      
      // IP 추출
      if (net.interfaces && Array.isArray(net.interfaces) && net.interfaces.length > 0) {
        const firstInterface = net.interfaces[0];
        if (firstInterface.ips && Array.isArray(firstInterface.ips) && firstInterface.ips.length > 0) {
          networkInfo.ip = firstInterface.ips[0];
        }
      }
      
      // 호스트명 추출
      if (net.hostname && net.hostname !== "Unknown") {
        networkInfo.hostname = net.hostname;
      }
      
      console.log(`[bg] ✓ 네트워크 정보:`, networkInfo);
    } else {
      console.warn(`[bg] Native Host 응답 형식 오류:`, nativeResp);
    }
  } catch (e) {
    console.error(`[bg] Native Host 에러:`, e);
  }

  // 2. 메시지 타입에 따른 분기 처리
  let targetUrl;
  let finalPayload;
  let timeout = 10000;

  if (type === "TEXT_EVENT") {
    console.log(`[bg] 텍스트 이벤트 처리 중...`);
    targetUrl = SERVER_TEXT_ENDPOINT;
    finalPayload = {
        url: senderUrl || payload?.source_url,
        text: payload?.raw_text || "",
        network_info: networkInfo,
        tab: payload?.tab || {},
        processed_at: new Date().toISOString()
    };

  } else if (type === "COMBINED_EVENT") {
    console.log(`[bg] 통합 이벤트 처리 중...`);
    targetUrl = SERVER_COMBINED_ENDPOINT;
    finalPayload = {
        url: senderUrl || payload?.source_url,
        text: payload?.raw_text || "",
        files_data: payload?.files_data || [],
        network_info: networkInfo,
        tab: payload?.tab || {},
        processed_at: new Date().toISOString()
    };
    timeout = 30000; // 파일 포함될 수 있으니 타임아웃 증가

  } else if (type === "FILE_COLLECT") {
    // 기존 FILE_COLLECT 로직 유지
    console.log(`[bg] 단일 파일 이벤트 처리 중: ${payload.name}`);
    targetUrl = SERVER_FILE_ENDPOINT;
    finalPayload = {
        ...payload,
        origin_url: payload.origin_url || senderUrl,
        network_info: networkInfo,
        processed_at: new Date().toISOString()
    };
    timeout = 30000;
  
  } else {
    console.error(`[bg] 알 수 없는 이벤트 타입: ${type}`);
    return { ok: false, error: "unknown_event_type" };
  }

  // 3. 서버로 데이터 전송
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

  try {
    console.log(`[bg] 서버로 전송: ${targetUrl}`);
    const res = await fetchWithTimeout(targetUrl, options, timeout);
    
    if (!res.ok) {
        const errText = await res.text().catch(() => "응답 없음");
        if (res.status === 401) throw new Error("인증 실패: API Secret 확인 필요");
        throw new Error(`서버 에러 ${res.status}: ${errText}`);
    }
    
    const result = await res.json().catch(() => null);
    console.log(`[bg] ✓ 서버 전송 성공`);
    
    // 💡 [수정] 서버 응답 처리 로직
    if (result && result.result && Array.isArray(result.result)) {
        const detectedItems = result.result;
        if (detectedItems.length > 0) {
            const detectionData = {
                url: senderUrl,
                timestamp: finalPayload.processed_at,
                // 파일 이벤트의 경우 파일명 추가
                fileName: type.includes('FILE') || type.includes('COMBINED') ? (payload.name || (payload.files_data && payload.files_data[0] ? payload.files_data[0].name : '')) : undefined,
                detected: detectedItems.map(item => ({
                    type: item.type,
                    value: item.value,
                    // status가 있는 경우에만 추가
                    ...(item.status && { status: item.status })
                }))
            };

            chrome.storage.local.get(["detectionLogs"], (storageResult) => {
                const logs = storageResult.detectionLogs || [];
                logs.push(detectionData);
                chrome.storage.local.set({ detectionLogs: logs }, () => {
                    console.log("[bg] 탐지 로그가 저장되었습니다.", detectionData);
                });
            });
        }
    }

    return { ok: true, result: result };

  } catch (e) {
    if (e.name === 'AbortError') {
        console.error(`[bg] 서버 요청 시간 초과 (${timeout}ms)`);
        throw new Error("서버 요청 시간 초과");
    } else if (e.message.includes("fetch")) {
        console.error(`[bg] 서버 연결 실패: 서버가 실행 중인지 확인하세요.`);
        throw new Error("서버 연결 실패");
    } else {
        console.error(`[bg] 서버 전송 에러: ${e.message}`);
        throw e;
    }
  }
}

/* === Port 기반 처리 (에러 핸들링 강화) === */
chrome.runtime.onConnect.addListener((port) => {
  if (port.name !== PORT_NAME) return;
  
  console.log("[bg] ✓ 포트 연결됨:", port.sender?.tab?.url);
  
  port.onMessage.addListener(async (msg) => {
    const { type, payload, reqId } = msg || {};
    if (!reqId) return; // reqId 없는 메시지는 무시
    
    console.log(`[bg] 메시지 수신: ${type} (reqId: ${reqId})`);
    
    try {
      const senderUrl = port.sender?.tab?.url || port.sender?.url || payload?.source_url;
      const out = await handlePayload(type, payload, senderUrl);
      
      try {
        port.postMessage({ reqId, ...out });
      } catch (e) {
        console.warn("[bg] 응답 전송 실패 (포트가 이미 닫혔을 수 있음)");
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

/* === 기존 sendMessage 경로도 유지(하위 호환성) === */
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  const t = msg?.type;
  
  if (t === "ping") {
    // console.log("[bg] Ping 수신 - Service Worker 활성화");
    sendResponse({ ok: true });
    return true;
  }
  
  if (!t || (t !== "PII_EVENT" && t !== "FILE_COLLECT" && t !== "COMBINED_EVENT" && t !== "TEXT_EVENT")) return;
  
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
  return true; // 비동기 응답을 위해 true 반환
});

console.log("[bg] ========== Background Script 활성화 ==========");