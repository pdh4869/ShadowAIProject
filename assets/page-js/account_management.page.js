// account_management.html 전용 JavaScript

// 임시 데이터
const today = new Date().toISOString().split('T')[0];
const mockAccounts = [
  { empId: 'S0001', email: 'super@company.com', name: '최고관리자', role: 'super', lastLogin: `${today} 09:30`, createdAt: '2023-01-01' },
  { empId: 'A1023', email: 'admin1@company.com', name: '김관리', role: 'admin', lastLogin: `${today} 16:45`, createdAt: '2023-06-15' },
  { empId: 'A1024', email: 'admin2@company.com', name: '이담당', role: 'admin', lastLogin: '2024-01-13 11:20', createdAt: '2023-08-20' },
  { empId: 'A1025', email: 'admin3@company.com', name: '박매니저', role: 'admin', lastLogin: '2024-01-12 14:10', createdAt: '2023-10-05' }
];

let accounts = [...mockAccounts];

document.addEventListener('DOMContentLoaded', function() {
  const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{"empId":"S0001","role":"super"}');
  const userEmpEl = document.querySelector('.pm-userbox .emp');
  if(userEmpEl) {
    userEmpEl.innerHTML = `<span class="dot" aria-hidden="true"></span> ${userInfo.empId}`;
  }

  checkPermissions(userInfo.role);
  renderAccounts();
  setupEventListeners();
});

function checkPermissions(role) {
  const permBanner = document.getElementById('permBanner');
  const createBtn = document.getElementById('createBtn');
  
  if (role !== 'super') {
    permBanner.hidden = false;
    createBtn.disabled = true;
    createBtn.style.opacity = '0.5';
  }
}

function renderAccounts(filteredAccounts = accounts) {
  const tbody = document.getElementById('rows');
  const empty = document.getElementById('empty');
  
  if (filteredAccounts.length === 0) {
    tbody.innerHTML = '';
    empty.hidden = false;
    return;
  }
  
  const today = new Date().toISOString().split('T')[0];
  
  empty.hidden = true;
  tbody.innerHTML = filteredAccounts.map(account => {
    const isToday = account.lastLogin.startsWith(today);
    return `
    <tr>
      <td>${account.empId}</td>
      <td>${account.email}</td>
      <td>${account.name}</td>
      <td>
        <span class="badge role ${account.role}">
          ${account.role === 'super' ? '최고 관리자' : '일반 관리자'}
        </span>
      </td>
      <td class="${isToday ? 'today-login' : ''}">${account.lastLogin}</td>
      <td>${account.createdAt}</td>
      <td>
        <div class="table-actions">
          ${account.role === 'super' ? `
            <button class="btn" onclick="openPasswordModal('${account.empId}')">비밀번호 변경</button>
          ` : `
            <button class="btn" onclick="openPasswordModal('${account.empId}')">비밀번호 변경</button>
            <button class="btn danger" onclick="openDeleteModal('${account.empId}')">삭제</button>
          `}
        </div>
      </td>
    </tr>
  `}).join('');
}

function setupEventListeners() {
  document.getElementById('searchBtn').addEventListener('click', handleSearch);
  document.getElementById('q').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleSearch();
  });
  
  document.getElementById('createBtn').addEventListener('click', () => {
    document.getElementById('createModal').classList.add('open');
  });
  
  document.querySelectorAll('[data-close]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const modalId = e.target.getAttribute('data-close');
      document.querySelector(modalId).classList.remove('open');
    });
  });
}

function handleSearch() {
  const query = document.getElementById('q').value.toLowerCase();
  const filtered = accounts.filter(account => 
    account.empId.toLowerCase().includes(query) ||
    account.name.toLowerCase().includes(query) ||
    (account.role === 'super' ? '최고 관리자' : '일반 관리자').toLowerCase().includes(query)
  );
  renderAccounts(filtered);
}

function openPasswordModal(empId) {
  document.getElementById('p_emp').value = empId;
  document.getElementById('pwModal').classList.add('open');
}

function openDeleteModal(empId) {
  document.getElementById('d_emp').value = empId;
  document.getElementById('delModal').classList.add('open');
}