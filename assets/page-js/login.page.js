// login.html 전용 JavaScript

const $ = (sel)=>document.querySelector(sel);

document.addEventListener('DOMContentLoaded', function() {
  const form = $('#loginForm');
  const emp = $('#emp');
  const pwd = $('#pwd');
  const err = $('#error');
  const submitBtn = $('#submitBtn');
  const togglePwd = $('#togglePwd');

  // 비밀번호 표시/숨김
  togglePwd.addEventListener('click', ()=>{
    const visible = pwd.getAttribute('type') === 'text';
    pwd.setAttribute('type', visible ? 'password' : 'text');
    togglePwd.setAttribute('aria-pressed', String(!visible));
    togglePwd.textContent = visible ? '표시' : '숨김';
  });

  // 로그인 폼 제출
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
});