// content.js
(() => {
  const CONFIG = { debounceMs:300, recentWindow:160, popupAutoHideMs:6000 };
  const onlyDigits = (s) => (s || "").replace(/\D+/g,"");
  const hasCE = (el) => !!el && (el.getAttribute?.("contenteditable")==="true" || el.getAttribute?.("contenteditable")==="plaintext-only");

  // ---- 유효성 검사 ----
  function luhnCheck(numStr){let sum=0,dbl=false;for(let i=numStr.length-1;i>=0;i--){let d=numStr.charCodeAt(i)-48;if(dbl){d*=2;if(d>9)d-=9;}sum+=d;dbl=!dbl;}return sum%10===0;}
  function validBizNo(num10){if(!/^\d{10}$/.test(num10))return false;const w=[1,3,7,1,3,7,1,3,5];let sum=0;for(let i=0;i<9;i++)sum+=(num10[i]-0)*w[i];sum+=Math.floor(((num10[8]-0)*5)/10);return (10-(sum%10))%10===(num10[9]-0);}
  const validMonth=(mm)=>{const m=+mm;return m>=1&&m<=12;};

  // ---- 탐지 패턴 ----
  const PATTERNS=[ 
    {label:"전화번호",rx:/\b(01[0-9][ -]?\d{3,4}[ -]?\d{4})\b/g},
    {label:"전화번호",rx:/\b(0\d{1,2}[ -]?\d{3,4}[ -]?\d{4})\b/g},
    {label:"이메일",rx:/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g},
    {label:"신용카드",rx:/\b(\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4})\b/g,post:(m)=>luhnCheck(onlyDigits(m))},
    {label:"주민·외국인등록번호",rx:/\b(\d{6}-?\d{7})\b/g},
    {label:"운전면허번호",rx:/\b\d{2}-\d{2}-\d{6}-\d{2}\b/g},
    {label:"운전면허번호",rx:/\b\d{2}-\d{6}-\d{2}\b/g},
    {label:"여권번호",rx:/\b[A-Z]\d{8}\b/g},
    {label:"여권번호",rx:/\b[A-Z]{2}\d{7}\b/g},
    //{label:"사업자등록번호",rx:/\b(\d{3}-?\d{2}-?\d{5})\b/g,post:(m)=>validBizNo(onlyDigits(m))},
    //{label:"우편번호",rx:/\b(\d{5})\b/g},
    {label:"IPv4",rx:/\b(?:(?:25[0-5]|2[0-4]\d|1?\d{1,2})\.){3}(?:25[0-5]|2[0-4]\d|1?\d{1,2})\b/g},
    {label:"MAC",rx:/\b([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b/g},
    {label:"계좌번호",rx:/(계좌|입금|이체|account|acct|bank|은행)[^\d]{0,8}(\d[0-9-]{8,16}\d)/gi,post:(m)=>onlyDigits(m).length>=9},
    {label:"카드 CVC/CVV",rx:/(CVC|CVV|시큐리티코드|보안코드)\D{0,5}(\d{3,4})/gi},
    {label:"카드 유효기간",rx:/(EXP|Expiry|유효기간|만료)\D{0,5}((0[1-9]|1[0-2])\/(\d{2}|\d{4}))/gi,post:(m)=>validMonth(m.split("/")[0].slice(-2))}
  ];
  const resetRegex=()=>{for(const p of PATTERNS)try{p.rx.lastIndex=0;}catch{}};

  // ---- 입력 요소 ----
  function getEditableElements(){return[...document.querySelectorAll("textarea,input[type='text'],[contenteditable='true'],[contenteditable='plaintext-only']")];}
  function getActiveOrLastEditable(){const a=document.activeElement;if(a&&(a.matches?.("textarea,input[type='text']")||hasCE(a)))return a;const els=getEditableElements();return els[els.length-1]||null;}
  const getText=(el)=>el?("value"in el?(el.value??""):(el.innerText??"")):"";

  // ---- 탐지 ----
  function detectPII(text,{full=false}={}){const target=full?text:text.slice(-CONFIG.recentWindow);const results=[],seen=new Set();resetRegex();for(const{label,rx,post}of PATTERNS){let m;while((m=rx.exec(target))!==null){const raw=m[2]||m[1]||m[0];if(post&&!post(raw))continue;const key=`${label}|${raw}`;if(seen.has(key))continue;seen.add(key);results.push({label,value:raw});if(!full&&results.length>=12)break;}}return results;}

  // ---- 탐지 배너 ----
  let bannerHideTimer=null;
  function ensureBanner(afterEl){let b=document.getElementById("pii-inline-banner");if(!b){b=document.createElement("div");b.id="pii-inline-banner";Object.assign(b.style,{marginTop:"8px",padding:"10px 12px",border:"2px solid #b91c1c",background:"#fef2f2",color:"#7f1d1d",fontSize:"13px",borderRadius:"8px",lineHeight:"1.4",maxWidth:"720px",whiteSpace:"pre-wrap",zIndex:"2147483647"});}if(afterEl&&afterEl.parentElement){if(b.parentElement!==afterEl.parentElement){afterEl.insertAdjacentElement("afterend",b);}}return b;}
  function renderBanner(el,results,reason="입력 중"){const b=ensureBanner(el);if(!b)return;if(!results||results.length===0){b.style.display="none";b.textContent="";return;}b.style.display="block";b.textContent=`개인정보 탐지 (${reason})\n`+results.map(r=>`- ${r.label} : ${r.value}`).join("\n");if(bannerHideTimer)clearTimeout(bannerHideTimer);bannerHideTimer=setTimeout(()=>{b.style.display="none";},CONFIG.popupAutoHideMs);}

  // ---- 모달 ----
  function ensureModal(){let m=document.getElementById("pii-confirm-modal");if(m)return m;m=document.createElement("div");m.id="pii-confirm-modal";m.innerHTML=`<div id="pii-confirm-backdrop" style="position:fixed;inset:0;background:rgba(0,0,0,0.35);z-index:2147483646;"></div><div id="pii-confirm-card" style="position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);background:#fff;color:#111;border-radius:12px;padding:16px 18px;width:min(92vw,560px);box-shadow:0 20px 60px rgba(0,0,0,0.35);z-index:2147483647;font-size:14px;line-height:1.5;"><div style="font-weight:700;font-size:16px;margin-bottom:8px;">개인정보가 포함된 것으로 보입니다.</div><pre id="pii-confirm-list" style="white-space:pre-wrap;background:#f6f7f9;padding:10px;border-radius:8px;max-height:40vh;overflow:auto;margin:8px 0 12px 0;"></pre><div style="margin-bottom:12px;">이 메시지를 정말 전송하시겠습니까?</div><div style="display:flex;gap:8px;justify-content:flex-end;"><button id="pii-confirm-cancel" style="padding:8px 12px;border-radius:8px;border:1px solid #ddd;background:#fff;cursor:pointer;">취소</button><button id="pii-confirm-send" style="padding:8px 12px;border-radius:8px;border:0;background:#ef4444;color:#fff;cursor:pointer;">전송</button></div></div>`;document.documentElement.appendChild(m);return m;}
  function showConfirmModal(results,onConfirm,onCancel){const m=ensureModal();m.querySelector("#pii-confirm-list").textContent=results.map(r=>`- ${r.label} : ${r.value}`).join("\n");const close=()=>{m.remove();};m.querySelector("#pii-confirm-cancel").onclick=()=>{onCancel?.();close();};m.querySelector("#pii-confirm-send").onclick=()=>{onConfirm?.();close();};}

  // ---- 스캔 ----
  function partialScan(el){const txt=getText(el);renderBanner(el,detectPII(txt,{full:false}),"입력 중");}
  function fullScan(el){const txt=getText(el);const results=detectPII(txt,{full:true});renderBanner(el,results,"전송 직전");return results;}

  // ---- 전송 처리 ----
  const SEND_SELECTORS="button[type='submit'],button[data-testid*='send'],[role='button'][aria-label*='send'],[aria-label*='전송'],[title*='전송'],button svg";
  let bypassOnce=false;

  function proceedSendVia(el,originBtn=null){
    bypassOnce=true;
    if(originBtn){ originBtn.click(); return; }
    const target=el||getActiveOrLastEditable();
    if(target){ const ev=new KeyboardEvent("keydown",{key:"Enter",bubbles:true}); target.dispatchEvent(ev); }
  }

  // ---- Enter 처리 ----
  document.addEventListener("keydown",(e)=>{
    if(bypassOnce){bypassOnce=false;return;}
    if(e.key!=="Enter")return;
    if(e.shiftKey&&!(e.ctrlKey||e.metaKey))return;
    const el=getActiveOrLastEditable(); if(!el) return;
    const results=fullScan(el);
    if(results.length>0){e.preventDefault();e.stopImmediatePropagation();e.stopPropagation();showConfirmModal(results,()=>proceedSendVia(el,null),()=>{});}
  },true);

  // ---- 클릭 처리 ----
  document.addEventListener("click",(e)=>{
    if(bypassOnce){bypassOnce=false;return;}

    // ✅ 모달 내부 버튼 클릭은 차단하지 않음
    if (e.target.closest("#pii-confirm-modal")) {
      return;
    }

    const path=e.composedPath?e.composedPath():(e.path||[]);
    let sendBtn=null;
    for(const node of path){if(!node||node.nodeType!==1)continue;if(node.tagName==="BUTTON"){sendBtn=node;break;}if(node.tagName==="SVG"&&node.closest("button")){sendBtn=node.closest("button");break;}}
    if(!sendBtn)return;
    const inputEl=getActiveOrLastEditable(); if(!inputEl)return;
    const results=fullScan(inputEl);
    if(results.length>0){e.preventDefault();e.stopImmediatePropagation();e.stopPropagation();showConfirmModal(results,()=>proceedSendVia(inputEl,sendBtn),()=>{});}
  },true);

  // ---- 입력 바인딩 ----
  let isComposing=false;
  function bindInputs(){getEditableElements().forEach(el=>{if(el._piiBound)return;el.addEventListener("compositionstart",()=>{isComposing=true;},{passive:true});el.addEventListener("compositionend",()=>{isComposing=false;partialScan(el);},{passive:true});let t=null;el.addEventListener("input",()=>{if(isComposing)return;clearTimeout(t);t=setTimeout(()=>partialScan(el),CONFIG.debounceMs);});el._piiBound=true;});}
  bindInputs();
  new MutationObserver(()=>bindInputs()).observe(document.documentElement||document.body,{childList:true,subtree:true});
  const initEl=getActiveOrLastEditable();if(initEl)partialScan(initEl);
})();
