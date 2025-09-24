// pagehooks.js (페이지 컨텍스트에서 동작)
// 목적: fetch / XHR의 body를 직렬화하여 content.js로 전달 (FormData의 파일은 base64 포함 시도)

(() => {
  // 중복 인젝션 방지
  if (window.__pii_pagehooks_installed) return;
  window.__pii_pagehooks_installed = true;

  const MAX_BASE64_BYTES = 512 * 1024; // base64로 포함할 최대 원시 바이트(512KB). 초과 시 data_b64 제외

  function fileToBase64Async(file){
    return new Promise((res, rej)=>{
      try {
        const fr = new FileReader();
        fr.onload = () => {
          try {
            const full = fr.result || '';
            // fr.result 형식: data:<mime>;base64,AAAA...
            const parts = full.split(',');
            const b64 = parts[1] || '';
            // 대략적인 바이트 크기 체크: base64 길이 * 3/4
            const approxBytes = Math.floor(b64.length * 3 / 4);
            if (approxBytes > MAX_BASE64_BYTES) {
              // 너무 크면 데이터는 제외하고 반환
              return res(null);
            }
            return res(b64);
          } catch(e){
            return res(null);
          }
        };
        fr.onerror = () => res(null);
        fr.readAsDataURL(file);
      } catch(e){ rej(e); }
    });
  }

  function serializeHeaders(hdrs){
    try {
      if (!hdrs) return {};
      // Headers 인스턴스
      if (typeof Headers !== 'undefined' && hdrs instanceof Headers){
        const out = {};
        for (const [k, v] of hdrs.entries()) out[k] = v;
        return out;
      }
      // plain object
      if (typeof hdrs === 'object'){
        try {
          // FormData-like or plain object
          const out = {};
          for (const k of Object.keys(hdrs)) {
            out[k] = hdrs[k];
          }
          return out;
        } catch(e){ return {}; }
      }
      return {};
    } catch(e){ return {}; }
  }

  async function serializeBody(body){
    try {
      if (!body) return { kind: 'empty' };
      if (typeof body === 'string') return { kind: 'text', text: body };
      if (body instanceof URLSearchParams) {
        const obj = {}; for(const [k,v] of body.entries()) obj[k] = v;
        return { kind: 'urlencoded', fields: obj };
      }
      if (body instanceof FormData) {
        const fields = {}; const files = [];
        for (const entry of body.entries()) {
          const k = entry[0], v = entry[1];
          if (v instanceof File) {
            try {
              const b64 = await fileToBase64Async(v);
              const item = { name: v.name, mime: v.type, size: v.size };
              if (b64) item.data_b64 = b64;
              else item.note = 'base64_skipped_or_failed';
              files.push(item);
            } catch(e) {
              files.push({ name: v.name, mime: v.type, size: v.size, note: 'read_failed' });
            }
          } else {
            if (fields[k] === undefined) fields[k] = v;
            else if (Array.isArray(fields[k])) fields[k].push(v);
            else fields[k] = [fields[k], v];
          }
        }
        return { kind: 'formdata', fields, files };
      }
      if (body instanceof Blob) {
        try { const txt = await body.text(); return { kind: 'blob_text', text: txt }; } catch(e){ return { kind: 'blob', size: body.size, type: body.type }; }
      }
      // 객체(일반 JS 객체)
      try {
        const txt = JSON.stringify(body);
        return { kind: 'blob_json', text: txt };
      } catch(e){}
    } catch(e){}
    return { kind: 'unknown' };
  }

  // 안전하게 postMessage 전송 (수신측이 content script)
  function postPayload(payload){
    try {
      window.postMessage({ __pii_from: 'page', type: 'REQUEST_BODY', payload }, '*');
    } catch(e){}
  }

  // fetch 훅
  const _fetch = window.fetch;
  window.fetch = async function(resource, init){
    try {
      const method = (init && init.method) || 'GET';
      const url = (typeof resource === 'string') ? resource : (resource && resource.url) || '';
      const headers = serializeHeaders(init && init.headers);
      const ser = await serializeBody(init && init.body ? init.body : null);
      postPayload({
        body: ser,
        tag: 'fetch',
        method,
        url,
        headers,
        timestamp: new Date().toISOString()
      });
    } catch(e){}
    return _fetch.apply(this, arguments);
  };

  // XHR 훅
  const _XHR = window.XMLHttpRequest;
  function HookedXHR(){
    const xhr = new _XHR();
    const _open = xhr.open;
    const _send = xhr.send;
    let _url = '';
    let _method = '';
    xhr.open = function(method, url){
      _url = url;
      _method = method;
      return _open.apply(this, arguments);
    };
    xhr.send = async function(body){
      try {
        const headers = {}; // 접근 불가: XHR send시 headers는 setRequestHeader로 존재. 여기서는 캡쳐 불가.
        const ser = await serializeBody(body);
        postPayload({
          body: ser,
          tag: 'xhr',
          method: _method || 'GET',
          url: _url || '',
          headers,
          timestamp: new Date().toISOString()
        });
      } catch(e){}
      return _send.apply(this, arguments);
    };
    return xhr;
  }
  window.XMLHttpRequest = HookedXHR;

  // 안전 종료 콘솔 표시 (디버깅용)
  try { console.debug && console.debug('[pii] pagehooks installed'); } catch(e){}
})();
