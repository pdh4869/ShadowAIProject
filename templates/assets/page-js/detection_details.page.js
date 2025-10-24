// detection_details.page.js - Flask 백엔드 데이터 사용 (updated)

const $ = (sel) => document.querySelector(sel);

// PII 타입 영어-한글 매핑
const PII_TYPE_MAP = {
  'phone': '전화번호',
  'email': '이메일',
  'ssn': '주민등록번호',
  'card': '카드번호',
  'account': '계좌번호',
  'ps': '이름',
  'image_face': '얼굴이미지',
  'name': '이름',
  'person': '이름',
  'rrn': '주민등록번호',
  'alien_registration': '외국인등록번호',
  'alien_reg': '외국인등록번호',
  'driver_license': '운전면허번호',
  'passport': '여권번호',
  'birth': '생년월일',
  'ip': 'IP',
  'org': '조직/기관',
  'position': '직책',
  'student_id': '학번',
  'combination_risk': '조합위험도',
  'lc': '주소',
  'luhn': '카드번호',
  '이름': '이름',
  'IP': 'IP',
  'PS': '이름',
  'COMBINATION_RISK': '조합위험도',
  'LC': '주소'
};

// PII 타입을 한글로 변환하는 함수
function translatePIIType(type) {
  if (!type) return '-';
  const lower = type.toLowerCase();
  // Luhn을 카드번호로 변환
  if (lower === 'luhn') return '카드번호';
  return PII_TYPE_MAP[lower] || type;
}

// Flask에서 전달받은 실제 데이터 사용
const DATA = window.DETECTION_LOGS || [];
const CHART_DATA = window.BAR_CHART_DATA || [];

// 스크롤 방지 함수
function preventScroll(e) {
  e.preventDefault();
}

// 날짜 포맷 함수
function fmt(d) { 
  return d.toISOString().slice(0,10); 
}

// 오늘 날짜 자동 설정
function setTodayDate() {
  const today = new Date();
  const todayStr = fmt(today);
  $('#from').value = todayStr;
  $('#to').value = todayStr;
}



// 테이블의 PII 타입 칩을 한글로 변환하고 색상 적용
function translateTableChips() {
  document.querySelectorAll('.chip').forEach(chip => {
    const originalText = chip.textContent.trim();
    const koreanText = translatePIIType(originalText);
    chip.textContent = koreanText;
    
    // 색상 적용
    chip.style.background = getTypeColor(originalText);
    chip.style.color = getTypeTextColor(originalText);
    chip.style.fontWeight = '700';
  });
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
  // URL 파라미터가 없으면 오늘 날짜 설정
  if (!$('#from').value && !$('#to').value) {
    setTodayDate();
    const today = new Date();
    const todayStr = fmt(today);
    $('#quickDesc').textContent = `· 오늘: ${todayStr} ~ ${todayStr}`;
    document.querySelector('.pill[data-range="today"]')?.classList.add('active');
  }
  
  // 차트 렌더링
  renderChart();
  adjustTableFontSize();
  translateTableChips();
  
  // 테이블 행 클릭 이벤트
  document.querySelectorAll('#rows tr').forEach(tr => {
    tr.addEventListener('click', function() {
      const logId = this.dataset.logId;
      const log = DATA.find(l => l.id == logId);
      if (log) openDetailModal(log);
    });
  });
  
  // 모달 이벤트
  $('#closeModal').addEventListener('click', closeDetailModal);
  $('#detailModal').addEventListener('click', function(e) {
    if (e.target === this) closeDetailModal();
  });
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closeDetailModal();
  });
});

// 빠른 날짜 범위 설정
document.querySelectorAll('.pill').forEach(btn => {
  btn.addEventListener('click', () => setQuickRange(btn.dataset.range));
});

function setQuickRange(kind) {
  const now = new Date();
  let from, to, label = '';
  
  if (kind === 'today') { 
    from = new Date(now);
    to = new Date(now);
    label = '오늘'; 
  } else if (kind === 'lastweek') { 
    from = new Date(now);
    from.setDate(now.getDate() - 6);
    to = new Date(now);
    label = '지난 주'; 
  } else if (kind === 'lastmonth') { 
    from = new Date(now);
    from.setMonth(now.getMonth() - 1, 1);
    to = new Date(now);
    to.setMonth(now.getMonth() - 1 + 1, 0);
    label = '지난 달'; 
  } else { 
    return; 
  }
  
  $('#from').value = fmt(from);
  $('#to').value = fmt(to);
  $('#quickDesc').textContent = `· ${label}: ${fmt(from)} ~ ${fmt(to)}`;
  
  document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
  const btn = document.querySelector(`.pill[data-range="${kind}"]`);
  if (btn) btn.classList.add('active');
}

// 필터 적용 버튼
$('#applyBtn').addEventListener('click', applyFilters);
$('#resetBtn').addEventListener('click', resetFilters);

function applyFilters() {
  const params = new URLSearchParams();
  
  const from = $('#from').value;
  const to = $('#to').value;
  const type = $('#type').value;
  const source = $('#source').value;
  const status = $('#status').value;
  const q = $('#q').value.trim();
  
  // 탐지 유형 매핑 (이미 정확한 값이므로 매핑 불필요)
  const mappedSource = source;
  
  if (from) params.append('from', from);
  if (to) params.append('to', to);
  if (type) params.append('type', type);
  if (source) params.append('source', source);
  if (status) params.append('status', status);
  if (q) params.append('q', q);
  
  window.location.search = params.toString();
}

function resetFilters() {
  window.location.href = window.location.pathname;
}

// Enter 키로 검색
document.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && e.target.id === 'q') {
    applyFilters();
  }
});

// 개인정보 유형 그룹 분류 (한글 기준)
const PII_GROUPS = {
  '연락처 정보': ['전화번호', '이메일'],
  '신원 정보': ['이름', '생년월일'],
  '위치 정보': ['IP', '직책', '조직/기관'],
  '신분증/증명서': ['주민등록번호', '외국인등록번호', '운전면허번호', '여권번호'],
  '금융 정보': ['계좌번호', '카드번호'],
  '생체 정보': ['얼굴이미지'],
  '기타': ['조합위험도', '학번']
};

const GROUP_COLORS = {
  '연락처 정보': 'rgba(59,130,246,0.15)',
  '신원 정보': 'rgba(6,182,212,0.15)',
  '위치 정보': 'rgba(245,158,11,0.15)',
  '신분증/증명서': 'rgba(236,72,153,0.15)',
  '금융 정보': 'rgba(139,92,246,0.15)',
  '생체 정보': 'rgba(220,38,38,0.15)',
  '기타': 'rgba(107,114,128,0.15)'
};

const GROUP_TEXT_COLORS = {
  '연락처 정보': '#1e40af',
  '신원 정보': '#0891b2',
  '위치 정보': '#d97706',
  '신분증/증명서': '#be185d',
  '금융 정보': '#7c3aed',
  '생체 정보': '#dc2626',
  '기타': '#374151'
};

function getTypeGroup(type) {
  // 영어를 한글로 변환
  const koreanType = translatePIIType(type);
  
  for (const [group, types] of Object.entries(PII_GROUPS)) {
    if (types.includes(koreanType)) return group;
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

// 테이블 폰트 크기 조절
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

// 상세 모달 열기 - 초기화에서 처리

function openDetailModal(log) {
  // 상태
  const statusEl = $('#detail-status');
  statusEl.textContent = log.status;
  statusEl.style.color = log.status === '성공' ? '#059669' : '#dc2626';
  
  // 기본 정보
  $('#detail-emp').textContent = log.ip_address || '-';
  $('#detail-date').textContent = log.timestamp || '-';
  
  // 시스템 정보
  $('#detail-ip').textContent = log.ip_address || '-';
  $('#detail-os').textContent = log.os_info || log.os || '-';
  $('#detail-computer').textContent = log.hostname || '-';
  
  // 웹 정보
  $('#detail-browser').textContent = log.browser || '-';
  $('#detail-llm').textContent = log.llm_type_name || '-';
  $('#detail-url').textContent = log.url || '-';
  
  // 탐지 정보
  $('#detail-source').textContent = log.file_type_name || '-';
  
  // 파일명 (텍스트인 경우 숨김)
  const filenameSection = $('#filename-section');
  if (log.file_type_name === '텍스트') {
    filenameSection.style.display = 'none';
  } else {
    filenameSection.style.display = 'block';
    $('#detail-filename').textContent = log.filename || '-';
  }
  
  // 개인정보 유형 - pii_type_counts 또는 pii_types_with_counts 사용
  const typesEl = $('#detail-types');
  
  if (log.pii_type_counts && Object.keys(log.pii_type_counts).length > 0) {
    // pii_type_counts 객체 사용
    typesEl.innerHTML = Object.entries(log.pii_type_counts).map(([type, count]) => {
      const koreanType = translatePIIType(type);
      return `<span style="display:inline-block;background:${getTypeColor(type)};color:${getTypeTextColor(type)};padding:4px 8px;border-radius:12px;font-size:12px;margin:2px 4px 2px 0;font-weight:700;">${koreanType}: ${count}</span>`;
    }).join('');
  } else if (log.pii_types_with_counts && Array.isArray(log.pii_types_with_counts)) {
    // pii_types_with_counts 배열 사용
    typesEl.innerHTML = log.pii_types_with_counts.map(item => {
      const [type, count] = item.split(':');
      const koreanType = translatePIIType(type);
      return `<span style="display:inline-block;background:${getTypeColor(type)};color:${getTypeTextColor(type)};padding:4px 8px;border-radius:12px;font-size:12px;margin:2px 4px 2px 0;font-weight:700;">${koreanType}: ${count}</span>`;
    }).join('');
  } else {
    typesEl.textContent = '-';
  }

  // 검증 결과
  const validationSection = $('#validation-section');
  if (log.validation_results && Array.isArray(log.validation_results) && log.validation_results.length > 0) {
    validationSection.style.display = 'block';
    $('#detail-validation').innerHTML = log.validation_results.map(result => {
      const match = result.match(/(valid|invalid) \(([^)]+)\)/);
      if (match) {
        const isValid = match[1] === 'valid';
        const piiType = match[2];
        const koreanType = translatePIIType(piiType);
        const status = isValid ? '성공' : '실패';
        return `<span style="display:inline-block;background:${isValid ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)'};color:${isValid ? '#059669' : '#dc2626'};padding:4px 8px;border-radius:12px;font-size:12px;margin:2px 4px 2px 0;font-weight:700;">${koreanType}: ${status}</span>`;
      }
      return '';
    }).join('');
  } else {
    validationSection.style.display = 'none';
  }
  
  // 개인 식별 의심
  const suspiciousEl = $('#detail-suspicious');
  if (log.suspicious === true) {
    suspiciousEl.innerHTML = '<span style="display:inline-block;background:rgba(220,38,38,0.15);color:#dc2626;padding:4px 8px;border-radius:12px;font-size:12px;font-weight:700;">의심</span>';
  } else {
    suspiciousEl.textContent = '-';
  }

  // 실패 사유
  const reasonSection = $('#reason-section');
  if (log.reason && log.reason.trim()) {
    reasonSection.style.display = 'block';
    $('#detail-reason').textContent = log.reason;
  } else {
    reasonSection.style.display = 'none';
  }
  
  $('#detailModal').style.display = 'block';
  document.body.style.overflow = 'hidden';
  document.addEventListener('wheel', preventScroll, { passive: false });
  document.addEventListener('touchmove', preventScroll, { passive: false });
}

function closeDetailModal() {
  $('#detailModal').style.display = 'none';
  document.body.style.overflow = '';
  document.removeEventListener('wheel', preventScroll);
  document.removeEventListener('touchmove', preventScroll);
}



// Chart.js 막대 차트
let barChart;

function getLabelFontSize() {
  const w = window.innerWidth;
  return w < 768 ? 8 : (w < 1024 ? 10 : 12);
}

function renderChart() {
  // 차트 라벨을 한글로 변환
  const labels = CHART_DATA.map(item => translatePIIType(item.type));
  const data = CHART_DATA.map(item => item.count);
  const total = data.reduce((a, b) => a + b, 0);
  
  const colors = [
    '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
    '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#a855f7',
    '#4e79a7', '#f28e2b', '#e15759'
  ];
  
  if (barChart) barChart.destroy();
  
  barChart = new Chart($('#barChart'), {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: labels.map((_, i) => colors[i % colors.length]),
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
          const selectedType = CHART_DATA[index].type; // 원본 영어 타입 사용
          const params = new URLSearchParams(window.location.search);
          params.set('source', selectedType);
          window.location.search = params.toString();
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
            font: { size: getLabelFontSize() },
            color: '#000000'
          }
        }
      }
    }
  });
  
  // 라벨 추가 플러그인
  Chart.register({
    id: 'customLabels',
    afterDraw: function(chart) {
      if (chart.canvas.id !== 'barChart') return;
      
      const ctx = chart.ctx;
      ctx.save();
      ctx.font = '12px Arial';
      ctx.fillStyle = '#000000';
      ctx.textAlign = 'center';
      
      chart.data.datasets[0].data.forEach((value, index) => {
        if (value > 0) {
          const meta = chart.getDatasetMeta(0);
          const bar = meta.data[index];
          const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : '0';
          ctx.fillText(`${percentage}%(${value}건)`, bar.x, bar.y - 15);
        }
      });
      ctx.restore();
    }
  });
}

// 화면 크기 변경 시
window.addEventListener('resize', () => {
  if (barChart) barChart.resize();
  adjustTableFontSize();
});