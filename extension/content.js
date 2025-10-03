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

  function sendViaPort(type, payload){
    return new Promise((resolve)=>{
      if (port) {
        const reqId = nextReqId();
        pending.set(reqId, { resolve });
        port.postMessage({ type, payload, reqId });
        setTimeout(() => {
          if (pending.has(reqId)) {
            pending.delete(reqId);
            resolve({ ok:false, error:"timeout" });
          }
        }, 10000);
      } else {
        resolve({ ok:false, error:"no_port" });
      }
    });
  }

  const filesMap = new Map();
  const pendingFiles = [];
  let isProcessing = false;
  let isSending = false;

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
    const allowed = ['pdf','docx','txt','png','jpg','jpeg','bmp','webp','gif','tiff'];
    if (!allowed.includes(ext)) {
      console.log(`[content] 지원하지 않는 파일 형식: ${file.name}`);
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
      try {
        const result = await sendViaPort("FILE_COLLECT", f);
        console.log(`[content] ✓ 파일 전송 완료:`, result);
      } catch (e) {
        console.error(`[content] ✗ 파일 전송 실패: ${f.name}`, e);
      }
    }
    
    pendingFiles.length = 0;
    isProcessing = false;
    console.log("[content] ========== 파일 전송 완료 ==========");
  }

  // 1. input[type=file] 감지
  document.addEventListener("change",(e)=>{
    if(e.target.tagName==="INPUT"&&e.target.type==="file"){
      if(e.target.files?.length){
        console.log(`[content] input[type=file] 감지: ${e.target.files.length}개`);
        pendingFiles.length = 0;
        filesMap.clear();
        for(const f of e.target.files) {
          storeFileForLater(f, location.href);
        }
      } else {
        console.log(`[content] 파일 선택 취소됨, 저장된 파일 초기화`);
        pendingFiles.length = 0;
        filesMap.clear();
      }
    }
  }, true);

  // 2. 드래그 앤 드롭 감지
  let dropHandled = false;
  document.addEventListener("drop", async (e)=>{
    if (dropHandled) return;
    if (e.dataTransfer?.files?.length) {
      dropHandled = true;
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



  // Enter 키 이벤트
  document.addEventListener("keydown", async (e)=>{
    if (e.key==="Enter" && !e.shiftKey && !e.ctrlKey && !e.altKey && !e.metaKey) {
      console.log("[content] ✓ Enter 키 전송");
      const text = getFocusedText().trim();
      if (text || pendingFiles.length > 0) {
        console.log(`[content] 전송: 텍스트 ${text.length}글자, 파일 ${pendingFiles.length}개`);
        await sendViaPort("COMBINED_EVENT", {
          source_url: location.href,
          page_title: document.title,
          raw_text: text,
          files_data: pendingFiles,
          tab: { ua: navigator.userAgent }
        });
        pendingFiles.length = 0;
        filesMap.clear();
      }
    }
  }, true);

  // 클릭 이벤트 (텍스트 미리 캡처)
  let lastCapturedText = "";
  document.addEventListener("mousedown", (e)=>{
    lastCapturedText = getFocusedText().trim();
    console.log(`[content] mousedown - 텍스트 캡처: ${lastCapturedText.length}글자`);
  }, true);

  document.addEventListener("click", async (e)=>{
    if (isSending) return;
    
    let el=e.target;
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
        isSending = true;
        console.log(`[content] 전송: 텍스트 ${lastCapturedText.length}글자, 파일 ${pendingFiles.length}개`);
        
        await sendViaPort("COMBINED_EVENT", {
          source_url: location.href,
          page_title: document.title,
          raw_text: lastCapturedText,
          files_data: pendingFiles,
          tab: { ua: navigator.userAgent }
        });
        
        pendingFiles.length = 0;
        filesMap.clear();
        lastCapturedText = "";
        
        setTimeout(() => { isSending = false; }, 2000);
        break;
      }
    }
  }, true);

  window.forceSendFiles = async () => {
    console.log("[content] 강제 전송 호출됨");
    await sendAllPendingFiles();
  };

  console.log("[content] ========== PII Agent 활성화 ==========");
  console.log("[content] URL:", location.href);
  console.log("[content] 디버깅: window.forceSendFiles() 호출하여 강제 전송 가능");
})();