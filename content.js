// ===== content.js (통합본: PII 메타데이터 + 파일 내용 후킹) =====
(function () {
  console.info("[Collector] injected on:", location.href);

  // 전송 중복 방지 (PII Hook 로직 유지)
  const state = { lastText: "", lastTs: 0 };

  // 파일명 수집 (PII Hook 로직 유지, 메타데이터에 포함될 파일 목록)
  const filesSet = new Set();
  function collectFileNamesFromInputs() {
    const names = [];
    document.querySelectorAll('input[type="file"]').forEach((inp) => {
      try {
        if (inp.files && inp.files.length) {
          for (const f of Array.from(inp.files)) {
            if (f && f.name) names.push(f.name);
          }
        }
      } catch {}
    });
    return names;
  }

  // --- LLM Collector: 파일 처리 유틸리티 ---
  const AGENT_HOST = "127.0.0.1:8000"; 
  const MARK_HEADER = "X-LLM-Collector";

  function arrayBufferToBase64(buffer){let b="";const by=new Uint8Array(buffer),ch=0x8000;for(let i=0;i<by.length;i+=ch){b+=String.fromCharCode.apply(null,by.subarray(i,i+ch));}return btoa(b);}
  const recent=new Map();function dedupe(k,ms=1500){const n=Date.now(),p=recent.get(k)||0;if(n-p<ms)return true;recent.set(k,n);return false;}
  const keyForFile=f=>`file:${f.name}:${f.size}:${f.lastModified||0}`;

  function isAgentRequest(input,init){
    try{
      const url=(typeof input==="string")?input:((input&&input.url)||"");
      if(url && url.includes(AGENT_HOST)) return true;
      const headers=(init&&init.headers)||(input&&input.headers);
      if(headers){
        if(headers.get&&headers.get(MARK_HEADER)) return true;
        if(typeof headers==="object" && MARK_HEADER in headers) return true;
      }
    }catch(_){}
    return false;
  }

  // Base64 파일을 백그라운드로 전송 (새로운 메시지 타입: FILE_COLLECT)
  function postFileViaBackground(payload){
    return new Promise((resolve)=>{
      try{
        chrome.runtime.sendMessage({type:"FILE_COLLECT",payload},(resp)=>{
          if(chrome.runtime.lastError){
            console.warn("[Collector] file send error:", chrome.runtime.lastError.message);
            resolve({ok:false,error:chrome.runtime.lastError.message});
          } else {
            resolve(resp);
          }
        });
      }catch(e){
        console.warn("[Collector] sendMessage exception:", e);
        resolve({ok:false,error:String(e)});
      }
    });
  }

  async function sendFileToDiskAgent(file,origin){
    if(!file) return;
    const k=keyForFile(file); if(dedupe(k)) return;
    
    // 1. 파일 이름 수집 (PII Hook 메타데이터용)
    if (file.name) filesSet.add(file.name); 

    // 2. 실제 파일 내용 Base64 전송 (Collector 로직)
    try{
      const b64=arrayBufferToBase64(await file.arrayBuffer());
      await postFileViaBackground({
        kind:"file",
        name:file.name,
        mime:file.type||"application/octet-stream",
        origin_url:origin,
        data_b64:b64,
        size: file.size,
        agent_id: "browser-agent",
        tab: {
		ua: navigator.userAgent,
		lang: navigator.language,
		platform: navigator.platform
	}
      });
    }catch(e){console.warn("[Collector] send file error:", e);}
  }
  async function sendBlobLikeToDiskAgent(blob,name,origin){
    const fname=name||blob.name||("upload_"+Date.now()+".bin");
    const fake=new File([blob],fname,{type:blob.type||"application/octet-stream",lastModified:Date.now()});
    return sendFileToDiskAgent(fake,origin);
  }
  /* LLM Collector 유틸리티 끝 */

  /* ====== input[type=file] / 드롭 핸들러 (파일 내용 전송) ====== */
  document.addEventListener("change",(e)=>{
    const el=e.target;
    if(el&&el.tagName==="INPUT"&&el.type==="file"&&el.files?.length){
      for(const f of el.files) sendFileToDiskAgent(f,location.href);
    }
  },true);

  // 드롭(폴더 재귀 포함) - Collector 로직 채택
  async function filesFromDataTransfer(items){
    const out=[],entries=[];
    for(const it of items){const en=it.webkitGetAsEntry?it.webkitGetAsEntry():null; if(en) entries.push(en);}
    async function walk(entry,path=""){
      return new Promise((resolve)=>{
        try{
          if(entry.isFile){
            entry.file((file)=>{
              const fname=path?`${path}/${file.name}`:file.name;
              const f2=new File([file],fname,{type:file.type,lastModified:file.lastModified});
              out.push(f2); resolve();
            });
          }else if(entry.isDirectory){
            const reader=entry.createReader();
            reader.readEntries(async (ents)=>{for(const e of ents) await walk(e,path?`${path}/${entry.name}`:entry.name); resolve();});
          }else resolve();
        }catch(_){resolve();}
      });
    }
    for(const e of entries) await walk(e,"");
    return out;
  }
  document.addEventListener("drop", async (e)=>{
    const dt=e.dataTransfer; if(!dt) return;
    if(dt.items && dt.items.length){
      const list=await filesFromDataTransfer(dt.items);
      if(list.length){ for(const f of list) sendFileToDiskAgent(f,location.href); return; }
    }
    if(dt.files?.length){ for(const f of dt.files) sendFileToDiskAgent(f,location.href); }
  },true);


  // --- 포커스된 입력값 추출 (PII Hook 로직 유지) ---
  function getFocusedText() {
      const a = document.activeElement;
      if (a) {
        if (a.tagName === "TEXTAREA") return a.value || "";
        if (a.tagName === "INPUT" && (a.type === "text" || a.type === "search"))
          return a.value || "";
        if (a.isContentEditable) return a.innerText || a.textContent || "";
      }
      const ta = document.querySelector("textarea,[contenteditable='true']");
      if (!ta) return "";
      return ta.tagName === "TEXTAREA"
        ? ta.value || ""
        : ta.innerText || ta.textContent || "";
  }
  function dedup(text) {
      const now = Date.now();
      if (text === state.lastText && now - state.lastTs < 300) return true;
      state.lastText = text;
      state.lastTs = now;
      return false;
  }

  // PII Hook의 send 함수 (PII_EVENT 메시지 전송)
  function sendPIIEvent(payload) {
      console.log("[content] send PII_EVENT", payload);
      if (chrome?.runtime?.sendMessage) {
        chrome.runtime.sendMessage({ type: "PII_EVENT", payload }, (response) => {
          if (chrome.runtime.lastError) {
            console.warn(
              "[content] PII_EVENT sendMessage error:",
              chrome.runtime.lastError.message
            );
          } else {
            console.log("[content] PII_EVENT sendMessage ack:", response);
          }
        });
      } else {
        console.error("[content] chrome.runtime.sendMessage not available");
      }
  }
function buildPIIPayload(text, files) {
  return {
    agent_id: "browser-agent",
    timestamp: new Date().toISOString(),
    source_url: location.href,
    page_title: document.title,
    raw_text: text || "",
    files: files || [],
    tab: { 
      ua: navigator.userAgent,
      lang: navigator.language,
      platform: navigator.platform
    }
  };
}

  // --- 전송 트리거 (Enter/버튼) - PII Hook 로직 유지 ---
  document.addEventListener(
      "keydown",
      async (e) => {
        if (e.key !== "Enter" || e.shiftKey || e.ctrlKey || e.altKey || e.metaKey)
          return;
        const text = (getFocusedText() || "").trim();
        if (!text || dedup(text)) return;

        const names = [
          ...new Set([...Array.from(filesSet), ...collectFileNamesFromInputs()]),
        ];
        sendPIIEvent(buildPIIPayload(text, names));
        filesSet.clear(); // 전송 후 파일명 목록 초기화
      },
      true
  );

  function isSendLike(el) {
      if (!el) return false;
      const t = (el.innerText || el.textContent || "").toLowerCase();
      const aria = (el.getAttribute?.("aria-label") || "").toLowerCase();
      const testid = (el.getAttribute?.("data-testid") || "").toLowerCase();
      return (
        t.includes("send") ||
        t.includes("전송") ||
        t.includes("보내기") ||
        aria.includes("send") ||
        aria.includes("전송") ||
        testid.includes("send")
      );
  }

  document.addEventListener(
      "click",
      async (e) => {
        let el = e.target;
        for (let i = 0; i < 4 && el; i++, el = el.parentElement) {
          if (isSendLike(el)) {
            const text = (getFocusedText() || "").trim();
            if (!text || dedup(text)) return;

            const names = [
              ...new Set([
                ...Array.from(filesSet),
                ...collectFileNamesFromInputs(),
              ]),
            ];
            sendPIIEvent(buildPIIPayload(text, names));
            filesSet.clear(); // 전송 후 파일명 목록 초기화
            break;
          }
        }
      },
      true
  );

  /* ====== fetch/XHR 후킹 (LLM Collector 로직 채택 - 파일 내용만) ====== */
  function scheduleProcessBody(fn){try{setTimeout(fn,0);}catch(_){Promise.resolve().then(fn);} }

  async function processBodyLike(body,origin){
    let extracted=false;
    try{
      if(typeof body==="string"){
        try{
          // JSON 문자열의 경우 텍스트 후킹은 키다운/클릭으로 커버. 파일 내용만 처리
        }catch(_){}
      }else if(body instanceof FormData){
        extracted=(await processFormData(body,origin))||extracted;
      }else if(body instanceof Blob){
        if((body.type||"").toLowerCase().includes("application/json")){
          // JSON Blob은 텍스트로 처리
          try{
            const txt=await body.text();
            // 텍스트 후킹은 키다운/클릭으로 커버
          }catch(_){ await sendBlobLikeToDiskAgent(body,"payload.bin",origin); extracted=true; }
        }else{
          // 일반 Blob은 파일로 처리
          await sendBlobLikeToDiskAgent(body,"payload.bin",origin);
          extracted=true;
        }
      }
    }catch(e){ console.warn("[Collector] processBodyLike error:", e); }
    return extracted;
  }
  async function processFormData(fd,origin){
    let extracted=false;
    for(const [k,v] of fd.entries()){
      try{
        if(typeof v==="string" && /(prompt|content|text|input|query|message)/i.test(k)){
          // 텍스트 후킹은 키다운/클릭에서 커버
        }else if(v instanceof File){
          sendFileToDiskAgent(v,origin);
          extracted=true;
        }else if(v instanceof Blob){
          const guess=v.name||k||"blob.bin";
          sendBlobLikeToDiskAgent(v,guess,origin);
          extracted=true;
        }
      }catch(e){ console.warn("[Collector] formdata entry error:", e); }
    }
    return extracted;
  }

  (function(){
    const _fetch=window.fetch;
    window.fetch=function(input,init={}){
      if(isAgentRequest(input,init)) return _fetch.apply(this,arguments);

      scheduleProcessBody(async ()=>{
        try{
          if(init && init.body){
            await processBodyLike(init.body,location.href);
          }else if(input instanceof Request){
            const clone=input.clone();
            const ct=(clone.headers.get("content-type")||"").toLowerCase();
            if(ct.includes("multipart/form-data")){
              const fd=await clone.formData().catch(()=>null);
              if(fd) await processFormData(fd,location.href);
            }
          }
        }catch(e){ console.warn("[Collector] fetch body error:", e); }
      });

      return _fetch.apply(this,arguments);
    };
  })();

  (function(){
    const _open=XMLHttpRequest.prototype.open;
    const _send=XMLHttpRequest.prototype.send;

    XMLHttpRequest.prototype.open=function(method,url){
      this.__url=url; return _open.apply(this,arguments);
    };
    XMLHttpRequest.prototype.send=function(body){
      if(this.__url && this.__url.includes(AGENT_HOST)) return _send.apply(this,arguments);

      scheduleProcessBody(async ()=>{
        try{
          await processBodyLike(body,location.href);
        }catch(e){ console.warn("[Collector] XHR body error:", e); }
      });

      return _send.apply(this,arguments);
    };
  })();

  console.log("[content] script loaded on", window.location.href);
})();