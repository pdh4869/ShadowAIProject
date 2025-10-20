/* ====== 샘플 데이터 ====== */
const DATA = [
  {emp:'192.168.1.100', status:'실패', date:'2025-10-15 14:09:47', types:[], source:'DOC', filename:'analysis.doc', reason:'빈 파일'},
  {emp:'192.168.1.101', status:'성공', date:'2025-10-15 14:56:35', types:['IP'], source:'텍스트', filename:'-', reason:'', suspicious: true},
  {emp:'192.168.1.102', status:'성공', date:'2025-10-15 13:52:22', types:['생년월일'], source:'텍스트', filename:'-', reason:''},
  {emp:'192.168.1.103', status:'성공', date:'2025-10-14 21:39:18', types:['IP'], source:'텍스트', filename:'-', reason:'', suspicious: true},
  {emp:'192.168.1.104', status:'성공', date:'2025-10-13 20:35:05', types:['이메일','카드번호'], source:'PDF', filename:'cards.pdf', reason:''},
  {emp:'192.168.1.105', status:'실패', date:'2025-10-12 04:22:01', types:[], source:'TXT', filename:'contacts.txt', reason:'암호화 파일'},
  {emp:'192.168.1.106', status:'성공', date:'2025-10-11 04:18:48', types:['카드번호','이메일'], source:'XLSX', filename:'report.xlsx', reason:'', suspicious: true},
  {emp:'192.168.1.100', status:'실패', date:'2025-10-10 11:05:44', types:[], source:'HWP', filename:'invoice.hwp', reason:'암호화 파일'},
  {emp:'192.168.1.101', status:'성공', date:'2025-10-09 11:53:31', types:['IP'], source:'텍스트', filename:'-', reason:''},
  {emp:'192.168.1.102', status:'성공', date:'2025-10-08 10:48:19', types:['전화번호'], source:'텍스트', filename:'-', reason:'', suspicious: true},
  {emp:'192.168.1.103', status:'성공', date:'2025-10-07 18:36:14', types:['주민등록번호'], source:'텍스트', filename:'-', reason:''},
  {emp:'192.168.1.104', status:'실패', date:'2025-10-06 17:32:02', types:[], source:'텍스트', filename:'-', reason:'지원 불가 형식'},
  {emp:'192.168.1.105', status:'실패', date:'2025-10-05 01:19:57', types:[], source:'PPTX', filename:'presentation.pptx', reason:'지원 불가 형식'},
  {emp:'192.168.1.106', status:'성공', date:'2025-10-04 00:15:45', types:['IP'], source:'TXT', filename:'cards.txt', reason:''},
  {emp:'192.168.1.100', status:'실패', date:'2025-10-03 08:02:40', types:[], source:'HWPX', filename:'cards.hwpx', reason:'빈 파일'},
  {emp:'192.168.1.101', status:'성공', date:'2025-10-02 07:50:28', types:['생년월일'], source:'PDF', filename:'draft.pdf', reason:'', suspicious: true},
  {emp:'192.168.1.102', status:'성공', date:'2025-10-01 07:45:15', types:['주민등록번호','카드번호'], source:'XLS', filename:'data.xls', reason:''},
  {emp:'192.168.1.103', status:'성공', date:'2025-09-30 14:33:11', types:['주민등록번호','생년월일'], source:'PDF', filename:'summary.pdf', reason:''},
  {emp:'192.168.1.104', status:'실패', date:'2025-09-29 14:28:59', types:[], source:'DOC', filename:'resume.doc', reason:'손상 파일'},
  {emp:'192.168.1.105', status:'성공', date:'2025-09-28 21:16:54', types:['생년월일'], source:'텍스트', filename:'-', reason:''},
  {emp:'192.168.1.106', status:'성공', date:'2025-09-27 21:11:42', types:['카드번호'], source:'텍스트', filename:'-', reason:'', suspicious: true},
  {emp:'192.168.1.100', status:'성공', date:'2025-09-26 05:59:37', types:['이메일','주민등록번호'], source:'XLSX', filename:'log.xlsx', reason:''},
  {emp:'192.168.1.101', status:'실패', date:'2025-09-25 04:54:25', types:[], source:'DOCX', filename:'draft.docx', reason:'빈 파일'},
  {emp:'192.168.1.102', status:'실패', date:'2025-09-24 04:42:12', types:[], source:'XLSX', filename:'summary.xlsx', reason:'지원 불가 형식'},
  {emp:'192.168.1.103', status:'성공', date:'2025-09-23 11:29:08', types:['IP','전화번호'], source:'TXT', filename:'user_notes.txt', reason:''},
  {emp:'192.168.1.104', status:'성공', date:'2025-09-22 11:25:55', types:['카드번호'], source:'TXT', filename:'summary.txt', reason:'', suspicious: true},
  {emp:'192.168.1.105', status:'성공', date:'2025-09-21 18:12:51', types:['카드번호'], source:'텍스트', filename:'-', reason:''},
  {emp:'192.168.1.106', status:'성공', date:'2025-09-20 18:08:38', types:['주민등록번호','카드번호'], source:'PDF', filename:'draft.pdf', reason:''},
  {emp:'192.168.1.100', status:'성공', date:'2025-09-19 01:56:34', types:['전화번호','이메일'], source:'PDF', filename:'draft.pdf', reason:'', suspicious: true},
  {emp:'192.168.1.101', status:'성공', date:'2025-09-18 01:51:21', types:['카드번호'], source:'TXT', filename:'apply.txt', reason:''},
  {emp:'192.168.1.102', status:'실패', date:'2025-09-17 00:39:09', types:[], source:'TXT', filename:'apply.txt', reason:'지원 불가 형식'},
  {emp:'192.168.1.103', status:'성공', date:'2025-09-16 08:26:04', types:['전화번호'], source:'XLSX', filename:'contacts.xlsx', reason:''},
  {emp:'192.168.1.104', status:'실패', date:'2025-09-15 07:22:52', types:[], source:'DOCX', filename:'data.docx', reason:'지원 불가 형식'},
  {emp:'192.168.1.105', status:'성공', date:'2025-09-14 15:09:48', types:['주민등록번호'], source:'PDF', filename:'cards.pdf', reason:''},
  {emp:'192.168.1.106', status:'성공', date:'2025-09-13 14:05:35', types:['IP'], source:'텍스트', filename:'-', reason:'', suspicious: true},
  {emp:'192.168.1.100', status:'성공', date:'2025-09-12 22:52:31', types:['IP'], source:'XLSX', filename:'contacts.xlsx', reason:''},
  {emp:'192.168.1.101', status:'실패', date:'2025-09-11 22:48:18', types:[], source:'XLSX', filename:'draft.xlsx', reason:'지원 불가 형식'},
  {emp:'192.168.1.102', status:'성공', date:'2025-09-10 21:35:06', types:['이메일','카드번호'], source:'XLSX', filename:'log.xlsx', reason:''},
  {emp:'192.168.1.103', status:'실패', date:'2025-09-09 05:23:01', types:[], source:'텍스트', filename:'-', reason:'지원 불가 형식'},
  {emp:'192.168.1.104', status:'성공', date:'2025-09-08 04:18:49', types:['전화번호'], source:'TXT', filename:'summary.txt', reason:''},
  {emp:'192.168.1.105', status:'성공', date:'2025-09-07 12:06:44', types:['전화번호'], source:'DOCX', filename:'invoice.docx', reason:''},
  {emp:'192.168.1.106', status:'성공', date:'2025-09-06 11:01:32', types:['카드번호'], source:'텍스트', filename:'-', reason:''},
  {emp:'192.168.1.100', status:'성공', date:'2025-09-05 19:49:27', types:['전화번호'], source:'XLSX', filename:'analysis.xlsx', reason:''},
  {emp:'192.168.1.101', status:'성공', date:'2025-09-04 18:45:15', types:['생년월일','전화번호'], source:'XLSX', filename:'invoice.xlsx', reason:''},
  {emp:'192.168.1.102', status:'성공', date:'2025-09-22 02:32:02', types:['이메일'], source:'TXT', filename:'q3_report.pdf', reason:''},
  {emp:'192.168.1.103', status:'실패', date:'2025-09-15 01:20:58', types:[], source:'텍스트', filename:'-', reason:'암호화 파일'},
  {emp:'192.168.1.104', status:'실패', date:'2025-09-23 01:15:45', types:[], source:'XLSX', filename:'draft.docx', reason:'지원 불가 형식'},
  {emp:'192.168.1.105', status:'성공', date:'2025-09-19 15:41:11', types:['IP'], source:'텍스트', filename:'-', reason:''},
  {emp:'192.168.1.106', status:'실패', date:'2025-09-23 22:28:07', types:[], source:'TXT', filename:'data.txt', reason:'손상 파일'},
  {emp:'192.168.1.100', status:'성공', date:'2025-09-14 22:24:54', types:['전화번호'], source:'PDF', filename:'q3_report.pdf', reason:''},
  {emp:'192.168.1.101', status:'실패', date:'2025-09-21 05:12:50', types:[], source:'DOCX', filename:'analysis.docx', reason:'빈 파일'},
  {emp:'192.168.1.102', status:'성공', date:'2025-09-24 05:59:37', types:['전화번호','IP'], source:'텍스트', filename:'-', reason:''},
  {emp:'192.168.1.103', status:'성공', date:'2025-09-24 04:55:25', types:['이메일'], source:'XLSX', filename:'user_notes.xlsx', reason:''},
  {emp:'192.168.1.104', status:'실패', date:'2025-09-24 12:42:20', types:[], source:'텍스트', filename:'-', reason:'빈 파일'},
  {emp:'192.168.1.105', status:'성공', date:'2025-09-24 11:38:08', types:['주민등록번호'], source:'TXT', filename:'notes.txt', reason:''},
  {emp:'192.168.1.106', status:'성공', date:'2025-09-10 19:25:04', types:['주민등록번호'], source:'PDF', filename:'draft.docx', reason:''},
  {emp:'192.168.1.100', status:'성공', date:'2025-09-18 18:21:51', types:['카드번호','주민등록번호'], source:'DOCX', filename:'summary.docx', reason:''},
  {emp:'192.168.1.101', status:'성공', date:'2025-09-15 02:08:47', types:['IP'], source:'TXT', filename:'apply.txt', reason:''},
  {emp:'192.168.1.103', status:'성공', date:'2025-09-14 02:04:34', types:['전화번호'], source:'PPTX', filename:'report.pptx', reason:''},
  {emp:'192.168.1.102', status:'실패', date:'2025-09-13 01:51:22', types:[], source:'HWPX', filename:'document.hwpx', reason:'암호화 파일'},
  {emp:'192.168.1.100', status:'성공', date:'2025-09-12 09:39:17', types:['이메일'], source:'HWP', filename:'memo.hwp', reason:''}
];

/* ====== DOM/유틸 ====== */
const $ = (sel) => document.querySelector(sel);

// 스크롤 방지 함수
function preventScroll(e) {
  e.preventDefault();
}
function fmt(d){ return d.toISOString().slice(0,10); }
function normalizeSource(source) {
  if(['DOCX','DOC'].includes(source)) return 'DOCX/DOC';
  if(['XLSX','XLS'].includes(source)) return 'XLSX/XLS';
  if(['PPTX','PPT'].includes(source)) return 'PPTX';
  if(['HWPX','HWP'].includes(source)) return 'HWPX/HWP';
  return source;
}
function startOfWeek(d){ const day = d.getDay(); const diff = (day===0?-6:1-day); const r=new Date(d); r.setDate(d.getDate()+diff); r.setHours(0,0,0,0); return r; }
function endOfWeek(d){ const s=startOfWeek(d); const r=new Date(s); r.setDate(s.getDate()+6); r.setHours(23,59,59,999); return r; }
function startOfLastWeek(d){ const s=startOfWeek(d); s.setDate(s.getDate()-7); return s; }
function endOfLastWeek(d){ const e=endOfWeek(d); e.setDate(e.getDate()-7); return e; }
function startOfLastMonth(d){ return new Date(d.getFullYear(), d.getMonth()-1, 1); }
function endOfLastMonth(d){ return new Date(d.getFullYear(), d.getMonth(), 0); }

/* 샘플에서 IP가 없을 때 순환 배정 */
const EMP_POOL = ['192.168.1.100','192.168.1.101','192.168.1.102','192.168.1.103','192.168.1.104'];
function attachEmp(rows){
  return rows.map((r,i)=> r.emp ? r : ({...r, emp: EMP_POOL[i % EMP_POOL.length]}));
}

/* 빠른 기간 */
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

/* 필터 적용 */
function applyFilters(){
  const from = $('#from').value;
  const to = $('#to').value;
  const type = $('#type').value;
  const source = $('#source').value;
  const status = $('#status').value;
  const q = $('#q').value.trim().toLowerCase();

  let rows = attachEmp(DATA);

  let filtered = rows.filter(row => {
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
  
  if (hasValidationType) {
    const validationResults = row.types.filter(type => validationTypes.includes(type))
      .map(type => {
        const status = row.status === '성공' ? '성공' : '실패';
        const bgColor = status === '성공' ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)';
        const textColor = status === '성공' ? '#059669' : '#dc2626';
        return `<span style="display:inline-block;background:${bgColor};color:${textColor};padding:2px 8px;border-radius:12px;font-size:12px;margin:2px 4px 2px 0;font-weight:700;">${type}-${status}</span>`;
      }).join('');
    validationEl.innerHTML = validationResults;
  } else {
    validationEl.textContent = '-';
  }
  validationSection.style.display = 'block';
  
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
        if (statusSpan) statusSpan.style.fontSize = fontSize;
      } else if (index % 7 === 3) { // 개인정보 유형 열
        const chips = td.querySelectorAll('.chip');
        chips.forEach(chip => chip.style.fontSize = fontSize);
      }
    });
  }
}

/* 테이블 렌더링 */
function renderRows(rows){
  const $rows = $('#rows');
  const $empty = $('#empty');
  const $summary = $('#summary');
  $rows.innerHTML='';
  if(rows.length===0){
    $empty.hidden = false;
  } else {
    $empty.hidden = true;
    rows.forEach((r, index) => {
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

/* 초기화 */
function resetFilters(){
  $('#from').value=''; $('#to').value=''; $('#type').value=''; $('#source').value='';
  $('#status').value=''; $('#q').value=''; $('#quickDesc').textContent='';
  document.querySelectorAll('.pill').forEach(p=>p.classList.remove('active'));
  applyFilters();
}

// Chart.js 막대 차트
let barChart;
function renderChart(rows){
  const userStats = {};
  rows.forEach(row => {
    if (row.status === '성공') {
      const emp = row.emp || '알 수 없음';
      userStats[emp] = (userStats[emp] || 0) + 1;
    }
  });
  
  const sortedUsers = Object.entries(userStats)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);
  
  const keys = sortedUsers.map(([emp]) => emp);
  const data = sortedUsers.map(([, count]) => count);
  const total = data.reduce((a, b) => a + b, 0);

  if(barChart) barChart.destroy();
  
  barChart = new Chart(document.getElementById('barChart'), {
    type: 'bar',
    data: {
      labels: keys,
      datasets: [{
        data: data,
        backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#a855f7'],
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
          const selectedUser = keys[index];
          $('#q').value = selectedUser;
          applyFilters();
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { display: false },
          grid: { display: false },
          border: { display: false }
        },
        x: {
          grid: { display: false },
          ticks: {
            font: { size: 12 },
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

/* 이벤트 바인딩 */
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.pill').forEach(btn=> btn.addEventListener('click', ()=> setQuickRange(btn.dataset.range)));
  $('#applyBtn').addEventListener('click', applyFilters);
  $('#resetBtn').addEventListener('click', resetFilters);
  document.addEventListener('keydown', (e)=>{ if(e.key==='Enter' && e.target.id==='q') applyFilters(); });
});

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
  const filterDate = localStorage.getItem('filterDate');
  const filterStatus = localStorage.getItem('filterStatus');
  
  if (filterDate) {
    $('#from').value = filterDate;
    $('#to').value = filterDate;
    $('#quickDesc').textContent = `· 선택된 날짜: ${filterDate} ~ ${filterDate}`;
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
  
  if (filterStatus) {
    $('#status').value = filterStatus;
    localStorage.removeItem('filterStatus');
  }
  
  // 필터 적용
  applyFilters();
});

/* 네비게이션 활성화 및 클릭 이벤트 */
document.addEventListener('DOMContentLoaded', function() {
  const navLinks = document.querySelectorAll('.pm-nav a');
  navLinks[2].classList.add('active'); // 사용자별 현황 버튼 활성화
  
  // 네비게이션 클릭 이벤트
  navLinks[0].addEventListener('click', (e) => { e.preventDefault(); location.href = 'detection_details.html'; });
  navLinks[1].addEventListener('click', (e) => { e.preventDefault(); location.href = 'personal_information_type.html'; });
  navLinks[2].addEventListener('click', (e) => { e.preventDefault(); location.href = 'user_type.html'; });
});

/* 로그아웃 버튼 스타일 강제 적용 */
document.addEventListener('DOMContentLoaded', function() {
  const logoutBtn = document.querySelector('.pm-userbox .logout');
  if (logoutBtn) {
    logoutBtn.style.fontSize = '12px';
    logoutBtn.style.fontWeight = '700';
    logoutBtn.style.padding = '6px 8px';
  }
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
  
  // 화면 크기 변경 시 차트 다시 그리기 및 테이블 폰트 조절
  window.addEventListener('resize', () => {
    if(barChart) barChart.resize();
    adjustTableFontSize();
  });
});