// personal_information_type.html 전용 JavaScript

/* 샘플 데이터 (emp 포함) */
const DATA = [
  {emp:'S0001', status:'실패', date:'2025-10-15', types:[], source:'DOCX', filename:'analysis.xlsx', reason:'빈 파일'},
  {emp:'A1023', status:'성공', date:'2025-10-15', types:['IP 주소'], source:'텍스트', filename:'-', reason:''},
  {emp:'A1138', status:'성공', date:'2025-10-15', types:['생년월일'], source:'텍스트', filename:'-', reason:''},
  {emp:'B2047', status:'성공', date:'2025-10-14', types:['IP 주소'], source:'텍스트', filename:'-', reason:''},
  {emp:'B2099', status:'성공', date:'2025-10-13', types:['이메일','카드번호'], source:'PDF', filename:'cards.txt', reason:''},
  {emp:'A1200', status:'실패', date:'2025-10-12', types:[], source:'TXT', filename:'contacts.xlsx', reason:'암호화 파일'},
  {emp:'B3001', status:'성공', date:'2025-10-11', types:['카드번호','이메일'], source:'XLSX', filename:'report.pdf', reason:''},
  {emp:'S0001', status:'실패', date:'2025-10-10', types:[], source:'XLSX', filename:'invoice.pdf', reason:'암호화 파일'},
  {emp:'A1023', status:'성공', date:'2025-10-09', types:['IP 주소'], source:'텍스트', filename:'-', reason:''},
  {emp:'A1138', status:'성공', date:'2025-10-08', types:['전화번호'], source:'텍스트', filename:'-', reason:''},
  {emp:'B2047', status:'성공', date:'2025-10-07', types:['주민등록번호'], source:'텍스트', filename:'-', reason:''},
  {emp:'B2099', status:'실패', date:'2025-10-06', types:[], source:'텍스트', filename:'-', reason:'지원 불가 형식'},
  {emp:'A1200', status:'실패', date:'2025-10-05', types:[], source:'XLSX', filename:'invoice.pdf', reason:'지원 불가 형식'},
  {emp:'B3001', status:'성공', date:'2025-10-04', types:['IP 주소'], source:'TXT', filename:'cards.txt', reason:''},
  {emp:'S0001', status:'실패', date:'2025-10-03', types:[], source:'DOCX', filename:'cards.txt', reason:'빈 파일'},
  {emp:'A1023', status:'성공', date:'2025-10-02', types:['생년월일'], source:'PDF', filename:'draft.docx', reason:''},
  {emp:'A1138', status:'성공', date:'2025-10-01', types:['주민등록번호','카드번호'], source:'XLSX', filename:'data.xlsx', reason:''},
  {emp:'B2047', status:'성공', date:'2025-09-30', types:['주민등록번호','생년월일'], source:'DOCX', filename:'summary.pdf', reason:''},
  {emp:'B2099', status:'실패', date:'2025-09-29', types:[], source:'XLSX', filename:'resume.docx', reason:'손상 파일'},
  {emp:'A1200', status:'성공', date:'2025-09-28', types:['생년월일'], source:'텍스트', filename:'-', reason:''},
  {emp:'B3001', status:'성공', date:'2025-09-27', types:['카드번호'], source:'텍스트', filename:'-', reason:''},
  {emp:'S0001', status:'성공', date:'2025-09-26', types:['이메일','주민등록번호'], source:'XLSX', filename:'log.xlsx', reason:''},
  {emp:'A1023', status:'실패', date:'2025-09-25', types:[], source:'DOCX', filename:'draft.docx', reason:'빈 파일'},
  {emp:'A1138', status:'실패', date:'2025-09-24', types:[], source:'XLSX', filename:'summary.pdf', reason:'지원 불가 형식'},
  {emp:'B2047', status:'성공', date:'2025-09-23', types:['IP 주소','전화번호'], source:'TXT', filename:'user_notes.txt', reason:''},
  {emp:'B2099', status:'성공', date:'2025-09-22', types:['카드번호'], source:'TXT', filename:'summary.pdf', reason:''},
  {emp:'A1200', status:'성공', date:'2025-09-21', types:['카드번호'], source:'텍스트', filename:'-', reason:''},
  {emp:'B3001', status:'성공', date:'2025-09-20', types:['주민등록번호','카드번호'], source:'PDF', filename:'draft.docx', reason:''},
  {emp:'S0001', status:'성공', date:'2025-09-19', types:['전화번호','이메일'], source:'PDF', filename:'draft.docx', reason:''},
  {emp:'A1023', status:'성공', date:'2025-09-18', types:['카드번호'], source:'TXT', filename:'apply.docx', reason:''},
  {emp:'A1138', status:'실패', date:'2025-09-17', types:[], source:'TXT', filename:'apply.docx', reason:'지원 불가 형식'},
  {emp:'B2047', status:'성공', date:'2025-09-16', types:['전화번호'], source:'XLSX', filename:'contacts.xlsx', reason:''},
  {emp:'B2099', status:'실패', date:'2025-09-15', types:[], source:'DOCX', filename:'data.xlsx', reason:'지원 불가 형식'},
  {emp:'A1200', status:'성공', date:'2025-09-14', types:['주민등록번호'], source:'PDF', filename:'cards.txt', reason:''},
  {emp:'B3001', status:'성공', date:'2025-09-13', types:['IP 주소'], source:'텍스트', filename:'-', reason:''},
  {emp:'S0001', status:'성공', date:'2025-09-12', types:['IP 주소'], source:'XLSX', filename:'contacts.xlsx', reason:''},
  {emp:'A1023', status:'실패', date:'2025-09-11', types:[], source:'XLSX', filename:'draft.docx', reason:'지원 불가 형식'},
  {emp:'A1138', status:'성공', date:'2025-09-10', types:['이메일','카드번호'], source:'XLSX', filename:'log.xlsx', reason:''},
  {emp:'B2047', status:'실패', date:'2025-09-09', types:[], source:'텍스트', filename:'-', reason:'지원 불가 형식'},
  {emp:'B2099', status:'성공', date:'2025-09-08', types:['전화번호'], source:'TXT', filename:'summary.pdf', reason:''},
  {emp:'A1200', status:'성공', date:'2025-09-07', types:['전화번호'], source:'DOCX', filename:'invoice.pdf', reason:''},
  {emp:'B3001', status:'성공', date:'2025-09-06', types:['카드번호'], source:'텍스트', filename:'-', reason:''},
  {emp:'S0001', status:'성공', date:'2025-09-05', types:['전화번호'], source:'XLSX', filename:'analysis.xlsx', reason:''},
  {emp:'A1023', status:'성공', date:'2025-09-04', types:['생년월일','전화번호'], source:'XLSX', filename:'invoice.pdf', reason:''},
  {emp:'A1138', status:'성공', date:'2025-09-22', types:['이메일'], source:'TXT', filename:'q3_report.pdf', reason:''},
  {emp:'B2047', status:'실패', date:'2025-09-15', types:[], source:'텍스트', filename:'-', reason:'암호화 파일'},
  {emp:'B2099', status:'실패', date:'2025-09-23', types:[], source:'XLSX', filename:'draft.docx', reason:'지원 불가 형식'},
  {emp:'A1200', status:'성공', date:'2025-09-19', types:['IP 주소'], source:'텍스트', filename:'-', reason:''},
  {emp:'B3001', status:'실패', date:'2025-09-23', types:[], source:'TXT', filename:'data.xlsx', reason:'손상 파일'},
  {emp:'S0001', status:'성공', date:'2025-09-14', types:['전화번호'], source:'PDF', filename:'q3_report.pdf', reason:''},
  {emp:'A1023', status:'실패', date:'2025-09-21', types:[], source:'DOCX', filename:'analysis.xlsx', reason:'빈 파일'},
  {emp:'A1138', status:'성공', date:'2025-09-24', types:['전화번호','IP 주소'], source:'텍스트', filename:'-', reason:''},
  {emp:'B2047', status:'성공', date:'2025-09-24', types:['이메일'], source:'XLSX', filename:'user_notes.txt', reason:''},
  {emp:'B2099', status:'실패', date:'2025-09-24', types:[], source:'텍스트', filename:'-', reason:'빈 파일'},
  {emp:'A1200', status:'성공', date:'2025-09-24', types:['주민등록번호'], source:'TXT', filename:'notes.txt', reason:''},
  {emp:'B3001', status:'성공', date:'2025-09-10', types:['주민등록번호'], source:'PDF', filename:'draft.docx', reason:''},
  {emp:'S0001', status:'성공', date:'2025-09-18', types:['카드번호','주민등록번호'], source:'DOCX', filename:'summary.pdf', reason:''},
  {emp:'A1023', status:'성공', date:'2025-09-15', types:['IP 주소'], source:'TXT', filename:'apply.docx', reason:''}
];

const $ = (sel) => document.querySelector(sel);

// 날짜 유틸
function fmt(d){ return d.toISOString().slice(0,10); }

// 빠른 기간
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

// 필터 적용
function applyFilters(){
  const from = $('#from').value;
  const to = $('#to').value;
  const type = $('#type').value;
  const source = $('#source').value;
  const status = $('#status').value;
  const emp = ($('#emp')?.value || '').trim().toLowerCase();
  const q = $('#q').value.trim().toLowerCase();

  let filtered = DATA.filter(row => {
    if (from && row.date < from) return false;
    if (to && row.date > to) return false;
    if (type && !(row.types || []).includes(type)) return false;
    if (source && row.source !== source) return false;
    if (status && row.status !== status) return false;
    if (emp && !(row.emp||'').toLowerCase().includes(emp)) return false;
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
  '위치 정보': ['장소', 'IP 주소', '조직명'],
  '신분증/증명서': ['주민등록번호', '외국인번호', '여권', '운전면허'],
  '금융 정보': ['카드번호', '계좌번호']
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
  $('#detail-ip').textContent = detail.ip;
  $('#detail-os').textContent = detail.os;
  $('#detail-computer').textContent = detail.computer;
  $('#detail-url').textContent = detail.url;
  $('#detail-browser').textContent = detail.browser;
  $('#detail-llm').textContent = detail.llm;
  $('#detail-source').textContent = row.source;
  
  // 개인정보 유형 칩 스타일링
  const typesEl = $('#detail-types');
  if (row.types && row.types.length > 0) {
    typesEl.innerHTML = row.types.map(type => 
      `<span style="display:inline-block;background:${getTypeColor(type)};color:${getTypeTextColor(type)};padding:2px 8px;border-radius:12px;font-size:12px;margin:2px 4px 2px 0;font-weight:700;">${type}</span>`
    ).join('');
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
}

/* 팝업 닫기 */
function closeDetailModal() {
  $('#detailModal').style.display = 'none';
  document.body.style.overflow = 'auto';
}

// 테이블 렌더
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
}

// Chart.js 파이차트(성공만 집계)
let pieChartInstance = null;

function renderChart(rows){
  const keys = ["전화번호","이메일","주민등록번호","카드번호","IP 주소","생년월일"];
  const counts = Object.fromEntries(keys.map(k=>[k,0]));
  rows.forEach(r=>{
    if (r.status === '성공') (r.types||[]).forEach(t => { if (counts.hasOwnProperty(t)) counts[t]++; });
  });

  const data = keys.map(k=>counts[k]);
  const filteredData = [];
  const filteredLabels = [];
  
  for(let i=0;i<keys.length;i++){
    if(data[i] > 0){
      filteredData.push(data[i]);
      filteredLabels.push(keys[i]);
    }
  }

  if(pieChartInstance) {
    pieChartInstance.destroy();
  }

  const ctx = document.getElementById('pieChart').getContext('2d');
  pieChartInstance = new Chart(ctx, {
    type: 'pie',
    data: {
      labels: filteredLabels,
      datasets: [{
        data: filteredData,
        backgroundColor: ["#3b82f6","#10b981","#f59e0b","#ef4444","#8b5cf6","#14b8a6"]
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      layout: {
        padding: {
          bottom: 30
        }
      },
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            boxWidth: 12,
            font: { size: 11 },
            padding: 20
          }
        },
        datalabels: {
          color: '#fff',
          formatter: (value, ctx) => {
            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
            const percentage = ((value / total) * 100).toFixed(1);
            return percentage + '%\n(' + value + '건)';
          }
        }
      }
    },
    plugins: [ChartDataLabels]
  });
}

// 초기화
function resetFilters(){
  $('#from').value=''; $('#to').value=''; $('#type').value=''; $('#source').value='';
  $('#status').value=''; $('#emp').value=''; $('#q').value=''; $('#quickDesc').textContent='';
  document.querySelectorAll('.pill').forEach(p=>p.classList.remove('active'));
  applyFilters();
}

document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.pill').forEach(btn=> btn.addEventListener('click', ()=> setQuickRange(btn.dataset.range)));
  $('#applyBtn').addEventListener('click', applyFilters);
  $('#resetBtn').addEventListener('click', resetFilters);
  document.addEventListener('keydown', (e)=>{ if(e.key==='Enter' && (e.target.id==='q' || e.target.id==='emp')) applyFilters(); });
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
  setTodayDate();
  // 오늘 범위 표시
  const today = new Date();
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
  document.getElementById('quickDesc').textContent = `· 오늘: ${todayStr} ~ ${todayStr}`;
  // 오늘 버튼 활성화
  document.querySelector('.pill[data-range="today"]').classList.add('active');
  // 필터 적용
  applyFilters();
});

// 차트카드 높이 조절 함수
function adjustChartHeight() {
  const filterCard = document.querySelector('.card[aria-label="필터"]');
  const chartCard = document.querySelector('.chart-card');
  
  setTimeout(() => {
    const filterHeight = filterCard.offsetHeight;
    const minHeight = 400;
    const finalHeight = Math.max(filterHeight, minHeight);
    chartCard.style.height = finalHeight + 'px';
  }, 10);
}

// 화면 크기 변경 시 차트 업데이트
window.addEventListener('resize', () => {
  if (pieChartInstance) {
    pieChartInstance.resize();
  }
  adjustChartHeight();
});

// 초기 높이 설정
window.addEventListener('load', adjustChartHeight);

// 네비게이션 활성화
document.addEventListener('DOMContentLoaded', function() {
  const navLinks = document.querySelectorAll('.pm-nav a');
  navLinks[2].classList.add('active'); // 개인정보 유형별 현황 버튼 활성화
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

// 사용자 정보 업데이트
(function(){
  const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{"empId":"S0001","role":"super"}');
  document.getElementById('userEmp').textContent = userInfo.empId;
  if(userInfo.role === 'super'){
    document.getElementById('accountBtn').style.display = 'block';
  }
})();