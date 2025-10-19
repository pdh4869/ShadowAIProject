// login.html 전용 JavaScript

const $ = (sel)=>document.querySelector(sel);
const form = $('#loginForm');
const emp  = $('#emp');
const pwd  = $('#pwd');
const err  = $('#error');
const submitBtn = $('#submitBtn');
const togglePwd = $('#togglePwd');

// Demo validation (프론트엔드 검증 샘플)
function validEmp(v){ return /^[A-Za-z0-9_-]{2,20}$/.test(v); }

togglePwd.addEventListener('click', ()=>{
  const visible = pwd.getAttribute('type') === 'text';
  pwd.setAttribute('type', visible ? 'password' : 'text');
  togglePwd.setAttribute('aria-pressed', String(!visible));
  togglePwd.textContent = visible ? '표시' : '숨김';
});

form.addEventListener('submit', (e)=>{
  e.preventDefault();
  err.textContent = '';
  const id = emp.value.trim();

  submitBtn.disabled = true;
  
  // 로그인 사용자 정보 저장
  const userInfo = {
    empId: id === 'S0001' ? 'S0001' : (id || 'A1023'),
    role: id === 'S0001' ? 'super' : 'admin'
  };
  localStorage.setItem('userInfo', JSON.stringify(userInfo));
  
  setTimeout(()=>{
    location.href = 'main.html';
  }, 700);
});

// Enter 키
[pwd, emp].forEach(el => el.addEventListener('keydown', (e)=>{
  if (e.key === 'Enter'){ form.requestSubmit(); }
}));