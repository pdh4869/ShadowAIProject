// 공통 사용자 관리 스크립트
(function() {
  // 사용자 정보 가져오기
  function getUserInfo() {
    const userInfo = localStorage.getItem('userInfo');
    if (userInfo) {
      return JSON.parse(userInfo);
    }
    // 기본값: 일반 관리자
    return { empId: 'A1023', role: 'admin' };
  }

  // 유저박스 업데이트
  function updateUserBox() {
    const userInfo = getUserInfo();
    const userBox = document.querySelector('.pm-userbox');
    
    if (userBox) {
      const empSpan = userBox.querySelector('.emp');
      if (empSpan) {
        empSpan.innerHTML = `<span class="dot" aria-hidden="true"></span> ${userInfo.empId}`;
      }

      // 계정 관리 버튼 처리
      let accountBtn = userBox.querySelector('.logout[onclick*="account_management"]');
      
      if (userInfo.role === 'super') {
        // 최고 관리자: 계정 관리 버튼 표시
        if (!accountBtn) {
          const logoutBtn = userBox.querySelector('.logout[onclick*="login.html"]');
          accountBtn = document.createElement('button');
          accountBtn.type = 'button';
          accountBtn.className = 'logout';
          accountBtn.onclick = () => location.href = 'account_management.html';
          accountBtn.textContent = '계정 관리';
          accountBtn.style.background = '#F9F7F7';
          userBox.insertBefore(accountBtn, logoutBtn);
        }
      } else {
        // 일반 관리자: 계정 관리 버튼 숨김
        if (accountBtn) {
          accountBtn.remove();
        }
      }
    }
  }

  // 즉시 실행 및 DOM 로드 시 재실행
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', updateUserBox);
  } else {
    updateUserBox();
  }
})();