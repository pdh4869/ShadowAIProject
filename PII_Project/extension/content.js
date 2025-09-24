// content.js
// 목적: 입력 전송 시 개인정보 탐지 후 서버 기록, 파일 업로드 발생 시 단순 이벤트만 서버 전송
'use strict';

const SERVER_URL = 'http://127.0.0.1:18080/collect';

// ===== 유틸 =====
function debounce(fn, ms = 500) {
  let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}
function nowISO(){ return new Date().toISOString(); }
function $(sel, root=document){ return root.querySelector(sel); }
function isVisible(el){
  if(!el) return false;
  try {
    const s = getComputedStyle(el);
    return s.display !== 'none' && s.visibility !== 'hidden' && el.offsetParent !== null;
  } catch (_) { return false; }
}

// ===== 입력 요소 수집 =====
function getEditableElements(){
  const els = new Set();
  try{
    document.querySelectorAll('textarea,input[type="text"],[contenteditable="true"]').forEach(el=>{
      if(isVisible(el)) els.add(el);
    });
    const gptMain = document.querySelector('main form textarea');
    if (gptMain && isVisible(gptMain)) els.add(gptMain);
  }catch(_){}
  return Array.from(els);
}

// ===== 경량 탐지 규칙 =====
const PII_RULES = [
  { 항목:'전화번호', rx:/\b(01[016789])[- ]?\d{3,4}[- ]?\d{4}\b/g },
  { 항목:'이메일',   rx:/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g },
  { 항목:'주민등록번호', rx:/\b\d{6}[-]?[1-4]\d{6}\b/g },
  { 항목:'카드번호', rx:/\b(?:\d{4}[- ]?){3}\d{4}\b|\b\d{16}\b/g },
  { 항목:'카드 CVC/CVV', rx:/\b(?:CVC|CVV)\s*[:=]?\s*\d{3,4}\b/gi },
  { 항목:'카드 유효기간', rx:/\b(0[1-9]|1[0-2])\s*[\/\-]\s*(\d{2}|\d{4})\b/g },
  { 항목:'계좌번호', rx:/\b(?!01)\d{10,14}\b/g },
  { 항목:'여권번호', rx:/\b[A-PR-WY][0-9]{7,8}\b/gi },
  { 항목:'운전면허번호', rx:/\b\d{2}[- ]?\d{2}[- ]?\d{6}[- ]?\d{2}\b/g },
  { 항목:'IP주소', rx:/\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b/g }
];

function detectPII(text){
  try{
    if(!text) return [];
    const out = [];
    for(const rule of PII_RULES){
      let m, rx = new RegExp(rule.rx.source, rule.rx.flags);
      while((m = rx.exec(text)) !== null){
        out.push({ 유형: rule.항목, 값: m[0] });
        if(out.length > 200) break;
      }
    }
    return out;
  }catch(_){ return []; }
}

// ===== 현재 입력값 읽기 =====
let activeInput = null;
function readFromElement(el){
  if(!el) return '';
  try{
    if(el.tagName === 'TEXTAREA' || (el.tagName === 'INPUT' && el.type === 'text')) return el.value || '';
    if(el.getAttribute && el.getAttribute('contenteditable') === 'true') return (el.innerText || el.textContent || '');
  }catch(_){}
  return '';
}
function getCurrentText(){
  try{
    const ae = document.activeElement;
    if(ae && (ae.tagName === 'TEXTAREA' || (ae.tagName === 'INPUT' && ae.type === 'text') || ae.getAttribute?.('contenteditable') === 'true')){
      const t = readFromElement(ae);
      if(t) return t;
    }
  }catch(_){}
  const t2 = readFromElement(activeInput);
  if(t2) return t2;
  const cands = ['main form textarea','form textarea','textarea','[contenteditable="true"]'];
  for(const sel of cands){
    const el = $(sel);
    const t = readFromElement(el);
    if(t) return t;
  }
  return '';
}

// ===== 서버 전송 =====
async function sendToServer(kind, text, dets, extra={}){
  try{
    await fetch(SERVER_URL, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        시각: nowISO(),
        페이지: location.href,
        종류: kind,
        항목들: dets,
        ...extra
      })
    });
  }catch(_){}
}

// ===== 전송 플로우 =====
let isSending = false;
let lastSentAt = 0;
async function handleSend(){
  try{
    const text = getCurrentText();
    if(!text || !text.trim()) return;
    const now = Date.now();
    if(isSending || (now - lastSentAt) < 500) return;
    isSending = true;

    const dets = detectPII(text);
    if(!dets || dets.length === 0){
      isSending = false;
      return; // 개인정보 없으면 기록 안 남김
    }

    await sendToServer('입력전송', text, dets);
    lastSentAt = Date.now();
  }catch(_){
  }finally{
    isSending = false;
  }
}

// ===== 이벤트 훅 =====
function hookEvents(){
  document.addEventListener('submit', async ()=>{ await handleSend(); }, true);
  document.addEventListener('keydown', async (e)=>{
    if(e.key === 'Enter' && !e.shiftKey){ await handleSend(); }
  }, true);
  document.addEventListener('click', async (e)=>{
    const t = e.target;
    if(!t) return;
    const btn = t.closest && t.closest('button,[role="button"],input[type="submit"]');
    if(btn) await handleSend();
  }, true);
}

// ===== 파일 업로드 감지 (파일명/크기 제외, 단순 이벤트) =====
function hookFileUploads(){
  document.addEventListener('change', async (e)=>{
    const t = e.target;
    if(t && t.type === 'file' && t.files && t.files.length > 0){
      fetch('http://127.0.0.1:18080/upload_meta', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({
          시각: nowISO(),
          페이지: location.href,
          종류: '파일'
        })
      }).catch(()=>{});
    }
  }, true);
}

// ===== 입력 감시 =====
const refresh = debounce(()=>{}, 200);
function attachInputs(){
  try{
    const inputs = getEditableElements();
    inputs.forEach(el=>{
      el.addEventListener('input', ()=>{
        if(activeInput!==el) activeInput = el;
        refresh();
      });
      el.addEventListener('focus', ()=>{
        activeInput = el;
        refresh();
      });
    });
  }catch(_){}
}

// ===== 초기화 =====
function init(){
  attachInputs();
  hookEvents();
  hookFileUploads(); // 파일 업로드 감지 추가
}
setTimeout(init, 600);
const obs = new MutationObserver(debounce(()=>{ attachInputs(); }, 800));
obs.observe(document.documentElement, {childList:true, subtree:true});
