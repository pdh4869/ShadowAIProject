// detection_type.html 전용 JavaScript - updated

// 오늘 날짜 자동 설정
function setTodayDate() {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, '0');
  const day = String(today.getDate()).padStart(2, '0');
  const todayStr = `${year}-${month}-${day}`;
  document.getElementById('from').value = todayStr;
  document.getElementById('to').value = todayStr;
}

// 페이지 로드 시 오늘 날짜 설정
document.addEventListener('DOMContentLoaded', function() {
  const filterSource = localStorage.getItem('filterSource');
  const filterStatus = localStorage.getItem('filterStatus');
  const filterDate = localStorage.getItem('filterDate');
  
  if (filterDate) {
    $('#from').value = filterDate;
    $('#to').value = filterDate;
    $('#quickDesc').textContent = `· 선택된 날짜: ${filterDate}`;
    document.querySelectorAll('.pill').forEach(p=>p.classList.remove('active'));
    localStorage.removeItem('filterDate');
  } else {
    setTodayDate();
    // 오늘 범위 표시
    const today = new Date();
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
    document.getElementById('quickDesc').textContent = `· 오늘: ${todayStr} ~ ${todayStr}`;
    // 오늘 버튼 활성화
    document.querySelector('.pill[data-range="today"]').classList.add('active');
  }
  
  if (filterSource) {
    $('#source').value = filterSource;
    localStorage.removeItem('filterSource');
  }
  
  if (filterStatus) {
    $('#status').value = filterStatus;
    localStorage.removeItem('filterStatus');
  }
  
  // 필터 적용
  applyFilters();
});

// 이벤트 리스너 등록
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.pill').forEach(btn=>{
    btn.addEventListener('click', ()=> setQuickRange(btn.dataset.range));
  });
  $('#applyBtn').addEventListener('click', applyFilters);
  $('#resetBtn').addEventListener('click', resetFilters);
  document.addEventListener('keydown', (e)=>{ if(e.key==='Enter' && e.target.id==='q') applyFilters(); });
});

/* 공통 데이터 사용 */
const DATA = window.COMMON_DATA || [
  {emp:'192.168.1.100', status:'실패', date:'2025-10-15 13:43:21', types:[], source:'DOC', filename:'analysis.doc', reason:'빈 파일'},
  {emp:'192.168.1.101', status:'성공', date:'2025-10-15 12:38:09', types:['IP'], source:'텍스트', filename:'-', reason:'', suspicious: true},
  {emp:'192.168.1.102', status:'성공', date:'2025-10-15 20:26:04', types:['생년월일'], source:'텍스트', filename:'-', reason:''},
  {emp:'192.168.1.103', status:'성공', date:'2025-10-14 19:22:52', types:['IP'], source:'텍스트', filename:'-', reason:'', suspicious: true},
  {emp:'192.168.1.104', status:'성공', date:'2025-10-13 03:09:39', types:['이메일','카드번호'], source:'PDF', filename:'cards.pdf', reason:''},
  {emp:'192.168.1.105', status:'실패', date:'2025-10-12 02:57:35', types:[], source:'TXT', filename:'contacts.txt', reason:'암호화 파일'},
  {emp:'192.168.1.106', status:'성공', date:'2025-10-11 02:52:22', types:['카드번호','이메일'], source:'XLSX', filename:'report.xlsx', reason:''},
  {emp:'192.168.1.100', status:'실패', date:'2025-10-10 09:40:18', types:[], source:'HWP', filename:'invoice.hwp', reason:'암호화 파일'},
  {emp:'192.168.1.101', status:'성공', date:'2025-10-09 09:35:05', types:['IP'], source:'텍스트', filename:'-', reason:''},
  {emp:'192.168.1.102', status:'성공', date:'2025-10-08 16:23:01', types:['전화번호'], source:'텍스트', filename:'-', reason:''},
  {emp:'192.168.1.103', status:'성공', date:'2025-10-07 16:18:49', types:['주민등록번호'], source:'텍스트', filename:'-', reason:''},
  {emp:'192.168.1.104', status:'실패', date:'2025-10-06 23:06:44', types:[], source:'텍스트', filename:'-', reason:'지원 불가 형식'},
  {emp:'192.168.1.105', status:'실패', date:'2025-10-05 23:53:32', types:[], source:'PPTX', filename:'presentation.pptx', reason:'지원 불가 형식'},
  {emp:'192.168.1.106', status:'성공', date:'2025-10-04 23:49:19', types:['IP'], source:'TXT', filename:'cards.txt', reason:''},
  {emp:'192.168.1.100', status:'실패', date:'2025-10-03 06:36:15', types:[], source:'HWPX', filename:'cards.hwpx', reason:'빈 파일'},
  {emp:'192.168.1.101', status:'성공', date:'2025-10-02 06:32:02', types:['생년월일'], source:'PDF', filename:'draft.pdf', reason:''},
  {emp:'192.168.1.102', status:'성공', date:'2025-10-01 13:19:58', types:['주민등록번호','카드번호'], source:'XLS', filename:'data.xls', reason:''},
  {emp:'192.168.1.103', status:'성공', date:'2025-09-30 13:15:45', types:['주민등록번호','생년월일'], source:'PDF', filename:'summary.pdf', reason:''},
  {emp:'192.168.1.104', status:'실패', date:'2025-09-29 20:02:41', types:[], source:'DOC', filename:'resume.doc', reason:'손상 파일'},
  {emp:'192.168.1.105', status:'성공', date:'2025-09-28 20:50:28', types:['생년월일'], source:'텍스트', filename:'-', reason:''},
  {emp:'192.168.1.106', status:'성공', date:'2025-09-27 19:46:16', types:['카드번호'], source:'텍스트', filename:'-', reason:''},
  {emp:'192.168.1.100', status:'성공', date:'2025-09-26 03:33:11', types:['이메일','주민등록번호'], source:'XLSX', filename:'log.xlsx', reason:''},
  {emp:'192.168.1.101', status:'실패', date:'2025-09-25 02:29:59', types:[], source:'DOCX', filename:'draft.docx', reason:'빈 파일'},
  {emp:'192.168.1.102', status:'실패', date:'2025-09-24 10:16:54', types:[], source:'XLSX', filename:'summary.xlsx', reason:'지원 불가 형식'},
  {emp:'192.168.1.103', status:'성공', date:'2025-09-23 09:12:42', types:['IP','전화번호'], source:'TXT', filename:'user_notes.txt', reason:''},
  {emp:'192.168.1.104', status:'성공', date:'2025-09-22 17:59:38', types:['카드번호'], source:'TXT', filename:'summary.txt', reason:''},
  {emp:'192.168.1.105', status:'성공', date:'2025-09-21 16:47:25', types:['카드번호'], source:'텍스트', filename:'-', reason:''},
  {emp:'192.168.1.106', status:'성공', date:'2025-09-20 16:42:13', types:['주민등록번호','카드번호'], source:'PDF', filename:'draft.pdf', reason:''},
  {emp:'192.168.1.100', status:'성공', date:'2025-09-19 00:30:08', types:['전화번호','이메일'], source:'PDF', filename:'draft.pdf', reason:''},
  {emp:'192.168.1.101', status:'성공', date:'2025-09-18 23:25:56', types:['카드번호'], source:'TXT', filename:'apply.txt', reason:''},
  {emp:'192.168.1.102', status:'실패', date:'2025-09-17 07:13:51', types:[], source:'TXT', filename:'apply.txt', reason:'지원 불가 형식'},
  {emp:'192.168.1.103', status:'성공', date:'2025-09-16 06:08:39', types:['전화번호'], source:'XLSX', filename:'contacts.xlsx', reason:''},
  {emp:'192.168.1.104', status:'실패', date:'2025-09-15 07:22:52', types:[], source:'DOCX', filename:'data.docx', reason:'지원 불가 형식'},
  {emp:'192.168.1.105', status:'성공', date:'2025-09-14 13:43:22', types:['주민등록번호'], source:'PDF', filename:'cards.pdf', reason:''},
  {emp:'192.168.1.106', status:'성공', date:'2025-09-13 13:39:09', types:['IP'], source:'텍스트', filename:'-', reason:''},
  {emp:'192.168.1.100', status:'성공', date:'2025-09-12 20:27:05', types:['IP'], source:'XLSX', filename:'contacts.xlsx', reason:''},
  {emp:'192.168.1.101', status:'실패', date:'2025-09-11 20:22:52', types:[], source:'XLSX', filename:'draft.xlsx', reason:'지원 불가 형식'},
  {emp:'192.168.1.102', status:'성공', date:'2025-09-10 03:10:48', types:['이메일','카드번호'], source:'XLSX', filename:'log.xlsx', reason:''},
  {emp:'192.168.1.103', status:'실패', date:'2025-09-09 03:05:35', types:[], source:'텍스트', filename:'-', reason:'지원 불가 형식'},
  {emp:'192.168.1.104', status:'성공', date:'2025-09-08 10:53:31', types:['전화번호'], source:'TXT', filename:'summary.txt', reason:''},
  {emp:'192.168.1.105', status:'성공', date:'2025-09-07 10:48:19', types:['전화번호'], source:'DOCX', filename:'invoice.docx', reason:''},
  {emp:'192.168.1.106', status:'성공', date:'2025-09-06 09:36:06', types:['카드번호'], source:'텍스트', filename:'-', reason:''},
  {emp:'192.168.1.100', status:'성공', date:'2025-09-05 17:23:02', types:['전화번호'], source:'XLSX', filename:'analysis.xlsx', reason:''},
  {emp:'192.168.1.101', status:'성공', date:'2025-09-04 16:19:49', types:['생년월일','전화번호'], source:'XLSX', filename:'invoice.xlsx', reason:''},
  {emp:'192.168.1.102', status:'성공', date:'2025-09-22 00:06:45', types:['이메일'], source:'TXT', filename:'q3_report.pdf', reason:''},
  {emp:'192.168.1.103', status:'실패', date:'2025-09-15 00:02:32', types:[], source:'텍스트', filename:'-', reason:'암호화 파일'},
  {emp:'192.168.1.104', status:'실패', date:'2025-09-23 07:49:28', types:[], source:'XLSX', filename:'draft.docx', reason:'지원 불가 형식'},
  {emp:'192.168.1.105', status:'성공', date:'2025-09-19 07:45:15', types:['IP'], source:'텍스트', filename:'-', reason:''},
  {emp:'192.168.1.106', status:'실패', date:'2025-09-23 06:32:03', types:[], source:'TXT', filename:'data.txt', reason:'손상 파일'},
  {emp:'192.168.1.100', status:'성공', date:'2025-09-14 14:20:58', types:['전화번호'], source:'PDF', filename:'q3_report.pdf', reason:''},
  {emp:'192.168.1.101', status:'실패', date:'2025-09-21 13:16:46', types:[], source:'DOCX', filename:'analysis.docx', reason:'빈 파일'},
  {emp:'192.168.1.102', status:'성공', date:'2025-09-24 21:03:41', types:['전화번호','IP'], source:'텍스트', filename:'-', reason:''},
  {emp:'192.168.1.103', status:'성공', date:'2025-09-24 20:59:29', types:['이메일'], source:'XLSX', filename:'user_notes.xlsx', reason:''},
  {emp:'192.168.1.104', status:'실패', date:'2025-09-24 04:46:24', types:[], source:'텍스트', filename:'-', reason:'빈 파일'},
  {emp:'192.168.1.105', status:'성공', date:'2025-09-24 03:42:12', types:['주민등록번호'], source:'TXT', filename:'notes.txt', reason:''},
  {emp:'192.168.1.106', status:'성공', date:'2025-09-10 03:29:59', types:['주민등록번호'], source:'PDF', filename:'draft.docx', reason:''},
  {emp:'192.168.1.100', status:'성공', date:'2025-09-18 10:17:55', types:['카드번호','주민등록번호'], source:'DOCX', filename:'summary.docx', reason:''},
  {emp:'192.168.1.101', status:'성공', date:'2025-09-15 10:12:43', types:['IP'], source:'TXT', filename:'apply.txt', reason:''},
  {emp:'192.168.1.103', status:'성공', date:'2025-09-14 17:00:38', types:['전화번호'], source:'PPTX', filename:'report.pptx', reason:''},
  {emp:'192.168.1.102', status:'실패', date:'2025-09-13 17:55:26', types:[], source:'HWPX', filename:'document.hwpx', reason:'암호화 파일'},
  {emp:'192.168.1.100', status:'성공', date:'2025-09-12 01:43:21', types:['이메일'], source:'HWP', filename:'memo.hwp', reason:''}
];

const $ = (sel) => document.querySelector(sel);

// 스크롤 방지 함수
function preventScroll(e) {
  e.preventDefault();
}

// helpers
function fmt(d){ return d.toISOString().slice(0,10); }
function normalizeSource(source) {
  if(['DOCX','DOC'].includes(source)) return 'DOCX/DOC';
  if(['XLSX','XLS'].includes(source)) return 'XLSX/XLS';
  if(['PPTX','PPT'].includes(source)) return 'PPTX';
  if(['HWPX','HWP'].includes(source)) return 'HWPX/HWP';
  if(['JPG','JPEG'].includes(source)) return 'JPG/JPEG';
  return source;
}

// quick range
function setQuickRange(kind){
  const now = new Date();
  let from, to, label='';
  
  if(kind==='today'){ 
    from = new Date(now);
    to = new Date(now);
    label = '오늘'; 
  }
  else if(kind==='lastweek'){ 
    from = new Date(now);
    from.setDate(now.getDate() - 6); // 7일 전부터
    to = new Date(now);
    label = '지난 주'; 
  }
  else if(kind==='lastmonth'){ 
    from = new Date(now);
    from.setMonth(now.getMonth() - 1, 1);
    to = new Date(now);
    to.setMonth(now.getMonth() - 1 + 1, 0);
    label = '지난 달'; 
  }
  else{ return; }
  
  $('#from').value = fmt(from);
  $('#to').value = fmt(to);
  $('#quickDesc').textContent = `· ${label}: ${fmt(from)} ~ ${fmt(to)}`;
  document.querySelectorAll('.pill').forEach(p=>p.classList.remove('active'));
  const btn = document.querySelector(`.pill[data-range="${kind}"]`);
  if(btn) btn.classList.add('active');
  applyFilters();
}

// filtering
function applyFilters(){
  const from = $('#from').value;
  const to = $('#to').value;
  const type = $('#type').value;
  const source = $('#source').value;
  const status = $('#status').value;
  const q = $('#q').value.trim().toLowerCase();

  let filtered = DATA.filter(row => {
    if (from && row.date.split(' ')[0] < from) return false;
    if (to && row.date.split(' ')[0] > to) return false;
    if (type && !(row.types || []).includes(type)) return false;
    if (source && normalizeSource(row.source) !== source) return false;
    if (status) {
      if (status === '개인 식별 의심') {
        if (!row.suspicious) return false;
      } else if (row.status !== status) {
        return false;
      }
    }
    if (q){
      const hay = [(row.types||[]).join(','),row.source,row.filename,row.reason,row.status,row.date,row.emp].join(' ').toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  renderRows(filtered);
  renderChart(filtered);
}

/* 개인정보 유형 그룹 분류 */
const PII_GROUPS = {
  '연락처 정보': ['전화번호', '이메일'],
  '신원 정보': ['이름', '생년월일'],
  '위치 정보': ['IP', '직책', '조직/기관'],
  '신분증/증명서': ['주민등록번호', '외국인등록번호', '운전면허번호', '여권번호'],
  '금융 정보': ['계좌번호', '카드번호']
};

const GROUP_COLORS = {
  '연락처 정보': 'rgba(59,130,246,0.15)',
  '신원 정보': 'rgba(6,182,212,0.15)',
  '위치 정보': 'rgba(245,158,11,0.15)',
  '신분증/증명서': 'rgba(236,72,153,0.15)',
  '금융 정보': 'rgba(139,92,246,0.15)'
};

const GROUP_TEXT_COLORS = {
  '연락처 정보': '#1e40af',
  '신원 정보': '#0891b2',
  '위치 정보': '#d97706',
  '신분증/증명서': '#be185d',
  '금융 정보': '#7c3aed'
};

function getTypeGroup(type) {
  for (const [group, types] of Object.entries(PII_GROUPS)) {
    if (types.includes(type)) return group;
  }
  return '기타';
}

function getTypeColor(type) {
  const group = getTypeGroup(type);
  return GROUP_COLORS[group] || 'rgba(107,114,128,0.15)';
}

function getTypeTextColor(type) {
  const group = getTypeGroup(type);
  return GROUP_TEXT_COLORS[group] || '#374151';
}

/* 세부 내용 생성 함수 */
function generateDetailData(row) {
  const ips = ['192.168.0.1', '10.0.0.15', '172.16.1.100', '192.168.1.50', '10.1.1.25'];
  const oses = ['Windows 10', 'Windows 11', 'macOS', 'Ubuntu'];
  const computers = ['DESKTOP-TR03E35', 'LAPTOP-ABC123', 'WORKSTATION-XYZ', 'PC-DEF456'];
  const urls = ['https://chatgpt.com/', 'https://claude.ai/', 'https://bard.google.com/', 'https://www.bing.com/chat'];
  const browsers = ['Chrome', 'Firefox', 'Safari', 'Edge'];
  const llms = ['GPT', 'Claude', 'Bard', 'Copilot'];
  
  const hash = row.emp.charCodeAt(0) + row.date.charCodeAt(5);
  return {
    ip: ips[hash % ips.length],
    os: oses[hash % oses.length],
    computer: computers[hash % computers.length],
    url: urls[hash % urls.length],
    browser: browsers[hash % browsers.length],
    llm: llms[hash % llms.length]
  };
}

/* 팝업 열기 */
function openDetailModal(row) {
  const detail = generateDetailData(row);
  
  // 상태 스타일링
  const statusEl = $('#detail-status');
  statusEl.textContent = row.status;
  statusEl.style.color = row.status === '성공' ? '#059669' : '#dc2626';
  
  $('#detail-emp').textContent = row.emp || '-';
  $('#detail-date').textContent = row.date || '-';
  $('#detail-ip').textContent = detail.ip;
  $('#detail-os').textContent = detail.os;
  $('#detail-computer').textContent = detail.computer;
  $('#detail-url').textContent = detail.url;
  $('#detail-browser').textContent = detail.browser;
  $('#detail-llm').textContent = detail.llm;
  $('#detail-source').textContent = row.source;
  
  // 파일명 표시/숨김 (탐지 유형이 '텍스트'인 경우 숨김)
  const filenameSection = $('#filename-section');
  const filenameEl = $('#detail-filename');
  if (row.source === '텍스트') {
    filenameSection.style.display = 'none';
  } else {
    filenameSection.style.display = 'block';
    filenameEl.textContent = row.filename || '-';
  }
  
  // 개인정보 유형 칩 스타일링
  const typesEl = $('#detail-types');
  if (row.types && row.types.length > 0) {
    typesEl.innerHTML = row.types.map(type => {
      const count = row.typeCounts ? row.typeCounts[type] || 1 : Math.floor(Math.random() * 5) + 1;
      return `<span style="display:inline-block;background:${getTypeColor(type)};color:${getTypeTextColor(type)};padding:2px 8px;border-radius:12px;font-size:12px;margin:2px 4px 2px 0;font-weight:700;">${type}: ${count}</span>`;
    }).join('');
  } else {
    typesEl.textContent = '-';
  }
  
  // 검증 결과 섹션 표시/숨김
  const validationSection = $('#validation-section');
  const validationEl = $('#detail-validation');
  const validationTypes = ['주민등록번호', '카드번호'];
  const hasValidationType = row.types && row.types.some(type => validationTypes.includes(type));
  
  if (hasValidationType && row.validation) {
    const validationResults = row.types.filter(type => validationTypes.includes(type))
      .map(type => {
        const validationStatus = row.validation[type];
        if (validationStatus) {
          const isValid = validationStatus === 'valid';
          const bgColor = isValid ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)';
          const textColor = isValid ? '#059669' : '#dc2626';
          const statusText = isValid ? '성공' : '실패';
          return `<span style="display:inline-block;background:${bgColor};color:${textColor};padding:2px 8px;border-radius:12px;font-size:12px;margin:2px 4px 2px 0;font-weight:700;">${type}: ${statusText}</span>`;
        }
        return null;
      }).filter(Boolean).join('');
    
    if (validationResults) {
      validationEl.innerHTML = validationResults;
      validationSection.style.display = 'block';
    } else {
      validationSection.style.display = 'none';
    }
  } else {
    validationSection.style.display = 'none';
  }
  
  // 개인 식별 의심 설정
  const suspiciousEl = $('#detail-suspicious');
  if (row.suspicious) {
    suspiciousEl.innerHTML = '<span style="display:inline-block;background:rgba(239,68,68,0.15);color:#dc2626;padding:2px 8px;border-radius:12px;font-size:12px;margin:2px 4px 2px 0;font-weight:700;">의심</span>';
  } else {
    suspiciousEl.textContent = '-';
  }
  
  // 실패 사유 섹션 표시/숨김
  const reasonSection = $('#reason-section');
  const reasonEl = $('#detail-reason');
  if (row.reason && row.reason.trim()) {
    reasonEl.textContent = row.reason;
    reasonSection.style.display = 'block';
  } else {
    reasonSection.style.display = 'none';
  }
  
  $('#detailModal').style.display = 'block';
  document.body.style.overflow = 'hidden';
  document.addEventListener('wheel', preventScroll, { passive: false });
  document.addEventListener('touchmove', preventScroll, { passive: false });
}

/* 팝업 닫기 */
function closeDetailModal() {
  $('#detailModal').style.display = 'none';
  document.body.style.overflow = '';
  document.removeEventListener('wheel', preventScroll);
  document.removeEventListener('touchmove', preventScroll);
}

/* 테이블 폰트 크기 및 열 너비 동적 조절 */
function adjustTableFontSize() {
  const screenWidth = window.innerWidth;
  const fontSize = screenWidth < 768 ? '10px' : screenWidth < 1024 ? '12px' : '14px';
  const headerFontSize = screenWidth < 768 ? '9px' : screenWidth < 1024 ? '11px' : '12px';
  
  const table = document.querySelector('table');
  if (table) {
    const headers = table.querySelectorAll('thead th');
    const cells = table.querySelectorAll('tbody td');
    
    headers.forEach((th, index) => {
      th.style.fontSize = headerFontSize;
      th.style.whiteSpace = 'nowrap';
      th.style.padding = screenWidth < 768 ? '6px' : '10px';
      
      // 열 너비 조절
      if (screenWidth < 768) {
        if (index === 0) th.style.width = '60px'; // 상태
        else if (index === 1) th.style.width = '80px'; // 일자
        else if (index === 2) th.style.width = '70px'; // IP
        else if (index === 3) th.style.width = '120px'; // 개인정보 유형
        else if (index === 4) th.style.width = '70px'; // 탐지 유형
        else if (index === 5) th.style.width = '80px'; // 파일명
        else if (index === 6) th.style.width = '80px'; // 실패 사유
      }
    });
    
    cells.forEach((td, index) => {
      td.style.fontSize = fontSize;
      td.style.whiteSpace = 'nowrap';
      td.style.overflow = 'hidden';
      td.style.textOverflow = 'ellipsis';
      td.style.padding = screenWidth < 768 ? '6px' : '12px';
      
      // 상태와 개인정보 유형 칩 내부 텍스트 폰트 크기 조절
      if (index % 7 === 0) { // 상태 열
        const statusSpan = td.querySelector('.status');
        const chipFontSize = screenWidth < 768 ? '11px' : screenWidth < 1024 ? '12px' : '12px';
        if (statusSpan) statusSpan.style.fontSize = chipFontSize;
      } else if (index % 7 === 3) { // 개인정보 유형 열
        const chips = td.querySelectorAll('.chip');
        const chipFontSize = screenWidth < 768 ? '11px' : screenWidth < 1024 ? '12px' : '12px';
        chips.forEach(chip => chip.style.fontSize = chipFontSize);
      }
    });
  }
}

// table (요청한 열 순서)
function renderRows(rows){
  const $rows = $('#rows');
  const $empty = $('#empty');
  const $summary = $('#summary');
  $rows.innerHTML='';
  if(rows.length===0){
    $empty.hidden = false;
  } else {
    $empty.hidden = true;
    rows.forEach(r => {
      const tr = document.createElement('tr');
      tr.style.cursor = 'pointer';
      tr.addEventListener('click', () => openDetailModal(r));
      const chips = (r.types||[]).map(t=>`<span class="chip" style="background:${getTypeColor(t)};color:${getTypeTextColor(t)};font-weight:700;">${t}</span>`).join(' ');
      tr.innerHTML = `
        <td style="text-align:center;"><span class="status ${r.status==='성공'?'ok':'fail'}">${r.status}</span></td>
        <td style="text-align:center;">${r.date}</td>
        <td style="text-align:center;">${r.emp || '-'}</td>
        <td style="text-align:center;"><div class="chips">${chips}</div></td>
        <td style="text-align:center;">${r.source}</td>
        <td style="text-align:center;">${r.filename||'-'}</td>
        <td style="text-align:center;">${r.reason||''}</td>`;
      $rows.appendChild(tr);
    });
  }
  $summary.textContent = `총 ${rows.length}건`;
  adjustTableFontSize();
}

function getLabelFontSize() {
  const w = window.innerWidth;
  return w < 768 ? 8 : (w < 1024 ? 10 : 12);
}

// Chart.js 막대 차트
let barChart;
function renderChart(rows){
  const allKeys = ["텍스트","PDF","DOCX/DOC","XLSX/XLS","PPTX","HWPX/HWP","TXT","PNG","JPG/JPEG","BMP","WEBP","GIF","TIFF"];
  const counts = Object.fromEntries(allKeys.map(k=>[k,0]));
  rows.forEach(r=>{ const norm = normalizeSource(r.source); if(counts.hasOwnProperty(norm)) counts[norm]++; });
  
  // 데이터가 있는 항목만 필터링
  const filteredEntries = allKeys.map(k => [k, counts[k]]).filter(([k, count]) => count > 0);
  const keys = filteredEntries.map(([k]) => k);
  const data = filteredEntries.map(([k, count]) => count);
  const total = data.reduce((a, b) => a + b, 0);

  if(barChart) barChart.destroy();
  
  barChart = new Chart(document.getElementById('barChart'), {
    type: 'bar',
    data: {
      labels: keys,
      datasets: [{
        data: data,
        backgroundColor: keys.map((_, i) => ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6','#06b6d4', '#ec4899', '#84cc16', '#f97316', '#a855f7','#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f','#edc948', '#b07aa1', '#ff9da7', '#9c755f', '#bab0ab'][i % 7]),
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,

      layout: {
        padding: {
          top: 50,
          bottom: 0
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (context) => `${context.label}: ${context.parsed.y}건`
          }
        }
      },
      onClick: (event, elements) => {
        if (elements.length > 0) {
          const index = elements[0].index;
          const selectedType = keys[index];
          $('#source').value = selectedType;
          applyFilters();
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { display: false },
          grid: { display: false },
          border: { display: false },
        },
        x: {
          grid: { display: false },
          font: { size: getLabelFontSize() },
          ticks: {
            font: { size: 12, size: getLabelFontSize() },
            color: '#000000'
          }
        }
      }
    }
  });
  
  // Chart.js 플러그인으로 라벨 추가
  Chart.register({
    id: 'customLabels',
    afterDraw: function(chart) {
      if (chart.canvas.id !== 'barChart') return;
      
      const ctx = chart.ctx;
      ctx.save();
      ctx.font = '12px Arial';
      ctx.fillStyle = '#000000';
      ctx.textAlign = 'center';
      
      const chartTotal = chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
      
      chart.data.datasets[0].data.forEach((value, index) => {
        if (value > 0) {
          const meta = chart.getDatasetMeta(0);
          const bar = meta.data[index];
          const percentage = chartTotal > 0 ? ((value/chartTotal)*100).toFixed(1) : '0';
          
          ctx.fillText(`${percentage}%(${value}건)`, bar.x, bar.y - 15);
        }
      });
      ctx.restore();
    }
  });
}

function resetFilters(){
  $('#from').value=''; $('#to').value=''; $('#type').value=''; $('#source').value=''; $('#status').value='';
  $('#q').value=''; $('#quickDesc').textContent='';
  document.querySelectorAll('.pill').forEach(p=>p.classList.remove('active'));
  applyFilters();
}

// 화면 크기 변경 시 차트 다시 그리기 및 테이블 폰트 조절
window.addEventListener('resize', () => {
  if(barChart) barChart.resize();
  adjustTableFontSize();
});

// 네비게이션 활성화 및 클릭 이벤트
document.addEventListener('DOMContentLoaded', function() {
  const navLinks = document.querySelectorAll('.pm-nav a');
  navLinks[0].classList.add('active'); // 탐지 현황 버튼 활성화
  
  // 네비게이션 클릭 이벤트
  navLinks[0].addEventListener('click', (e) => { e.preventDefault(); location.href = 'detection_details.html'; });
  navLinks[1].addEventListener('click', (e) => { e.preventDefault(); location.href = 'personal_information_type.html'; });
  navLinks[2].addEventListener('click', (e) => { e.preventDefault(); location.href = 'user_type.html'; });
});

/* 모달 이벤트 리스너 */
document.addEventListener('DOMContentLoaded', function() {
  $('#closeModal').addEventListener('click', closeDetailModal);
  $('#detailModal').addEventListener('click', function(e) {
    if (e.target === this) closeDetailModal();
  });
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closeDetailModal();
  });
});