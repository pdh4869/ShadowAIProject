// content.js — 최종 버전: 모든 전송 방식 감지
(function () {
  const PORT_NAME = "pii_port";
  let port = null;
  let pending = new Map();

  function nextReqId(){ return `${Date.now()}-${Math.random().toString(36).slice(2,8)}`; }
  function connectPort() {
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
      setTimeout(connectPort, 1000);
    });
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
  let isProcessing = false; // 중복 방지 플래그

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
    
    // 중복 체크
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
    filesMap.clear();
    isProcessing = false;
    console.log("[content] ========== 파일 전송 완료 ==========");
  }

  // 1. input[type=file] 감지
  document.addEventListener("change",(e)=>{
    if(e.target.tagName==="INPUT"&&e.target.type==="file"&&e.target.files?.length){
      console.log(`[content] input[type=file] 감지: ${e.target.files.length}개`);
      for(const f of e.target.files) {
        storeFileForLater(f, location.href);
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

  // 메시지 전송 핸들러 (공통)
  async function handleMessageSend(source) {
    console.log(`[content] ========== 메시지 전송 감지 (${source}) ==========`);
    
    // 파일 먼저 전송
    if (pendingFiles.length > 0) {
      console.log(`[content] 대기 중인 파일 ${pendingFiles.length}개 전송 시작`);
      await sendAllPendingFiles();
    } else {
      console.log(`[content] 전송할 파일 없음`);
    }
    
    // 텍스트 전송
    const text=(getFocusedText()||"").trim();
    if (text) {
      console.log(`[content] 텍스트 전송: ${text.substring(0, 50)}... (${text.length}글자)`);
      sendViaPort("PII_EVENT", buildPIIPayload(text, Array.from(filesMap.keys())));
    }
    filesMap.clear();
  }

  // Enter 키 이벤트
  document.addEventListener("keydown", async (e)=>{
    console.log(`[content] 키 입력: ${e.key}, Shift: ${e.shiftKey}`);
    
    if (e.key==="Enter" && !e.shiftKey && !e.ctrlKey && !e.altKey && !e.metaKey) {
      console.log("[content] ✓ Enter 키 감지 (전송)");
      await handleMessageSend("Enter키");
    }
  }, true);

  // 클릭 이벤트 - 모든 버튼 클릭 로깅
  document.addEventListener("click", async (e)=>{
    console.log("[content] 클릭 이벤트:", e.target);
    
    let el=e.target;
    for (let i=0;i<8&&el;i++,el=el.parentElement){
      const t=(el.innerText||"").toLowerCase();
      const ariaLabel = (el.getAttribute?.("aria-label")||"").toLowerCase();
      const role = (el.getAttribute?.("role")||"").toLowerCase();
      const tagName = el.tagName?.toLowerCase();
      const className = el.className?.toString().toLowerCase() || "";
      
      console.log(`[content] 체크 중 (depth ${i}): tag=${tagName}, role=${role}, text="${t.substring(0,20)}", aria="${ariaLabel}"`);
      
      // 전송 버튼 감지 (매우 넓은 패턴)
      const isSendButton = 
        tagName === "button" ||
        role === "button" ||
        t.includes("send") || 
        t.includes("전송") || 
        t.includes("보내기") ||
        ariaLabel.includes("send") || 
        ariaLabel.includes("submit") ||
        className.includes("send") ||
        el.id?.includes("send");
      
      if (isSendButton) {
        console.log(`[content] ✓✓✓ 전송 버튼 후보 발견! depth=${i}`);
        
        // 파일이 있을 때만 전송 (중복 방지)
        if (pendingFiles.length > 0) {
          console.log("[content] 파일 있음 → 전송 실행");
          await handleMessageSend("클릭");
          break;
        } else {
          console.log("[content] 파일 없음 → 전송 스킵");
        }
      }
    }
  }, true);

  // 강제 전송 함수 (디버깅용 - 콘솔에서 수동 호출 가능)
  window.forceSendFiles = async () => {
    console.log("[content] 강제 전송 호출됨");
    await sendAllPendingFiles();
  };

  console.log("[content] ========== PII Agent 활성화 ==========");
  console.log("[content] URL:", location.href);
  console.log("[content] 디버깅: window.forceSendFiles() 호출하여 강제 전송 가능");
})();