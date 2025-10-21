// login.html 전용 JavaScript

const $ = (sel) => document.querySelector(sel);

document.addEventListener('DOMContentLoaded', function() {
  const form = $('#loginForm');
  const emp = $('#emp');
  const pwd = $('#pwd');
  const err = $('#error');
  const submitBtn = $('#submitBtn');
  const togglePwd = $('#togglePwd');

  // 비밀번호 표시/숨김
  togglePwd.addEventListener('click', () => {
    const visible = pwd.getAttribute('type') === 'text';
    pwd.setAttribute('type', visible ? 'password' : 'text');
    togglePwd.setAttribute('aria-pressed', String(!visible));
    togglePwd.textContent = visible ? '표시' : '숨김';
  });

  // 로그인 폼 제출
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    err.textContent = '';

    const employee_id = emp.value.trim();
    const password = pwd.value;

    // 입력값 검증
    if (!employee_id) {
      err.textContent = 'ID를 입력해 주세요.';
      emp.focus();
      return;
    }
    
    if (!password) {
      err.textContent = '비밀번호를 입력해 주세요.';
      pwd.focus();
      return;
    }
    
    // 로딩 상태
    submitBtn.disabled = true;
    submitBtn.textContent = '로그인 중...';

    try {
      const response = await fetch('/api/dashboard_login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          employee_id: employee_id,
          password: password
        })
      });

      const data = await response.json();

      if (response.ok && data.status === 'success') {
        // 로그인 성공
        err.style.color = '#10b981';
        err.textContent = '로그인 성공! 이동 중...';
        
        // 사용자 정보 저장 (선택사항)
        // localStorage에 저장하지만, Flask 세션이 실제 인증을 담당
        try {
          localStorage.setItem('userInfo', JSON.stringify({
            empId: employee_id,
            role: 'admin' // 실제 role은 서버에서 관리
          }));
        } catch (e) {
          console.warn('localStorage 저장 실패:', e);
        }
        
        // 메인 페이지로 리다이렉트
        setTimeout(() => {
          window.location.href = '/main';
        }, 500);
        
      } else {
        // 로그인 실패
        err.style.color = '#ef4444';
        err.textContent = data.message || 'ID 또는 비밀번호가 올바르지 않습니다.';
        pwd.value = '';
        pwd.focus();
      }
      
    } catch (error) {
      console.error('로그인 오류:', error);
      err.style.color = '#ef4444';
      err.textContent = '서버 연결 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.';
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = '로그인';
    }
  });

  // Enter 키 처리
  [pwd, emp].forEach(el => {
    el.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        form.requestSubmit();
      }
    });
  });
  
  // 페이지 로드 시 ID 입력란에 포커스
  emp.focus();
});