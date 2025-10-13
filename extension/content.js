// content.js – 최종 버전: 모든 전송 방식 감지
(function () {
  const PORT_NAME = "pii_port";
  let port = null;
  let pending = new Map();

  function nextReqId(){ return `${Date.now()}-${Math.random().toString(36).slice(2,8)}`; }
  function connectPort() {
    try {
      if (!chrome?.runtime?.id) return;
      port = chrome.runtime.connect({ name: PORT_NAME });
      port.onMessage.addListener((msg) => {
        const { reqId } = msg || {};
        if (reqId && pending.has(reqId)) {
          pending.get(reqId).resolve(msg);
          pending.delete(reqId);
        }
      });
      port.onDisconnect.addListener(() => {
        port = null;
      });
    } catch (e) {
      console.log("[content] 확장 프로그램 컨텍스트 무효화됨, 페이지 새로고침 필요");
      port = null;
    }
  }
  if (chrome?.runtime?.id) connectPort();

  async function sendViaPort(type, payload){
    return new Promise(async (resolve)=>{
      if (!port) {
        console.warn("[content] 포트 연결 없음, Service Worker 깨우기 시도...");
        try {
          await chrome.runtime.sendMessage({type: "ping"});
        } catch(e) {
          console.log("[content] Service Worker 깨우기 실패, 재연결 시도");
        }
        await new Promise(r => setTimeout(r, 100));
        connectPort();
        if (!port) {
          console.error("[content] 포트 재연결 실패");
          resolve({ ok:false, error:"포트 연겴 실패" });
          return;
        }
      }
      
      const reqId = nextReqId();
      pending.set(reqId, { resolve });
      
      try {
        port.postMessage({ type, payload, reqId });
      } catch (e) {
        pending.delete(reqId);
        console.error("[content] 메시지 전송 실패:", e.message);
        resolve({ ok:false, error:`전송 실패: ${e.message}` });
        return;
      }
      
      setTimeout(() => {
        if (pending.has(reqId)) {
          pending.delete(reqId);
          console.error("[content] 응답 타임아웃 (10초): 서버 상태 확인 필요");
          resolve({ ok:false, error:"응답 타임아웃" });
        }
      }, 10000);
    });
  }

  const filesMap = new Map();
  const pendingFiles = [];
  let isProcessing = false;
  let isSending = false;
  const MAX_FILES = 10;
  const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB

  function arrayBufferToBase64(buffer){
    let b="";
    const by=new Uint8Array(buffer);
    for(let i=0;i<by.length;i+=0x8000){
      b+=String.fromCharCode.apply(null,by.subarray(i,i+0x8000));
    }
    return btoa(b);
  }

  async function storeFileForLater(file, origin){
    const ext = file.name.split('.').pop().toLowerCase();
    const allowed = ['pdf','docx','hwp','txt','png','jpg','jpeg','bmp','webp','gif','tiff','xlsx','pptx'];
    if (!allowed.includes(ext)) {
      console.log(`[content] 지원하지 않는 파일 형식: ${file.name}`);
      return;
    }
    
    if (file.size > MAX_FILE_SIZE) {
      console.log(`[content] 파일이 너무 큼: ${file.name} (${file.size} bytes)`);
      return;
    }
    
    if (pendingFiles.length >= MAX_FILES) {
      console.log(`[content] 최대 파일 개수 초과 (${MAX_FILES}개)`);
      return;
    }
    
    if (filesMap.has(file.name)) {
      console.log(`[content] 이미 저장된 파일: ${file.name}`);
      return;
    }
    
    console.log(`[content] ✓ 파일 감지: ${file.name} (${file.size} bytes)`);
    
    try {
      const b64 = arrayBufferToBase64(await file.arrayBuffer());
      const fileData = {
        kind:"file", 
        name:file.name, 
        mime:file.type||"application/octet-stream",
        origin_url:origin, 
        data_b64:b64, 
        size:file.size
      };
      
      filesMap.set(file.name, fileData);
      pendingFiles.push(fileData);
      console.log(`[content] ✓ 파일 저장 완료: ${file.name}, 대기중: ${pendingFiles.length}개`);
    } catch (e) {
      console.error(`[content] 파일 읽기 실패: ${file.name}`, e);
    }
  }

  async function sendAllPendingFiles(){
    if(pendingFiles.length === 0) {
      return;
    }
    
    if (isProcessing) {
      console.log("[content] 이미 전송 중...");
      return;
    }
    
    isProcessing = true;
    console.log(`[content] ========== ${pendingFiles.length}개 파일 전송 시작 ==========`);
    
    for(const f of pendingFiles) {
      console.log(`[content] 📤 파일 전송 중: ${f.name}`);
      const result = await sendViaPort("FILE_COLLECT", f);
      
      if (result.ok) {
        console.log(`[content] ✓ 파일 전송 성공: ${f.name}`);
      } else {
        console.error(`[content] ✗ 파일 전송 실패: ${f.name} - ${result.error}`);
      }
    }
    
    pendingFiles.length = 0;
    isProcessing = false;
    console.log("[content] ========== 파일 전송 완료 ==========");
  }

  // 1. input[type=file] 감지 (취소 감지 위해 지연 처리)
  let fileInputTimeout = null;
  document.addEventListener("change",(e)=>{
    if(e.target.tagName==="INPUT"&&e.target.type==="file"){
      const input = e.target;
      
      // 이전 타이머 취소
      if(fileInputTimeout) clearTimeout(fileInputTimeout);
      
      if(input.files?.length){
        console.log(`[content] input[type=file] 감지: ${input.files.length}개, 500ms 대기 중...`);
        
        // 500ms 후에 여전히 파일이 있으면 저장
        fileInputTimeout = setTimeout(() => {
          if(input.files?.length) {
            console.log(`[content] 파일 저장 시작: ${input.files.length}개`);
            pendingFiles.length = 0;
            filesMap.clear();
            for(const f of input.files) {
              storeFileForLater(f, location.href);
            }
          } else {
            console.log(`[content] 파일 취소됨 (저장 안함)`);
          }
          fileInputTimeout = null;
        }, 500);
      } else {
        console.log(`[content] 파일 선택 취소됨, 저장된 파일 초기화`);
        pendingFiles.length = 0;
        filesMap.clear();
      }
    }
  }, true);

  // 2. 드래그 앤 드롭 감지
  let dropHandled = false;
  let justDropped = false;
  document.addEventListener("drop", async (e)=>{
    if (dropHandled) return;
    if (e.dataTransfer?.files?.length) {
      dropHandled = true;
      justDropped = true;
      console.log(`[content] 드롭 이벤트 감지: ${e.dataTransfer.files.length}개 파일`);
      pendingFiles.length = 0;
      filesMap.clear();
      for(const f of e.dataTransfer.files) {
        await storeFileForLater(f, location.href);
      }
      setTimeout(() => { dropHandled = false; }, 1000);
    }
  }, true);

  // 3. 클립보드 붙여넣기 감지
  document.addEventListener("paste", async (e)=>{
    if (e.clipboardData?.files?.length) {
      console.log(`[content] 붙여넣기 감지: ${e.clipboardData.files.length}개 파일`);
      for(const f of e.clipboardData.files) {
        await storeFileForLater(f, location.href);
      }
    }
  }, true);

  function getFocusedText() {
    const a=document.activeElement;
    if (a?.tagName==="TEXTAREA") return a.value||"";
    if (a?.tagName==="INPUT" && (a.type==="text"||a.type==="search")) return a.value||"";
    if (a?.isContentEditable) return a.innerText||a.textContent||"";
    const ta=document.querySelector("textarea,[contenteditable='true']");
    if (!ta) return "";
    return ta.tagName==="TEXTAREA"?ta.value||"":ta.innerText||ta.textContent||"";
  }
  
  function buildPIIPayload(text, files) {
    return {
      source_url: location.href,
      page_title: document.title,
      raw_text: text, 
      files: Array.from(files), 
      tab: { ua: navigator.userAgent }
    };
  }



  // 허용된 URL 확인
  function isAllowedUrl(url) {
    return url.match(/^https:\/\/chatgpt\.com\/?$/i) || url.match(/^https:\/\/chatgpt\.com\/(c|g)\//i) || url.match(/^https:\/\/gemini\.google\.com\//i);
  }
  let isActive = isAllowedUrl(location.href);

  // Enter 키 이벤트
  document.addEventListener("keydown", async (e)=>{
    if (!isActive) return;
    if (e.key==="Enter" && !e.shiftKey && !e.ctrlKey && !e.altKey && !e.metaKey) {
      console.log("[content] ✓ Enter 키 전송");
      const text = getFocusedText().trim();
      if (text || pendingFiles.length > 0) {
        console.log(`[content] 전송: 텍스트 ${text.length}글자, 파일 ${pendingFiles.length}개`);
        const result = await sendViaPort("COMBINED_EVENT", {
          source_url: location.href,
          page_title: document.title,
          raw_text: text,
          files_data: pendingFiles,
          tab: { ua: navigator.userAgent }
        });
        
        if (!result.ok) {
          console.error(`[content] 전송 실패: ${result.error}`);
        }
        
        pendingFiles.length = 0;
        filesMap.clear();
      }
    }
  }, true);

  // 클릭 이벤트 (텍스트 미리 캡처)
  let lastCapturedText = "";
  document.addEventListener("mousedown", (e)=>{
    if (!isActive) return;
    
    // 취소 버튼 체크 (드롭 직후)
    if (justDropped && pendingFiles.length > 0) {
      let el = e.target;
      for (let i=0; i<8 && el; i++, el=el.parentElement) {
        const ariaLabel = (el.getAttribute?.("aria-label")||"");
        const className = el.className?.toString().toLowerCase() || "";
        
        if (ariaLabel.includes("제거") || ariaLabel.includes("파일 제거") ||
            ariaLabel.toLowerCase().includes("close") || ariaLabel.toLowerCase().includes("cancel") || 
            className.includes("close") || className.includes("cancel")) {
          justDropped = false;
          console.log(`[content] 취소 버튼 감지 - 대기 파일 삭제`);
          pendingFiles.length = 0;
          filesMap.clear();
          return;
        }
      }
    }
    
    lastCapturedText = getFocusedText().trim();
    console.log(`[content] mousedown - 텍스트 캡처: ${lastCapturedText.length}글자`);
  }, true);

  document.addEventListener("click", async (e)=>{
    if (!isActive || isSending) return;
    
    // 취소 버튼 먼저 체크
    let el = e.target;
    for (let i=0; i<8 && el; i++, el=el.parentElement) {
      const ariaLabel = (el.getAttribute?.("aria-label")||"");
      const className = el.className?.toString().toLowerCase() || "";
      
      if (ariaLabel.includes("제거") || ariaLabel.includes("파일 제거") ||
          ariaLabel.toLowerCase().includes("close") || ariaLabel.toLowerCase().includes("cancel") || 
          className.includes("close") || className.includes("cancel")) {
        if (justDropped && pendingFiles.length > 0) {
          justDropped = false;
          console.log(`[content] 취소 버튼 감지 - 대기 파일 삭제`);
          pendingFiles.length = 0;
          filesMap.clear();
        }
        return;
      }
    }
    
    // 전송 버튼 체크
    el = e.target;
    for (let i=0;i<8&&el;i++,el=el.parentElement){
      const t=(el.innerText||"").toLowerCase();
      const ariaLabel = (el.getAttribute?.("aria-label")||"").toLowerCase();
      const tagName = el.tagName?.toLowerCase();
      const className = el.className?.toString().toLowerCase() || "";
      
      const isSendButton = 
        tagName === "button" ||
        t.includes("send") || 
        t.includes("전송") || 
        ariaLabel.includes("send") || 
        ariaLabel.includes("submit") ||
        className.includes("send");
      
      if (isSendButton && (pendingFiles.length > 0 || lastCapturedText)) {
        justDropped = false;
        isSending = true;
        console.log(`[content] 전송: 텍스트 ${lastCapturedText.length}글자, 파일 ${pendingFiles.length}개`);
        
        const result = await sendViaPort("COMBINED_EVENT", {
          source_url: location.href,
          page_title: document.title,
          raw_text: lastCapturedText,
          files_data: pendingFiles,
          tab: { ua: navigator.userAgent }
        });
        
        if (!result.ok) {
          console.error(`[content] 전송 실패: ${result.error}`);
        }
        
        pendingFiles.length = 0;
        filesMap.clear();
        lastCapturedText = "";
        justDropped = false;
        
        setTimeout(() => { isSending = false; }, 2000);
        break;
      }
    }
  }, true);

  window.forceSendFiles = async () => {
    console.log("[content] 강제 전송 호출됨");
    await sendAllPendingFiles();
  };

  // URL 변경 감지 (SPA 대응)
  let lastUrl = location.href;
  const urlObserver = new MutationObserver(() => {
    if (location.href !== lastUrl) {
      const wasActive = isActive;
      isActive = isAllowedUrl(location.href);
      console.log(`[content] URL 변경 감지: ${lastUrl} → ${location.href}`);
      console.log(`[content] 탐지 상태: ${wasActive ? '활성' : '비활성'} → ${isActive ? '활성' : '비활성'}`);
      
      // 비활성에서 활성으로 전환 시 포트 재연결
      if (!wasActive && isActive) {
        console.log(`[content] 활성화 됨 - 포트 재연결 시도`);
        if (!port) {
          connectPort();
        }
      }
      
      lastUrl = location.href;
      pendingFiles.length = 0;
      filesMap.clear();
      lastCapturedText = "";
    }
  });
  urlObserver.observe(document, { subtree: true, childList: true });

  console.log("[content] ========== PII Agent 활성화 ==========");
  console.log("[content] URL:", location.href);
  console.log(`[content] 탐지 상태: ${isActive ? '활성' : '비활성'}`);
  console.log("[content] 디버깅: window.forceSendFiles() 호출하여 강제 전송 가능");
})();