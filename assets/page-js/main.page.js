// main.html 전용 JavaScript

document.addEventListener('DOMContentLoaded', function() {
  // 사용자 정보 업데이트
  const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{"empId":"S0001","role":"super"}');
  const userEmpEl = document.getElementById('userEmp');
  const accountBtnEl = document.getElementById('accountBtn');
  if(userEmpEl) userEmpEl.textContent = userInfo.empId;
  if(userInfo.role === 'super' && accountBtnEl){
    accountBtnEl.style.display = 'block';
  }

  // 오늘 기준 7일간 시간 추이 데이터 생성
  const generateTrendData = () => {
    const data = [];
    const today = new Date();
    for (let i = 6; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(today.getDate() - i);
      const dateStr = date.toISOString().split('T')[0];
      data.push({
        date: dateStr,
        total: Math.floor(Math.random() * 30) + 20,
        highRisk: Math.floor(Math.random() * 15) + 5,
        failed: Math.floor(Math.random() * 5) + 1
      });
    }
    return data;
  };
  const trendData = generateTrendData();

  // 시간 추이 그래프
  const trendChartEl = document.getElementById("trendChart");
  if(trendChartEl) {
    new Chart(trendChartEl, {
      type: "bar",
      data: {
        labels: trendData.map(d => d.date.slice(5)),
        datasets: [
          { label: "총탐지", data: trendData.map(d => d.total), backgroundColor: "#2563eb" },
          { label: "고위험", data: trendData.map(d => d.highRisk), backgroundColor: "#16a34a" },
          { label: "탐지실패", data: trendData.map(d => d.failed), backgroundColor: "#dc2626" }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { 
          y: { beginAtZero: true },
          x: { grid: { display: false } }
        },
        onClick: (event, elements) => {
          if (elements.length > 0) {
            const index = elements[0].index;
            const selectedDate = trendData[index].date;
            localStorage.setItem('filterDate', selectedDate);
            location.href = 'detection_details.html';
          }
        }
      }
    });
  }

  // 기존 차트들
  const detectionsOverTime = [
    { date: "2025-09-18", count: 3 },
    { date: "2025-09-19", count: 7 },
    { date: "2025-09-20", count: 5 },
    { date: "2025-09-21", count: 8 },
    { date: "2025-09-22", count: 4 },
  ];

  // 사용자 기여도 데이터 (IP)
  const contribData = [
    { name: "192.168.1.100", count: 45, highRisk: 12 },
    { name: "192.168.1.101", count: 38, highRisk: 8 },
    { name: "192.168.1.102", count: 32, highRisk: 15 },
    { name: "192.168.1.103", count: 28, highRisk: 6 },
    { name: "192.168.1.104", count: 25, highRisk: 9 }
  ];

  const sourceStats = [
    { source: "텍스트", count: 25 },
    { source: "PDF", count: 50 },
    { source: ["DOCX", "DOC"], count: 30 },
    { source: ["XLSX", "XLS"], count: 22 },
    { source: "PPTX", count: 15 },
    { source: ["HWPX", "HWP"], count: 12 },
    { source: "TXT", count: 18 }
  ];
  const totalSources = sourceStats.reduce((sum, s) => sum + s.count, 0);

  // 금일 PII 탐지 데이터 생성
  const generateTodayDetections = () => {
    const today = new Date().toISOString().split('T')[0];
    const highRiskTypes = ['주민등록번호', '외국인등록번호', '운전면허번호', '여권번호', '계좌번호', '카드번호'];
    const allTypes = ['이름', '전화번호', '이메일', '생년월일', '주민등록번호', '외국인등록번호', '운전면허번호', '여권번호', '계좌번호', '카드번호', 'IP', '직책', '조직/기관'];
    
    const detections = [];
    for (let i = 0; i < 45; i++) {
      const type = allTypes[Math.floor(Math.random() * allTypes.length)];
      const isValidated = Math.random() > 0.15; // 85% 확률로 검증 통과
      detections.push({
        date: today,
        type: type,
        emp: ['192.168.1.100', '192.168.1.101', '192.168.1.102', '192.168.1.103', '192.168.1.104'][Math.floor(Math.random() * 5)],
        validated: isValidated
      });
    }
    
    const totalCount = detections.length;
    const highRiskCount = detections.filter(d => highRiskTypes.includes(d.type)).length;
    const highRiskPercentage = totalCount > 0 ? Math.round((highRiskCount / totalCount) * 100) : 0;
    
    // 검증 통과율 계산 (Luhn/체크섬 통과율)
    const validatedCount = detections.filter(d => d.validated).length;
    const validationRate = totalCount > 0 ? Math.round((validatedCount / totalCount) * 100) : 0;
    
    return { totalCount, highRiskCount, highRiskPercentage, validationRate, detections };
  };

  // 대시보드 지표 업데이트
  const todayData = generateTodayDetections();
  
  // 총 탐지 수 업데이트
  const totalNumEl = document.getElementById('totalNum');
  if(totalNumEl) totalNumEl.textContent = todayData.totalCount;
  
  // 고위험 PII 비중 업데이트
  const highRiskNumEl = document.getElementById('highRiskNum');
  if(highRiskNumEl) highRiskNumEl.textContent = `${todayData.highRiskPercentage}%`;
  
  // 검증 통과율 업데이트
  const validNumEl = document.getElementById('validNum');
  if(validNumEl) validNumEl.textContent = `${todayData.validationRate}%`;
  
  // 금일 탐지 유형 테이블 업데이트
  const typeStats = {};
  todayData.detections.forEach(d => {
    typeStats[d.type] = (typeStats[d.type] || 0) + 1;
  });
  
  const todayTypeTbody = document.getElementById('todayTypeTbody');
  const todayTotal = document.getElementById('todayTotal');
  if(todayTotal) todayTotal.textContent = todayData.totalCount;
  
  if(todayTypeTbody) {
    const sortedTypes = Object.entries(typeStats).sort((a, b) => b[1] - a[1]);
    for(let i = 0; i < 5; i++) {
      const tr = document.createElement('tr');
      if(i < sortedTypes.length) {
        const [type, count] = sortedTypes[i];
        tr.style.cursor = 'pointer';
        tr.addEventListener('click', () => {
          localStorage.setItem('filterType', type);
          location.href = 'personal_information_type.html';
        });
        tr.innerHTML = `<td>${type}</td><td>${count}</td>`;
      } else {
        tr.innerHTML = `<td>-</td><td>-</td>`;
      }
      todayTypeTbody.appendChild(tr);
    }
  }

  // 금일 개인 식별 의심 데이터 생성
  const generateSuspiciousDetections = () => {
    const today = new Date().toISOString().split('T')[0];
    const sources = ['text', 'report.pdf', 'data.xlsx', 'info.docx', 'backup.txt', 'analysis.pdf'];
    const suspicious = [
      { date: today, time: '15:42', emp: '192.168.1.100', source: sources[Math.floor(Math.random() * sources.length)] },
      { date: today, time: '13:28', emp: '192.168.1.102', source: sources[Math.floor(Math.random() * sources.length)] },
      { date: today, time: '11:15', emp: '192.168.1.103', source: sources[Math.floor(Math.random() * sources.length)] },
      { date: today, time: '09:33', emp: '192.168.1.101', source: sources[Math.floor(Math.random() * sources.length)] },
      { date: today, time: '16:07', emp: '192.168.1.104', source: sources[Math.floor(Math.random() * sources.length)] },
      { date: today, time: '14:51', emp: '192.168.1.105', source: sources[Math.floor(Math.random() * sources.length)] },
      { date: today, time: '12:30', emp: '192.168.1.106', source: sources[Math.floor(Math.random() * sources.length)] },
      { date: today, time: '10:15', emp: '192.168.1.107', source: sources[Math.floor(Math.random() * sources.length)] }
    ];
    return suspicious.sort((a, b) => b.time.localeCompare(a.time));
  };

  // 개인 식별 의심 목록 렌더링
  function renderSuspiciousList() {
    const suspicious = generateSuspiciousDetections();
    const suspiciousList = document.getElementById('suspiciousList');
    const totalSuspicious = document.getElementById('totalSuspicious');
    
    if(totalSuspicious) totalSuspicious.textContent = suspicious.length;
    
    if(suspiciousList) {
      suspiciousList.innerHTML = '';
      suspicious.slice(0, 8).forEach(item => {
        const li = document.createElement('li');
        li.style.listStyle = 'none';
        li.style.lineHeight = '16px';
        li.style.cursor = 'pointer';
        li.addEventListener('click', () => {
          localStorage.setItem('filterStatus', '개인 식별 의심');
          location.href = 'detection_details.html';
        });
        const shortDate = item.date.slice(2).replace(/-/g, '/');
        li.textContent = `• ${shortDate} ${item.time} - ${item.emp} / ${item.source}`;
        suspiciousList.appendChild(li);
      });
    }
  }
  renderSuspiciousList();

  // 금일 탐지 실패 데이터 생성
  const generateTodayFailures = () => {
    const today = new Date().toISOString().split('T')[0];
    const failures = [
      { date: today, time: '14:23', emp: '192.168.1.100', file: 'secret.pdf', reason: '암호화 파일' },
      { date: today, time: '11:45', emp: '192.168.1.103', file: 'test.docx', reason: '손상 파일' },
      { date: today, time: '09:12', emp: '192.168.1.102', file: 'data.xlsx', reason: '빈 파일' },
      { date: today, time: '16:30', emp: '192.168.1.101', file: 'report.pdf', reason: '지원 불가 형식' },
      { date: today, time: '13:15', emp: '192.168.1.104', file: 'info.txt', reason: '액세스 거부' },
      { date: today, time: '08:45', emp: '192.168.1.105', file: 'backup.zip', reason: '암호화 파일' },
      { date: today, time: '07:30', emp: '192.168.1.108', file: 'data2.xlsx', reason: '권한 없음' },
      { date: today, time: '17:15', emp: '192.168.1.109', file: 'report2.pdf', reason: '파일 손상' }
    ];
    return failures.sort((a, b) => b.time.localeCompare(a.time));
  };

  // 탐지 실패 목록 렌더링
  function renderFailureList() {
    const failures = generateTodayFailures();
    const failureList = document.getElementById('failureList');
    const totalFailures = document.getElementById('totalFailures');
    
    if(totalFailures) totalFailures.textContent = failures.length;
    
    if(failureList) {
      failureList.innerHTML = '';
      failures.slice(0, 8).forEach(failure => {
        const li = document.createElement('li');
        li.style.listStyle = 'none';
        li.style.lineHeight = '16px';
        li.style.cursor = 'pointer';
        li.addEventListener('click', () => {
          localStorage.setItem('filterStatus', '실패');
          location.href = 'detection_details.html';
        });
        const shortDate = failure.date.slice(2).replace(/-/g, '/');
        li.textContent = `• ${shortDate} ${failure.time} - ${failure.emp} / ${failure.file} (${failure.reason})`;
        failureList.appendChild(li);
      });
    }
  }
  renderFailureList();

  // 현재 시간 설정
  const now = new Date();
  const timeStr = now.getFullYear() + '.' + String(now.getMonth()+1).padStart(2,'0') + '.' + String(now.getDate()).padStart(2,'0') + ' ' + String(now.getHours()).padStart(2,'0') + ':' + String(now.getMinutes()).padStart(2,'0') + ' 기준';
  const contribTimestamp = document.getElementById('contribTimestamp');
  const suspiciousTimestamp = document.getElementById('suspiciousTimestamp');
  const failureTimestamp = document.getElementById('failureTimestamp');
  if(contribTimestamp) contribTimestamp.textContent = timeStr;
  if(suspiciousTimestamp) suspiciousTimestamp.textContent = timeStr;
  if(failureTimestamp) failureTimestamp.textContent = timeStr;

  // 사용자 기여도 테이블 생성 (IP)
  const tbody = document.getElementById("contribTbody");
  if(tbody) {
    for(let i = 0; i < 5; i++) {
      const tr = document.createElement('tr');
      if(i < contribData.length) {
        const item = contribData[i];
        const highRiskPercent = Math.round((item.highRisk / item.count) * 100);
        tr.style.cursor = 'pointer';
        tr.addEventListener('click', () => {
          localStorage.setItem('filterEmp', item.name);
          location.href = 'detection_details.html';
        });
        tr.innerHTML = `<td>${item.name}</td><td>${item.count}</td><td>${highRiskPercent}%</td>`;
      } else {
        tr.innerHTML = `<td>-</td><td>-</td><td>-</td>`;
      }
      tbody.appendChild(tr);
    }
  }

  const barChartEl = document.getElementById("chartSourceBar");
  if(barChartEl) {
    // 데이터가 0보다 큰 항목만 필터링
    const filteredSourceStats = sourceStats.filter(s => s.count > 0);
    const filteredTotal = filteredSourceStats.reduce((sum, s) => sum + s.count, 0);
    
    new Chart(barChartEl, {
      type: "bar",
      data: { 
        labels: filteredSourceStats.map(s => s.source), 
        datasets: [{ 
          data: filteredSourceStats.map(s => s.count), 
          backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899'].slice(0, filteredSourceStats.length), 
          barThickness: 'flex', 
          categoryPercentage: 0.8 
        }] 
      },
      options: { 
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: { top: 40, bottom: 0 } },
        plugins: { 
          legend: { display: false }, 
          datalabels: { 
            anchor: 'end', 
            align: 'top', 
            color: '#374151', 
            font: { size: 10 }, 
            formatter: (v) => filteredTotal > 0 ? ((v/filteredTotal)*100).toFixed(1)+'%\n(' + v + '건)' : '0%\n(0건)'
          } 
        },
        scales: { 
          y: { beginAtZero: true, grid: { display: false }, ticks: { display: false }, border: { display: false } }, 
          x: { grid: { display: false }, ticks: { font: { size: 10 }, padding: 0, maxRotation: 0 } } 
        },
        onClick: (event, elements) => {
          if (elements.length > 0) {
            const index = elements[0].index;
            const selectedSource = filteredSourceStats[index].source;
            const filterValue = Array.isArray(selectedSource) ? selectedSource.join('/') : selectedSource;
            localStorage.setItem('filterSource', filterValue);
            location.href = 'detection_type.html';
          }
        }
      },
      plugins: [ChartDataLabels]
    });
  }

  // 통계 카드 데이터 업데이트
  const todayTypeStats = [
    { type: "전화번호", count: 10, isHighRisk: false, validCount: 9 },
    { type: "이메일", count: 8, isHighRisk: false, validCount: 7 },
    { type: "주민등록번호", count: 5, isHighRisk: true, validCount: 4 },
    { type: "카드번호", count: 3, isHighRisk: true, validCount: 3 },
    { type: "IP", count: 2, isHighRisk: false, validCount: 2 }
  ];
  const todayTotalStats = todayTypeStats.reduce((a,b)=>a+b.count,0);
  const highRiskCount = todayTypeStats.filter(item => item.isHighRisk).reduce((a,b)=>a+b.count,0);
  const validCount = todayTypeStats.reduce((a,b)=>a+b.validCount,0);
  const highRiskRatio = ((highRiskCount / todayTotalStats) * 100).toFixed(1);
  const validRatio = ((validCount / todayTotalStats) * 100).toFixed(1);
  
  const stats = {
    total: { num: todayTotalStats, delta: 12.5 },
    highRisk: { num: parseFloat(highRiskRatio), delta: 3.2 },
    valid: { num: parseFloat(validRatio), delta: 5.1 }
  };
  
  const totalDelta = document.getElementById('totalDelta');
  if(totalDelta) {
    totalDelta.textContent = (stats.total.delta > 0 ? '+' : '') + stats.total.delta + '%';
    totalDelta.className = 'delta ' + (stats.total.delta > 0 ? 'ok' : 'bad');
  }
  
  const riskDelta = document.getElementById('highRiskDelta');
  if(riskDelta) {
    riskDelta.textContent = (stats.highRisk.delta > 0 ? '+' : '') + stats.highRisk.delta + '%';
    riskDelta.className = 'delta ' + (stats.highRisk.delta > 0 ? 'bad' : 'ok');
  }
  
  const validDelta = document.getElementById('validDelta');
  if(validDelta) {
    validDelta.textContent = (stats.valid.delta > 0 ? '+' : '') + stats.valid.delta + '%';
    validDelta.className = 'delta ' + (stats.valid.delta > 0 ? 'ok' : 'bad');
  }
});