// 공통 유틸리티 함수들
window.Common = {
  // 날짜 포맷팅
  formatDate: (date, format = 'YYYY-MM-DD') => {
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const hour = String(d.getHours()).padStart(2, '0');
    const minute = String(d.getMinutes()).padStart(2, '0');
    
    return format
      .replace('YYYY', year)
      .replace('MM', month)
      .replace('DD', day)
      .replace('HH', hour)
      .replace('mm', minute);
  },

  // 숫자 포맷팅 (천단위 콤마)
  formatNumber: (num) => {
    return new Intl.NumberFormat('ko-KR').format(num);
  },

  // 테이블 정렬
  sortTable: (table, columnIndex, ascending = true) => {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    rows.sort((a, b) => {
      const aText = a.cells[columnIndex].textContent.trim();
      const bText = b.cells[columnIndex].textContent.trim();
      
      if (!isNaN(aText) && !isNaN(bText)) {
        return ascending ? aText - bText : bText - aText;
      }
      return ascending ? aText.localeCompare(bText) : bText.localeCompare(aText);
    });
    
    rows.forEach(row => tbody.appendChild(row));
  },

  // 필터 기능
  filterTable: (table, searchText, columnIndex = null) => {
    const tbody = table.querySelector('tbody');
    const rows = tbody.querySelectorAll('tr');
    
    rows.forEach(row => {
      const cells = columnIndex !== null ? [row.cells[columnIndex]] : row.cells;
      const match = Array.from(cells).some(cell => 
        cell.textContent.toLowerCase().includes(searchText.toLowerCase())
      );
      row.style.display = match ? '' : 'none';
    });
  },

  // 모달 제어
  modal: {
    open: (modalId) => {
      const modal = document.getElementById(modalId);
      if (modal) modal.classList.add('open');
    },
    close: (modalId) => {
      const modal = document.getElementById(modalId);
      if (modal) modal.classList.remove('open');
    }
  },

  // 알림 표시
  showNotification: (message, type = 'info') => {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    notification.style.cssText = `
      position: fixed; top: 20px; right: 20px; z-index: 9999;
      padding: 12px 16px; border-radius: 8px; color: white;
      background: ${type === 'error' ? '#ef4444' : type === 'success' ? '#10b981' : '#3F72AF'};
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
  },

  // 로딩 스피너
  loading: {
    show: () => {
      if (document.getElementById('loading')) return;
      const loading = document.createElement('div');
      loading.id = 'loading';
      loading.innerHTML = '<div class="spinner"></div>';
      loading.style.cssText = `
        position: fixed; inset: 0; background: rgba(0,0,0,0.5);
        display: flex; align-items: center; justify-content: center; z-index: 9998;
      `;
      document.body.appendChild(loading);
    },
    hide: () => {
      const loading = document.getElementById('loading');
      if (loading) loading.remove();
    }
  }
};

// 공통 네비게이션 및 이벤트 핸들러
window.CommonEvents = {
  // 페이지 네비게이션
  navigateTo: (url) => {
    location.href = url;
  },
  
  // 모달 버튼 호버 효과
  setupModalButtonHover: (buttonId, hoverColor = '#e2e8f0', normalColor = '#f1f5f9') => {
    const button = document.getElementById(buttonId);
    if (button) {
      button.addEventListener('mouseover', () => {
        button.style.background = hoverColor;
      });
      button.addEventListener('mouseout', () => {
        button.style.background = normalColor;
      });
    }
  }
};

// DOM 로드 시 공통 이벤트 바인딩
document.addEventListener('DOMContentLoaded', function() {
  // 페이지 제목 클릭 이벤트
  const pageTitle = document.querySelector('.page-title span');
  if (pageTitle) {
    pageTitle.addEventListener('click', () => CommonEvents.navigateTo('main.html'));
    pageTitle.style.cursor = 'pointer';
  }
  
  // 네비게이션 메뉴 클릭 이벤트
  const navLinks = document.querySelectorAll('.pm-nav a');
  navLinks.forEach((link, index) => {
    const urls = ['detection_details.html', 'detection_type.html', 'personal_information_type.html'];
    if (urls[index]) {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        CommonEvents.navigateTo(urls[index]);
      });
    }
  });
  
  // 로그아웃 버튼 클릭 이벤트
  const logoutBtns = document.querySelectorAll('.logout');
  logoutBtns.forEach(btn => {
    if (btn.textContent.includes('로그아웃')) {
      btn.addEventListener('click', () => CommonEvents.navigateTo('login.html'));
    } else if (btn.textContent.includes('계정 관리')) {
      btn.addEventListener('click', () => CommonEvents.navigateTo('account_management.html'));
    }
  });
  
  // 모달 닫기 버튼 호버 효과
  CommonEvents.setupModalButtonHover('closeModal');
});

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

      // 계정 관리 버튼 처리 (HTML에 이미 존재하는 버튼 제어)
      const accountBtn = userBox.querySelector('#accountBtn');
      
      if (accountBtn) {
        if (userInfo.role === 'super') {
          // 최고 관리자: 계정 관리 버튼 표시
          accountBtn.style.display = '';
        } else {
          // 일반 관리자: 계정 관리 버튼 숨김
          accountBtn.style.display = 'none';
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