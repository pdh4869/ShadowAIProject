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

  // 공통 데이터에서 7일간 시간 추이 데이터 생성
  const generateTrendData = () => {
    const commonData = window.COMMON_DATA || [];
    const highRiskTypes = ['주민등록번호', '외국인등록번호', '운전면허번호', '여권번호', '계좌번호', '카드번호'];
    const data = [];
    const today = new Date();
    
    for (let i = 6; i >= 0; i--) {
      const date = new Date(today);
      date.setDate(today.getDate() - i);
      const dateStr = date.toISOString().split('T')[0];
      
      const dayData = commonData.filter(d => d.date.split(' ')[0] === dateStr);
      const total = dayData.length;
      const highRisk = dayData.filter(d => d.status === '성공' && (d.types || []).some(type => highRiskTypes.includes(type))).length;
      const failed = dayData.filter(d => d.status === '실패').length;
      
      data.push({ date: dateStr, total, highRisk, failed });
    }
    return data;
  };
  const trendData = generateTrendData();

  // 일별 추이 그래프
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

  // 오늘 날짜 기준 사용자별 탐지 빈도 계산
  const calculateContribData = () => {
    const commonData = window.COMMON_DATA || [];
    const today = new Date().toISOString().split('T')[0];
    const highRiskTypes = ['주민등록번호', '외국인등록번호', '운전면허번호', '여권번호', '계좌번호', '카드번호'];
    const userStats = {};
    
    // 오늘 날짜 데이터만 필터링
    const todayData = commonData.filter(row => row.date.split(' ')[0] === today);
    
    todayData.forEach(row => {
      if (row.status === '성공' && row.emp) {
        if (!userStats[row.emp]) {
          userStats[row.emp] = { count: 0, highRisk: 0, totalTypes: 0 };
        }
        userStats[row.emp].count += 1;
        userStats[row.emp].highRisk += (row.types || []).filter(type => highRiskTypes.includes(type)).length;
        userStats[row.emp].totalTypes += (row.types || []).length;
      }
    });
    
    return Object.entries(userStats)
      .map(([name, stats]) => ({ name, count: stats.count, highRisk: stats.highRisk, totalTypes: stats.totalTypes }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);
  };
  
  const contribData = calculateContribData();

  // 금일 기준 소스 통계 계산
  const calculateSourceStats = () => {
    const commonData = window.COMMON_DATA || [];
    const today = new Date().toISOString().split('T')[0];
    const sourceMap = {
      '텍스트': 0, 'PDF': 0, 'DOCX': 0, 'DOC': 0, 'HWPX': 0, 'HWP': 0, 'XLSX': 0, 'XLS': 0, 'PPTX': 0, 'TXT': 0, 'PNG': 0, 'JPG': 0, 'JPEG': 0, 'BMP': 0, 'WEBP': 0, 'GIF': 0, 'TIFF': 0
    };
    
    commonData.forEach(row => {
      if (row.date.split(' ')[0] === today && row.status === '성공' && sourceMap.hasOwnProperty(row.source)) {
        sourceMap[row.source]++;
      }
    });
    
    return [
      { source: '텍스트', count: sourceMap['텍스트'] },
      { source: 'PDF', count: sourceMap['PDF'] },
      { source: 'DOCX/DOC', count: sourceMap['DOCX'] + sourceMap['DOC'] },
      { source: 'HWPX/HWP', count: sourceMap['HWPX'] + sourceMap['HWP'] },
      { source: 'XLSX/XLS', count: sourceMap['XLSX'] + sourceMap['XLS'] },
      { source: 'PPTX', count: sourceMap['PPTX'] },
      { source: 'TXT', count: sourceMap['TXT'] },
      { source: 'PNG', count: sourceMap['PNG'] },
      { source: 'JPG/JPEG', count: sourceMap['JPG'] + sourceMap['JPEG'] },
      { source: 'BMP', count: sourceMap['BMP'] },
      { source: 'WEBP', count: sourceMap['WEBP'] },
      { source: 'GIF', count: sourceMap['GIF'] },
      { source: 'TIFF', count: sourceMap['TIFF'] }
    ];
  };
  
  const sourceStats = calculateSourceStats();
  const totalSources = sourceStats.reduce((sum, s) => sum + s.count, 0);
  
  // 총 건수 업데이트
  const totalSourcesEl = document.getElementById('totalSources');
  if(totalSourcesEl) totalSourcesEl.textContent = totalSources;

  // 오늘 날짜 기준 금일 데이터 추출
  const generateTodayDetections = () => {
    const today = new Date().toISOString().split('T')[0];
    const highRiskTypes = ['주민등록번호', '외국인등록번호', '운전면허번호', '여권번호', '계좌번호', '카드번호'];
    const validationTypes = ['주민등록번호', '카드번호']; // 검증 가능한 타입
    
    // 오늘 날짜 전체 데이터 (성공+실패)
    const commonData = window.COMMON_DATA || [];
    const todayAllData = commonData.filter(d => d.date.split(' ')[0] === today);
    const todaySuccessData = todayAllData.filter(d => d.status === '성공');
    
    const detections = [];
    const validationDetections = []; // 검증 대상 PII만 저장
    
    todaySuccessData.forEach(row => {
      (row.types || []).forEach(type => {
        detections.push({
          date: today,
          type: type,
          emp: row.emp
        });
        
        // 검증 가능한 타입만 별도 저장
        if (validationTypes.includes(type) && row.validation && row.validation[type]) {
          validationDetections.push({
            type: type,
            validated: row.validation[type] === 'valid'
          });
        }
      });
    });
    
    const totalCount = detections.length;
    const totalRecords = todayAllData.length; // 전체 레코드 수 (성공+실패)
    const highRiskCount = detections.filter(d => highRiskTypes.includes(d.type)).length;
    const highRiskPercentage = totalCount > 0 ? Math.round((highRiskCount / totalCount) * 100) : 0;
    
    // 검증 통과율 계산 (카드번호, 주민등록번호만 대상)
    const validatedCount = validationDetections.filter(d => d.validated).length;
    const validationRate = validationDetections.length > 0 ? Math.round((validatedCount / validationDetections.length) * 100) : 0;
    
    return { totalCount, totalRecords, highRiskCount, highRiskPercentage, validationRate, detections };
  };

  // 대시보드 지표 업데이트
  const todayData = generateTodayDetections();
  
  // 총 탐지 수 업데이트 (전체 레코드 수)
  const totalNumEl = document.getElementById('totalNum');
  if(totalNumEl) totalNumEl.textContent = todayData.totalRecords;
  
  // 고위험 PII 비중 업데이트
  const highRiskNumEl = document.getElementById('highRiskNum');
  if(highRiskNumEl) highRiskNumEl.textContent = `${todayData.highRiskPercentage}%`;
  
  // 검증 통과율 업데이트
  const validNumEl = document.getElementById('validNum');
  if(validNumEl) validNumEl.textContent = `${todayData.validationRate}%`;
  
  // 오늘 날짜 기준 탐지 유형 테이블 업데이트
  const typeStats = {};
  const today = new Date().toISOString().split('T')[0];
  const commonData = window.COMMON_DATA || [];
  const todaySuccessData = commonData.filter(row => row.date.split(' ')[0] === today && row.status === '성공');
  
  todaySuccessData.forEach(row => {
    (row.types || []).forEach(type => {
      typeStats[type] = (typeStats[type] || 0) + 1;
    });
  });
  
  const todayTypeTbody = document.getElementById('todayTypeTbody');
  const todayTotal = document.getElementById('todayTotal');
  if(todayTotal) todayTotal.textContent = Object.values(typeStats).reduce((a, b) => a + b, 0);
  
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

  // 공통 데이터에서 개인 식별 의심 데이터 추출 (최신 날짜순)
  const generateSuspiciousDetections = () => {
    const commonData = window.COMMON_DATA || [];
    const suspicious = commonData
      .filter(row => row.suspicious && row.status === '성공')
      .map(row => ({
        date: row.date.split(' ')[0],
        time: row.date.split(' ')[1].substring(0, 5),
        emp: row.emp,
        source: row.filename || row.source,
        fullDate: row.date
      }))
      .sort((a, b) => new Date(b.fullDate) - new Date(a.fullDate));
    return suspicious;
  };

  // 개인 식별 의심 목록 렌더링
  function renderSuspiciousList() {
    const suspicious = generateSuspiciousDetections();
    const suspiciousList = document.getElementById('suspiciousList');
    const totalSuspicious = document.getElementById('totalSuspicious');
    const displayCount = getDisplayCount();
    
    if(totalSuspicious) totalSuspicious.textContent = suspicious.length;
    
    if(suspiciousList) {
      suspiciousList.innerHTML = '';
      suspicious.slice(0, displayCount).forEach(item => {
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

  // 공통 데이터에서 탐지 실패 데이터 추출 (최신 날짜순)
  const generateTodayFailures = () => {
    const commonData = window.COMMON_DATA || [];
    const failures = commonData
      .filter(row => row.status === '실패')
      .map(row => ({
        date: row.date.split(' ')[0],
        time: row.date.split(' ')[1].substring(0, 5),
        emp: row.emp,
        file: row.filename || '-',
        reason: row.reason,
        fullDate: row.date
      }))
      .sort((a, b) => new Date(b.fullDate) - new Date(a.fullDate));
    return failures;
  };

  // 화면 크기에 따른 표시 개수 계산
  function getDisplayCount() {
    const screenWidth = window.innerWidth;
    
    if (screenWidth < 1200) {
      return 5;
    } else {
      return 8;
    }
  }

  function getFailureDisplayCount() {
    const screenWidth = window.innerWidth;
    
    if (screenWidth < 900) {
      return 3;
    } else if (screenWidth < 1200) {
      return 5;
    } else {
      return 8;
    }
  }

  // 탐지 실패 목록 렌더링
  function renderFailureList() {
    const failures = generateTodayFailures();
    const failureList = document.getElementById('failureList');
    const totalFailures = document.getElementById('totalFailures');
    const displayCount = getFailureDisplayCount();
    
    if(totalFailures) totalFailures.textContent = failures.length;
    
    if(failureList) {
      failureList.innerHTML = '';
      failures.slice(0, displayCount).forEach(failure => {
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
  const typeTimestamp = document.getElementById('typeTimestamp');
  const suspiciousTimestamp = document.getElementById('suspiciousTimestamp');
  const failureTimestamp = document.getElementById('failureTimestamp');
  const sourceTimestamp = document.getElementById('sourceTimestamp');
  if(contribTimestamp) contribTimestamp.textContent = timeStr;
  if(typeTimestamp) typeTimestamp.textContent = timeStr;
  if(suspiciousTimestamp) suspiciousTimestamp.textContent = timeStr;
  if(failureTimestamp) failureTimestamp.textContent = timeStr;
  if(sourceTimestamp) sourceTimestamp.textContent = timeStr;

  function getLabelFontSize() {
    const w = window.innerWidth;
    return w < 768 ? 8 : (w < 1024 ? 10 : 12);
  }

  // 사용자 기여도 테이블 생성 (IP)
  const tbody = document.getElementById("contribTbody");
  if(tbody) {
    for(let i = 0; i < 5; i++) {
      const tr = document.createElement('tr');
      if(i < contribData.length) {
        const item = contribData[i];
        const highRiskPercent = Math.round((item.highRisk / item.totalTypes) * 100);
        tr.style.cursor = 'pointer';
        tr.addEventListener('click', () => {
          localStorage.setItem('filterEmp', item.name);
          location.href = 'user_type.html';
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
    
    const sortedStats = [...filteredSourceStats].sort(
      (a, b) => (b.count - a.count) || a.source.localeCompare(b.source)
    );

    new Chart(barChartEl, {
      type: "bar",
      data: { 
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
            const filterValue = Array.isArray(selectedSource) ? selectedSource.join('/') : selectedSource;
            localStorage.setItem('filterSource', filterValue);
            location.href = 'detection_details.html';
          }
        }
      },
      plugins: [ChartDataLabels]
    });
  }

  // 전날 대비 증감률 계산
  const calculateDeltaStats = () => {
    const today = new Date().toISOString().split('T')[0];
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const yesterdayStr = yesterday.toISOString().split('T')[0];
    
    const commonData = window.COMMON_DATA || [];
    const highRiskTypes = ['주민등록번호', '외국인등록번호', '운전면허번호', '여권번호', '계좌번호', '카드번호'];
    
    // 오늘 데이터
    const todayAllData = commonData.filter(d => d.date.split(' ')[0] === today);
    const todaySuccessData = todayAllData.filter(d => d.status === '성공');
    const todayDetections = [];
    const todayValidationDetections = [];
    const validationTypes = ['주민등록번호', '카드번호'];
    
    todaySuccessData.forEach(row => {
      (row.types || []).forEach(type => {
        todayDetections.push({ type });
        
        if (validationTypes.includes(type) && row.validation && row.validation[type]) {
          todayValidationDetections.push({
            type: type,
            validated: row.validation[type] === 'valid'
          });
        }
      });
    });
    
    // 어제 데이터
    const yesterdayAllData = commonData.filter(d => d.date.split(' ')[0] === yesterdayStr);
    const yesterdaySuccessData = yesterdayAllData.filter(d => d.status === '성공');
    const yesterdayDetections = [];
    const yesterdayValidationDetections = [];
    
    yesterdaySuccessData.forEach(row => {
      (row.types || []).forEach(type => {
        yesterdayDetections.push({ type });
        
        if (validationTypes.includes(type) && row.validation && row.validation[type]) {
          yesterdayValidationDetections.push({
            type: type,
            validated: row.validation[type] === 'valid'
          });
        }
      });
    });
    
    // 통계 계산
    const todayTotal = todayAllData.length; // 전체 레코드 수
    const yesterdayTotal = yesterdayAllData.length; // 전체 레코드 수
    const todayDetectionCount = todayDetections.length; // 실제 탐지된 개인정보 건수
    const yesterdayDetectionCount = yesterdayDetections.length; // 실제 탐지된 개인정보 건수
    const totalDelta = yesterdayTotal > 0 ? ((todayTotal - yesterdayTotal) / yesterdayTotal * 100) : 0;
    
    const todayHighRisk = todayDetections.filter(d => highRiskTypes.includes(d.type)).length;
    const yesterdayHighRisk = yesterdayDetections.filter(d => highRiskTypes.includes(d.type)).length;
    const todayHighRiskRatio = todayDetectionCount > 0 ? (todayHighRisk / todayDetectionCount * 100) : 0;
    const yesterdayHighRiskRatio = yesterdayDetectionCount > 0 ? (yesterdayHighRisk / yesterdayDetectionCount * 100) : 0;
    const highRiskDelta = yesterdayHighRiskRatio > 0 ? (todayHighRiskRatio - yesterdayHighRiskRatio) : 0;
    
    const todayValid = todayValidationDetections.filter(d => d.validated).length;
    const yesterdayValid = yesterdayValidationDetections.filter(d => d.validated).length;
    const todayValidRatio = todayValidationDetections.length > 0 ? (todayValid / todayValidationDetections.length * 100) : 0;
    const yesterdayValidRatio = yesterdayValidationDetections.length > 0 ? (yesterdayValid / yesterdayValidationDetections.length * 100) : 0;
    const validDelta = yesterdayValidRatio > 0 ? (todayValidRatio - yesterdayValidRatio) : 0;
    
    return {
      total: { num: todayTotal, delta: Math.round(totalDelta * 10) / 10 },
      highRisk: { num: Math.round(todayHighRiskRatio * 10) / 10, delta: Math.round(highRiskDelta * 10) / 10 },
      valid: { num: Math.round(todayValidRatio * 10) / 10, delta: Math.round(validDelta * 10) / 10 }
    };
  };
  
  const stats = calculateDeltaStats();
  
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

  // 화면 크기 변경 시 목록 재렌더링
  window.addEventListener('resize', function() {
    renderSuspiciousList();
    renderFailureList();
  });
});