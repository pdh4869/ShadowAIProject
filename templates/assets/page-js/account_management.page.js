// account_management.html 전용 JavaScript
// 더미 데이터 제거 + 실제 백엔드 렌더링 데이터 활용 + 디자인 그대로 유지

let accounts = [];

// API 호출을 위한 유틸리티 함수
async function callApi(url, method = 'POST', data = null) {
  try {
    const options = {
      method: method,
      headers: {
        'Content-Type': 'application/json',
      },
    };
    if (data) {
      options.body = JSON.stringify(data);
    }
    
    options.credentials = 'include';
    
    const response = await fetch(url, options);
    const result = await response.json();
    
    if (!response.ok) {
      throw new Error(result.message || `API 요청 실패: ${response.status} ${response.statusText}`);
    }
    return result;
  } catch (error) {
    console.error(`API Error on ${url}:`, error);
    alert('오류 발생: ' + error.message);
    throw error; 
  }
}

// ====================================================================
// 페이지 초기화 및 검색 로직
// ====================================================================

document.addEventListener('DOMContentLoaded', function() {
  readAccountsFromTable();
  setupEventListeners();
  // ⭐ 페이지 로드 시, Jinja로 렌더링된 버튼에도 리스너를 붙여줌
  attachActionListeners();
});

// ✅ 테이블에서 현재 렌더링된 실제 데이터를 읽어서 accounts 배열 구성
function readAccountsFromTable() {
  const rows = document.querySelectorAll('#rows tr');
  accounts = [];

  rows.forEach(row => {
    const empId = row.querySelector('td[data-field="employee_id"]').textContent.trim();
    const email = row.querySelector('td[data-field="email"]').textContent.trim();
    const name = row.querySelector('td[data-field="name"]').textContent.trim();
    const role = row.getAttribute('data-privilege') || 'admin'; 
    
    const lastLogin = row.querySelector('td[data-field="last_login"]')?.textContent.trim() || '';
    const createdAt = row.querySelector('td[data-field="created_at"]')?.textContent.trim() || '';

    accounts.push({
      empId,
      email,
      name,
      role,
      lastLogin,
      createdAt
    });
  });
}

// ✅ 검색 결과만 tbody 갱신 (thead는 그대로 유지)
function renderAccounts(filteredAccounts = accounts) {
  const tbody = document.getElementById('rows');
  const empty = document.getElementById('empty');
  
  const currentUserPrivilege = window.currentUserPrivilege || 'general';
  const currentUserId = window.currentUserId;

  if (!tbody) return;

  if (filteredAccounts.length === 0) {
    tbody.innerHTML = '';
    if (empty) empty.hidden = false;
    return;
  }

  if (empty) empty.hidden = true;
  const today = new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' }).replace(/\. /g, '-').replace(/\.$/, '');

  tbody.innerHTML = filteredAccounts.map(account => {
    const isToday = account.lastLogin.startsWith(today);
    const roleLabel = account.role === 'super' ? '최고 관리자' : '일반 관리자';
    const roleClass = account.role === 'super' ? 'role super' : 'role admin';
    
    const isCurrentUser = currentUserId === account.empId;
    let actionButtons = '';
    
    // ⭐ 권한 로직: 검색 후 재렌더링 시 onclick 속성 직접 부여
    if (currentUserPrivilege === 'super') {
        if (isCurrentUser) {
            actionButtons = `
                <button class="btn ghost btn-sm change-pw-btn" data-emp="${account.empId}" onclick="openPasswordModal('${account.empId}')">비밀번호 변경</button>
            `;
        } else if (account.role !== 'super') {
            actionButtons = `
                <button class="btn ghost btn-sm change-pw-btn" data-emp="${account.empId}" onclick="openPasswordModal('${account.empId}')">비밀번호 변경</button>
                <button class="btn danger btn-sm delete-btn" data-emp="${account.empId}" onclick="openDeleteModal('${account.empId}')">삭제</button>
            `;
        } else {
            actionButtons = `<span class="text-muted">권한 없음</span>`;
        }
    } else {
        actionButtons = `<span class="text-muted">권한 없음</span>`;
    }


    return `
      <tr data-employee-id="${account.empId}" data-privilege="${account.role}">
        <td data-field="employee_id">${account.empId}</td>
        <td data-field="email">${account.email}</td>
        <td data-field="name">${account.name}</td>
        <td data-field="privilege">
          <span class="badge ${roleClass}">${roleLabel}</span>
        </td>
        <td data-field="last_login" class="${isToday ? 'today-login' : ''}">${account.lastLogin}</td>
        <td data-field="created_at">${account.createdAt}</td>
        <td class="action-cell">
          <div class="table-actions">
            ${actionButtons}
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

// ✅ 검색 기능 (사번, 이름, 역할)
function handleSearch() {
  const query = document.getElementById('q').value.toLowerCase();
  
  const filtered = accounts.filter(account => {
    const roleText = account.role === 'super' ? '최고 관리자' : '일반 관리자';

    return account.empId.toLowerCase().includes(query) ||
           account.name.toLowerCase().includes(query) ||
           roleText.toLowerCase().includes(query) ||
           account.role.toLowerCase().includes(query)
  });
  
  renderAccounts(filtered);
}


// ====================================================================
// 모달 및 API 연동 로직
// ====================================================================

function validatePassword(password) {
    return password.length >= 8;
}

async function handleCreateSubmit() {
    const emp = document.getElementById('c_emp').value.trim();
    const email = document.getElementById('c_email').value.trim();
    const name = document.getElementById('c_name').value.trim();
    const pwd = document.getElementById('c_pwd').value;
    
    if (!emp || !email || !name || !pwd) {
        alert('모든 필드를 입력해주세요.');
        return;
    }
    
    if (!validatePassword(pwd)) {
        alert('비밀번호는 8자 이상이어야 합니다.');
        return;
    }

    try {
        const data = { emp, email, name, pwd };
        const result = await callApi('/api/admin/create', 'POST', data);
        
        alert(result.message);
        document.getElementById('createModal').classList.remove('open');
        window.location.reload(); 
        
    } catch (e) {}
}

async function handlePwSubmit() {
    const emp = document.getElementById('p_emp').value.trim();
    const pwd = document.getElementById('p_pwd').value;
    
    if (!pwd) {
        alert('새 비밀번호를 입력해주세요.');
        return;
    }

    if (!validatePassword(pwd)) {
        alert('비밀번호는 8자 이상이어야 합니다.');
        return;
    }

    try {
        const data = { emp, pwd };
        const result = await callApi('/api/admin/change_password', 'POST', data);
        
        alert(result.message);
        document.getElementById('pwModal').classList.remove('open');
    } catch (e) {}
}

async function handleDeleteSubmit() {
    const emp = document.getElementById('d_emp').value.trim();
    
    if (!confirm(`${emp} 계정을 정말로 삭제하시겠습니까?`)) {
        return;
    }

    try {
        const data = { emp };
        const result = await callApi('/api/admin/delete', 'POST', data);
        
        alert(result.message);
        document.getElementById('delModal').classList.remove('open');
        window.location.reload(); 
        
    } catch (e) {}
}

/**
 * 페이지 최초 로드 시 Jinja 템플릿에 의해 렌더링된 버튼에 이벤트 리스너를 직접 연결합니다.
 * 검색 후에는 renderAccounts에서 onclick 속성을 통해 연결되므로 이 함수는 최초 1회만 의미가 있습니다.
 */
function attachActionListeners() {
    document.querySelectorAll('.action-cell .change-pw-btn').forEach(button => {
        // 기존의 data-emp 속성을 사용하여 모달 함수 호출
        button.onclick = function() {
            openPasswordModal(this.getAttribute('data-emp'));
        };
    });

    document.querySelectorAll('.action-cell .delete-btn').forEach(button => {
        button.onclick = function() {
            openDeleteModal(this.getAttribute('data-emp'));
        };
    });
}


// ✅ 이벤트 리스너 설정
function setupEventListeners() {
  const searchBtn = document.getElementById('searchBtn');
  const searchInput = document.getElementById('q');
  const createBtn = document.getElementById('createBtn');
  
  const createSubmit = document.getElementById('createSubmit'); 
  const pwSubmit = document.getElementById('pwSubmit');         
  const delSubmit = document.getElementById('delSubmit');       


  if (searchBtn) searchBtn.addEventListener('click', handleSearch);
  if (searchInput) {
    searchInput.addEventListener('keypress', e => {
      if (e.key === 'Enter') handleSearch();
    });
  }

  // 모달 오픈 버튼
  if (createBtn) {
    createBtn.addEventListener('click', () => {
      document.getElementById('createModal').classList.add('open');
    });
  }

  // ⭐ 모달 SUBMIT 버튼 리스너 등록
  if (createSubmit) createSubmit.addEventListener('click', handleCreateSubmit);
  if (pwSubmit) pwSubmit.addEventListener('click', handlePwSubmit);
  if (delSubmit) delSubmit.addEventListener('click', handleDeleteSubmit);


  // 모달 닫기 버튼 리스너
  document.querySelectorAll('[data-close]').forEach(btn => {
    btn.addEventListener('click', e => {
      const modalId = e.target.getAttribute('data-close');
      document.querySelector(modalId).classList.remove('open');
      
      if (modalId === '#createModal') {
          document.getElementById('c_emp').value = '';
          document.getElementById('c_email').value = '';
          document.getElementById('c_name').value = '';
          document.getElementById('c_pwd').value = '';
      }
      if (modalId === '#pwModal') {
          document.getElementById('p_pwd').value = '';
      }
    });
  });
}

// ✅ 비밀번호 변경 모달 열기
function openPasswordModal(empId) {
  document.getElementById('p_emp').value = empId;
  document.getElementById('pwModal').classList.add('open');
}

// ✅ 삭제 모달 열기
function openDeleteModal(empId) {
  document.getElementById('d_emp').value = empId;
  document.getElementById('delModal').classList.add('open');
}