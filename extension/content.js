/* content.js — LLM Upload Collector (수집 전용) */

console.info("[LLM-Collector] injected on:", location.href); // 🔎 주입 확인용

const AGENT_HOST  = "127.0.0.1:18080";
const MARK_HEADER = "X-LLM-Collector";

/* ====== LLM 도메인 화이트리스트 (서브도메인 허용) ====== */
const USE_LLM_WHITELIST = true;
const LLM_DOMAINS = [
  "chat.openai.com", "chatgpt.com",
  "oaistatic.com",               // GPT 외부 프레임
  "gemini.google.com", "claude.ai",
  "bard.google.com", "poe.com",
  "perplexity.ai", "huggingface.co"
];
function hostAllowed() {
  if (!USE_LLM_WHITELIST) return true;
  const h = location.host;
  const ok = LLM_DOMAINS.some(d => h === d || h.endsWith("." + d));
  if (!ok) console.debug("[LLM-Collector] host blocked by whitelist:", h);
  return ok;
}

/* ====== 유틸/집계/중계(배경) 등 나머지 로직 ====== */
function arrayBufferToBase64(buffer){let b="";const by=new Uint8Array(buffer),ch=0x8000;for(let i=0;i<by.length;i+=ch){b+=String.fromCharCode.apply(null,by.subarray(i,i+ch));}return btoa(b);}
const recent=new Map();function dedupe(k,ms=1500){const n=Date.now(),p=recent.get(k)||0;if(n-p<ms)return true;recent.set(k,n);return false;}
const keyForFile=f=>`file:${f.name}:${f.size}:${f.lastModified||0}`;

const textBuf=new Map();
function flushText(origin){
  const e=textBuf.get(origin); if(!e) return;
  const payload=e.chunks.join("\n").trim(); e.chunks=[]; e.timer=null; if(!payload) return;
  const h=payload.slice(0,2048); if(e.lastSentHash===h) return; e.lastSentHash=h;
  sendTextToAgent(payload,origin);
}
function queueText(text,origin,waitMs=1200){
  if(!hostAllowed()) return; if(!text||!text.trim()) return;
  let e=textBuf.get(origin); if(!e){e={chunks:[],timer:null,lastSentHash:""}; textBuf.set(origin,e);}
  e.chunks.push(text.trim()); if(!e.timer) e.timer=setTimeout(()=>flushText(origin),waitMs);
}

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

function postViaBackground(payload){
  return new Promise((resolve)=>{
    try{
      chrome.runtime.sendMessage({type:"COLLECT",payload},(resp)=>{
        if(chrome.runtime.lastError){
          console.warn("[LLM-Collector] bg send error:", chrome.runtime.lastError.message);
          resolve({ok:false,error:chrome.runtime.lastError.message});
        } else {
          resolve(resp);
        }
      });
    }catch(e){
      console.warn("[LLM-Collector] sendMessage exception:", e);
      resolve({ok:false,error:String(e)});
    }
  });
}

async function sendFileToAgent(file,origin){
  if(!hostAllowed()||!file) return;
  const k=keyForFile(file); if(dedupe(k)) return;
  try{
    const b64=arrayBufferToBase64(await file.arrayBuffer());
    await postViaBackground({kind:"file",name:file.name,mime:file.type||"application/octet-stream",origin_url:origin,data_b64:b64});
  }catch(e){console.warn("[Collector] send file error:", e);}
}
async function sendBlobLikeToAgent(blob,name,origin){
  const fname=name||blob.name||("upload_"+Date.now()+".bin");
  const fake=new File([blob],fname,{type:blob.type||"application/octet-stream",lastModified:Date.now()});
  return sendFileToAgent(fake,origin);
}
async function sendTextToAgent(text,origin){
  if(!hostAllowed()) return;
  const norm=(text||"").trim(); if(!norm) return;
  const r=await postViaBackground({kind:"text",text:norm,origin_url:origin});
  if(!r?.ok) console.debug("[LLM-Collector] text post failed:", r);
}

/* ====== input[type=file] ====== */
document.addEventListener("change",(e)=>{
  const el=e.target;
  if(el&&el.tagName==="INPUT"&&el.type==="file"&&el.files?.length){
    for(const f of el.files) sendFileToAgent(f,location.href);
  }
},true);

/* ====== 드롭(폴더 재귀) ====== */
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
    if(list.length){ for(const f of list) sendFileToAgent(f,location.href); return; }
  }
  if(dt.files?.length){ for(const f of dt.files) sendFileToAgent(f,location.href); }
},true);

/* ====== 프롬프트 감지: ChatGPT 딥 셀렉터 + 일반 입력 ====== */
function queryDeepAll(selector,root=document){
  const out=[]; const walk=(node)=>{
    if(!node) return;
    if(node.querySelectorAll) out.push(...node.querySelectorAll(selector));
    const tree=node.querySelectorAll?node.querySelectorAll("*"):[];
    for(const el of tree) if(el.shadowRoot) walk(el.shadowRoot);
  }; walk(root); return out;
}
let lastGPTPrompt="";
function readChatGPTPrompt(){
  const els=queryDeepAll('#prompt-textarea, [data-testid="prompt-textarea"], textarea[id="prompt-textarea"]');
  const el=els[0]; if(!el) return "";
  return (el.value ?? el.innerText ?? el.textContent ?? "").trim();
}
function getActiveEditorText(){
  const active=document.activeElement;
  const pickup=(el)=>{
    if(!el) return "";
    if(el.tagName==="TEXTAREA") return el.value||"";
    if(el.tagName==="INPUT" && /^(text|search|email)$/i.test(el.type)) return el.value||"";
    if(el.getAttribute && (el.getAttribute("contenteditable")==="true"||el.getAttribute("role")==="textbox")) return el.innerText||el.textContent||"";
    return "";
  };
  let t=pickup(active); if(t) return t;
  const cand=document.querySelector('[contenteditable="true"], [role="textbox"], textarea, input[type="text"], input[type="search"], input[type="email"]');
  return pickup(cand);
}
document.addEventListener("input",()=>{
  const g=readChatGPTPrompt(); if(g) lastGPTPrompt=g;
},true);

document.addEventListener("keydown",(e)=>{
  if(!hostAllowed()) return;
  if(e.key==="Enter" && !e.shiftKey && !e.repeat){
    const g=readChatGPTPrompt();
    if(g){ lastGPTPrompt=g; queueText(g,location.href); }
    else{
      const t=getActiveEditorText();
      if(t && t.trim().length) queueText(t,location.href);
    }
  }
},true);
document.addEventListener("click",(e)=>{
  if(!hostAllowed()) return;
  const el=e.target?.closest?.('button, [role="button"]'); if(!el) return;
  const label=(el.getAttribute?.("aria-label")||el.innerText||"").toLowerCase();
  if(/(send|전송|submit|send message|submit message)/i.test(label)){
    const g=readChatGPTPrompt();
    if(g){ lastGPTPrompt=g; queueText(g,location.href); }
    else{
      const t=getActiveEditorText();
      if(t && t.trim().length) queueText(t,location.href);
    }
  }
},true);
document.addEventListener("submit",(e)=>{
  if(!hostAllowed()) return;
  const form=e.target;
  const txtEl=form.querySelector("textarea, input[type='text'], input[type='search'], input[type='email']");
  if(txtEl?.value?.trim()) queueText(txtEl.value,location.href);
},true);

/* ====== fetch/XHR 후킹 + GPT 전송 엔드포인트 백업 ====== */
function extractTextsFromJSON(obj,out=[],maxLen=2000){
  try{
    if(obj==null) return out;
    if(typeof obj==="string"){const s=obj.trim(); if(s) out.push(s.slice(0,maxLen)); return out;}
    if(Array.isArray(obj)){for(const v of obj) extractTextsFromJSON(v,out,maxLen); return out;}
    if(typeof obj==="object"){for(const [,v] of Object.entries(obj)) extractTextsFromJSON(v,out,maxLen);}
  }catch(_){}
  return out;
}
function scheduleProcessBody(fn){try{setTimeout(fn,0);}catch(_){Promise.resolve().then(fn);} }

(function(){
  const _fetch=window.fetch;
  window.fetch=function(input,init={}){
    if(!hostAllowed()) return _fetch.apply(this,arguments);
    if(isAgentRequest(input,init)) return _fetch.apply(this,arguments);

    scheduleProcessBody(async ()=>{
      let anyExtracted=false;
      try{
        const urlStr=(typeof input==="string")?input:((input&&input.url)||"");
        const isGPTSend=/https?:\/\/(?:[^/]*\.)?(chatgpt\.com|chat\.openai\.com)\/backend-.*\/(conversation|messages)/i.test(urlStr);

        if(init && init.body){
          anyExtracted=(await processBodyLike(init.body,location.href))||anyExtracted;
        }else if(input instanceof Request){
          const clone=input.clone();
          const ct=(clone.headers.get("content-type")||"").toLowerCase();
          if(ct.includes("application/json")){
            const txt=await clone.text().catch(()=>null);
            if(txt){try{
              const obj=JSON.parse(txt);
              const texts=extractTextsFromJSON(obj).slice(0,5);
              texts.forEach(t=>queueText(t,location.href));
              if(texts.length) anyExtracted=true;
            }catch(_){}} 
          }else if(ct.includes("multipart/form-data")){
            const fd=await clone.formData().catch(()=>null);
            if(fd) anyExtracted=(await processFormData(fd,location.href))||anyExtracted;
          }
        }

        if(isGPTSend && !anyExtracted && lastGPTPrompt){
          queueText(lastGPTPrompt,location.href);
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
    if(!hostAllowed()) return _send.apply(this,arguments);
    if(this.__url && this.__url.includes(AGENT_HOST)) return _send.apply(this,arguments);

    scheduleProcessBody(async ()=>{
      let anyExtracted=false;
      try{
        const isGPTSend=/https?:\/\/(?:[^/]*\.)?(chatgpt\.com|chat\.openai\.com)\/backend-.*\/(conversation|messages)/i.test(this.__url||"");
        anyExtracted=(await processBodyLike(body,location.href))||anyExtracted;
        if(isGPTSend && !anyExtracted && lastGPTPrompt){
          queueText(lastGPTPrompt,location.href);
        }
      }catch(e){ console.warn("[Collector] XHR body error:", e); }
    });

    return _send.apply(this,arguments);
  };
})();

async function processBodyLike(body,origin){
  let extracted=false;
  try{
    if(typeof body==="string"){
      try{
        const obj=JSON.parse(body);
        const texts=extractTextsFromJSON(obj).slice(0,5);
        texts.forEach(t=>queueText(t,origin));
        if(texts.length) extracted=true;
      }catch(_){}
    }else if(body instanceof FormData){
      extracted=(await processFormData(body,origin))||extracted;
    }else if(body instanceof Blob){
      if((body.type||"").toLowerCase().includes("application/json")){
        try{
          const txt=await body.text();
          const obj=JSON.parse(txt);
          const texts=extractTextsFromJSON(obj).slice(0,5);
          texts.forEach(t=>queueText(t,origin));
          if(texts.length) extracted=true;
        }catch(_){ await sendBlobLikeToAgent(body,"payload.bin",origin); }
      }else{
        await sendBlobLikeToAgent(body,"payload.bin",origin);
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
        queueText(v,origin); extracted=true;
      }else if(v instanceof File){
        sendFileToAgent(v,origin);
      }else if(v instanceof Blob){
        const guess=v.name||k||"blob.bin";
        sendBlobLikeToAgent(v,guess,origin);
      }
    }catch(e){ console.warn("[Collector] formdata entry error:", e); }
  }
  return extracted;
}
