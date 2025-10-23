// main.html 전용 JavaScript

// Flask에서 전달받는 실제 데이터 변수 정의 (backend.py의 show_dashboard 함수 참조)
const KPI_DATA = window.KPI_DATA || {};
const TREND_DATA = window.TREND_DATA || [];
const TODAY_STATS = window.TODAY_STATS || {types: []};
const TOP_USERS = window.TOP_USERS || [];
const SOURCE_STATS = window.SOURCE_STATS || [];
const PII_TYPE_OVERALL_STATS = window.PII_TYPE_OVERALL_STATS || [];
const RECENT_FAILURES = window.RECENT_FAILURES || [];
const RECENT_SUSPICIOUS = window.RECENT_SUSPICIOUS || [];

// ⭐ 수정: 새로운 매핑 정보로 업데이트
const PII_TYPE_MAP_KR = {
  'phone': '전화번호', 'email': '이메일', 'ssn': '주민등록번호', 'card': '카드번호',
  'account': '계좌번호', 'ps': '이름', 'image_face': '얼굴이미지', 'name': '이름',
  'person': '이름', 'rrn': '주민등록번호', 'alien_registration': '외국인등록번호',
  'driver_license': '운전면허번호', 'passport': '여권번호', 'birth': '생년월일',
  'ip': 'IP', 'org': '조직/기관', 'position': '직책', 'student_id': '학번',
  'combination_risk': '조합위험도', 'IP': 'IP', 'PS': '이름', 'COMBINATION_RISK': '조합위험도',
  // 백엔드에서 DB 조회 시 이미 한글로 나올 수 있는 항목도 포함 (안전 보장)
  '주민등록번호': '주민등록번호', '카드번호': '카드번호', '계좌번호': '계좌번호',
  '전화번호': '전화번호', '이메일': '이메일', '이름': '이름'
};

document.addEventListener('DOMContentLoaded', function() {
  
  // 1. 사용자 정보 업데이트 (로컬 스토리지 기반 더미 로직은 유지)
  const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{"empId":"S0001","role":"super"}');
  const userEmpEl = document.getElementById('userEmp');
  const accountBtnEl = document.getElementById('accountBtn');
  if(userEmpEl) userEmpEl.textContent = userInfo.empId;
  if(userInfo.role === 'super' && accountBtnEl){
    accountBtnEl.style.display = 'block';
  }

  // 2. Indicator cards (KPI_DATA 사용)
  const totalDelta = document.getElementById('totalDelta');
  if(totalDelta) {
    totalDelta.textContent = (KPI_DATA.total_delta > 0 ? '+' : '') + KPI_DATA.total_delta + '%';
    totalDelta.className = 'delta ' + (KPI_DATA.total_delta_class || 'bad');
    document.getElementById('totalNum').textContent = KPI_DATA.total_num || 0;
  }
  
  const riskDelta = document.getElementById('highRiskDelta');
  if(riskDelta) {
    riskDelta.textContent = (KPI_DATA.high_risk_delta > 0 ? '+' : '') + KPI_DATA.high_risk_delta + '%';
    riskDelta.className = 'delta ' + (KPI_DATA.high_risk_delta_class || 'ok');
    
    // ⭐ 수정: 소수점 둘째 자리까지 강제 표시하여 낮은 값도 명확히 보이게 함
    const highRiskNum = KPI_DATA.high_risk_num || 0; 
    document.getElementById('highRiskNum').textContent = `${highRiskNum.toFixed(2)}%`;
  }
  
  const validDelta = document.getElementById('validDelta');
  if(validDelta) {
    // 백엔드에서 계산된 valid_delta와 valid_num 사용
    validDelta.textContent = (KPI_DATA.valid_delta > 0 ? '+' : '') + KPI_DATA.valid_delta + '%';
    validDelta.className = 'delta ' + (KPI_DATA.valid_delta_class || 'ok');
    document.getElementById('validNum').textContent = `${KPI_DATA.valid_num}%`;
  }

  // ⭐ 3. 일별 추이 그래프 (TREND_DATA 사용)
  const trendChartEl = document.getElementById("trendChart");

  // ⭐ 디버깅을 위한 로그 추가
  console.log("TREND_DATA:", TREND_DATA);
  console.log("trendChartEl exists:", !!trendChartEl);
  console.log("TREND_DATA length:", TREND_DATA.length);
  
  // 각 날짜별 데이터 확인
  TREND_DATA.forEach((data, index) => {
    console.log(`Day ${index}: ${data.date} - Total: ${data.total}, HighRisk: ${data.highRisk}, Failed: ${data.failed}`);
  });

  if(trendChartEl && TREND_DATA.length > 0) {
    try { // ⭐ 차트 로드 실패 시 디버깅을 위해 try-catch 블록 추가
        const labels = TREND_DATA.map(d => d.date.slice(5));
        const totalData = TREND_DATA.map(d => d.total);
        const highRiskData = TREND_DATA.map(d => d.highRisk);
        const failedData = TREND_DATA.map(d => d.failed);

        console.log("Chart Labels:", labels);
        console.log("Chart Total Data:", totalData);
        
        new Chart(trendChartEl, {
          type: "bar",
          data: {
            labels: labels,
            datasets: [
              { label: "총탐지", data: totalData, backgroundColor: "#2563eb" },
              { label: "고위험", data: highRiskData, backgroundColor: "#16a34a" },
              { label: "탐지실패", data: failedData, backgroundColor: "#dc2626" }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: { 
              y: { 
                beginAtZero: true,
                min: 0, // 최소값 0 강제
                // ⭐ Y축 눈금 간격을 1 단위로 표시
                ticks: {
                    precision: 0, 
                    stepSize: 1 // 1 단위로 눈금 설정
                }
              },
              x: { grid: { display: false } }
            },
            onClick: (event, elements) => {
              if (elements.length > 0) {
                const index = elements[0].index;
                const selectedDate = TREND_DATA[index].date;
                window.location.href = `/detection_details?from=${selectedDate}&to=${selectedDate}`;
              }
            }
          }
        });
    } catch (error) {
        console.error("Error drawing trend chart:", error);
    }
  } else if(trendChartEl) {
     // 데이터가 없는 경우 (TREND_DATA.length가 0인 경우)
     trendChartEl.parentElement.innerHTML = '<p class="text-center text-gray-500 py-4">최근 탐지 이력 데이터가 부족합니다.</p>';
  }

  // 4. 사용자별 탐지 빈도 테이블 (TOP_USERS 사용)
  const tbody = document.getElementById("contribTbody");
  if(tbody) {
    tbody.innerHTML = ''; 
    TOP_USERS.slice(0, 5).forEach(item => {
      const tr = document.createElement('tr');
      const highRiskPercent = Math.round(item.high_risk); 
      tr.style.cursor = 'pointer';
      tr.addEventListener('click', () => {
        window.location.href = `/user_type?q=${encodeURIComponent(item.account)}`;
      });
      tr.innerHTML = `<td>${item.account}</td><td>${item.count}</td><td>${highRiskPercent}%</td>`;
      tbody.appendChild(tr);
    });
    for(let i = TOP_USERS.length; i < 5; i++) {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>-</td><td>-</td><td>-</td>`;
        tbody.appendChild(tr);
    }
    document.getElementById('contribTimestamp').textContent = new Date().toLocaleString('ko-KR', { hour12: false, dateStyle: 'short', timeStyle: 'short' }) + ' 기준';
  }

  // 5. 금일 탐지 유형 테이블 (TODAY_STATS 사용)
  console.log("=== TODAY_STATS 디버깅 ===");
  console.log("TODAY_STATS:", TODAY_STATS);
  console.log("Types:", TODAY_STATS.types);
  
  const todayTypeTbody = document.getElementById('todayTypeTbody');
  const totalDetectedPii = TODAY_STATS.types ? TODAY_STATS.types.reduce((a, b) => a + b.count, 0) : 0;
  
  if(todayTypeTbody) {
    todayTypeTbody.innerHTML = '';
    // TODAY_STATS.types가 비어있지 않다면, TOP 5를 표시
    (TODAY_STATS.types || []).slice(0, 5).forEach(item => {
      const tr = document.createElement('tr');
      tr.style.cursor = 'pointer';

      // ⭐ 수정: PII 유형을 한글로 매핑
      const displayType = PII_TYPE_MAP_KR[item.type] || item.type;

      tr.addEventListener('click', () => {
        window.location.href = `/personal_information_type?type=${encodeURIComponent(item.type)}`;
      });
      tr.innerHTML = `<td>${displayType}</td><td>${item.count}</td>`;
      todayTypeTbody.appendChild(tr);
    });
    // 5개 미만인 경우 나머지 행을 '-'으로 채움
    for(let i = (TODAY_STATS.types || []).length; i < 5; i++) {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>-</td><td>-</td>`;
        todayTypeTbody.appendChild(tr);
    }
    document.getElementById('typeTimestamp').textContent = new Date().toLocaleString('ko-KR', { hour12: false, dateStyle: 'short', timeStyle: 'short' }) + ' 기준';
  }
  
  // 6. 파일 확장자별 분포 차트 (SOURCE_STATS 사용)
  const barChartEl = document.getElementById("chartSourceBar");
  if(barChartEl) {
    const filteredSourceStats = SOURCE_STATS.filter(s => s.count > 0);
    const filteredTotal = filteredSourceStats.reduce((sum, s) => sum + s.count, 0);
    
    const sortedStats = [...filteredSourceStats].sort(
      (a, b) => (b.count - a.count) || a.source.localeCompare(b.source)
    );

    const totalSourcesEl = document.getElementById('totalSources');
    if(totalSourcesEl) totalSourcesEl.textContent = filteredTotal;
    document.getElementById('sourceTimestamp').textContent = new Date().toLocaleString('ko-KR', { hour12: false, dateStyle: 'short', timeStyle: 'short' }) + ' 기준';

    const getLabelFontSize = () => {
      const w = window.innerWidth;
      return w < 768 ? 8 : (w < 1024 ? 10 : 12);
    };

    new Chart(barChartEl, {
      type: "bar",
      data: { 
        // 파일 확장자는 그대로 표시
        labels: sortedStats.map(s => s.source),
        datasets: [{ 
          data: sortedStats.map(s => s.count),
          backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6','#06b6d4', '#ec4899', '#84cc16', '#f97316', '#a855f7','#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f','#edc948', '#b07aa1', '#ff9da7', '#9c755f', '#bab0ab'].slice(0, sortedStats.length),
          barThickness: 'flex', 
          categoryPercentage: 0.8 
        }] 
      },
      options: { 
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        layout: { padding: { left: 12, right: 12, top: 16, bottom: 10 } },
        plugins: { 
          legend: { display: false }, 
          datalabels: { display: false }
        },
        scales: { 
          y: { beginAtZero: true, grid: { display: false }, ticks: { display: true, autoskip: false, font: { size: getLabelFontSize() }, padding: 0, color: '#000000' }, border: { display: true, tickLength: 0 } }, 
          x: { display: true, drawBorder: true, lineWidth: 1, grid: { display: true }, ticks: { precision: 0, font: { size: getLabelFontSize() }, padding: 0, maxRotation: 0 } } 
        },
        onClick: (event, elements) => {
          if (elements.length > 0) {
            const index = elements[0].index;
            const selectedSource = sortedStats[index].source;
            window.location.href = `/detection_details?source=${encodeURIComponent(selectedSource)}`;
          }
        }
      },
      plugins: [ChartDataLabels]
    });
  }

  // ⭐ 7. 개인 식별 의심 목록 (RECENT_SUSPICIOUS 사용) - (총 건수 표시 수정)
  function renderSuspiciousList() {
    const suspiciousList = document.getElementById('suspiciousList');
    const totalSuspicious = document.getElementById('totalSuspicious');
    const displayCount = window.innerWidth < 1200 ? 5 : 8;

    if(totalSuspicious) totalSuspicious.textContent = RECENT_SUSPICIOUS.length; // RECENT_SUSPICIOUS.length로 수정
    document.getElementById('suspiciousTimestamp').textContent = new Date().toLocaleString('ko-KR', { hour12: false, dateStyle: 'short', timeStyle: 'short' }) + ' 기준';
    
    if(suspiciousList) {
      suspiciousList.innerHTML = '';
      RECENT_SUSPICIOUS.slice(0, displayCount).forEach(item => {
        const li = document.createElement('li');
        li.style.listStyle = 'none';
        li.style.lineHeight = '16px';
        li.style.cursor = 'pointer';
        const shortDate = item.timestamp.slice(2, 10).replace(/-/g, '/'); // YY/MM/DD
        const time = item.timestamp.slice(11, 16); // HH:MM
        const source = item.file || item.file_type_name || '-';
        li.textContent = `• ${shortDate} ${time} - ${item.ip_address} / ${source}`;
        suspiciousList.appendChild(li);
      });
      if (RECENT_SUSPICIOUS.length === 0) {
          suspiciousList.innerHTML = `<li class="text-gray-500 text-center py-2">탐지된 의심 내역이 없습니다.</li>`;
      }
    }
  }
  renderSuspiciousList();

  // 8. 탐지 실패 목록 (RECENT_FAILURES 사용)
  function renderFailureList() {
    const failureList = document.getElementById('failureList');
    const totalFailures = document.getElementById('totalFailures');
    const displayCount = window.innerWidth < 900 ? 3 : (window.innerWidth < 1200 ? 5 : 8);
    
    if(totalFailures) totalFailures.textContent = RECENT_FAILURES.length;
    document.getElementById('failureTimestamp').textContent = new Date().toLocaleString('ko-KR', { hour12: false, dateStyle: 'short', timeStyle: 'short' }) + ' 기준';

    if(failureList) {
      failureList.innerHTML = '';
      RECENT_FAILURES.slice(0, displayCount).forEach(failure => {
        const li = document.createElement('li');
        li.style.listStyle = 'none';
        li.style.lineHeight = '16px';
        li.style.cursor = 'pointer';
        li.addEventListener('click', () => {
          window.location.href = `/detection_details?status=${encodeURIComponent('실패')}`;
        });
        const shortDate = failure.timestamp.slice(2, 10).replace(/-/g, '/'); // YY/MM/DD
        const time = failure.timestamp.slice(11, 16); // HH:MM
        const file = failure.file || '-';
        li.textContent = `• ${shortDate} ${time} - ${failure.ip_address} / ${file} (${failure.reason})`;
        failureList.appendChild(li);
      });
      if (RECENT_FAILURES.length === 0) {
          failureList.innerHTML = `<li class="text-gray-500 text-center py-2">탐지 실패 내역이 없습니다.</li>`;
      }
    }
  }
  renderFailureList();
  
  // 9. 화면 크기 변경 시 목록 재렌더링
  window.addEventListener('resize', function() {
    renderSuspiciousList();
    renderFailureList();
  });
});