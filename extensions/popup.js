// popup.js (랜덤 로그 생성 기능 추가)

document.addEventListener('DOMContentLoaded', updateUI);

/**
 * 로그인 폼 제출 이벤트 처리
 */
document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const employeeId = document.getElementById('employee_id').value;
    const errorMessage = document.getElementById('error-message');
    errorMessage.textContent = '';

    try {
        const response = await fetch('http://127.0.0.1:5001/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ employee_id: employeeId })
        });
        const data = await response.json();

        if (response.ok) {
            chrome.storage.local.set({ token: data.token }, () => {
                console.log('Token stored, user logged in.');
                updateUI();
            });
        } else {
            errorMessage.textContent = data.message || '로그인에 실패했습니다.';
        }
    } catch (error) {
        console.error('Login request failed:', error);
        errorMessage.textContent = '서버에 연결할 수 없습니다.';
    }
});

/**
 * 로그아웃 버튼 클릭 이벤트 처리
 */
document.getElementById('logout-btn').addEventListener('click', () => {
    chrome.storage.local.remove('token', () => {
        console.log('Token removed, user logged out.');
        updateUI();
    });
});

/**
 * '로그 기록하기' 버튼 클릭 이벤트 처리
 */
document.getElementById('send-data-btn').addEventListener('click', async () => {
    const logStatus = document.getElementById('log-status');
    logStatus.textContent = '전송 중...';

    const { token } = await chrome.storage.local.get('token');
    if (!token) {
        logStatus.textContent = '오류: 재로그인이 필요합니다.';
        return;
    }

    try {
        const profileResponse = await fetch('http://127.0.0.1:5001/api/profile', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!profileResponse.ok) throw new Error('프로필 정보를 가져올 수 없습니다.');
        
        const profileData = await profileResponse.json();
        const employeeId = profileData.employee_id;
        
        const fileTypes = ['텍스트', 'pdf', 'docx', 'xlsx', 'txt'];
        const randomFileType = fileTypes[Math.floor(Math.random() * fileTypes.length)];

        let randomFilename = null;
        if (randomFileType !== '텍스트') {
            const randomName = `report_${Math.floor(Math.random() * 10000)}`;
            randomFilename = `${randomName}.${randomFileType}`;
        }

        const allPiiTypes = ['이름', '휴대폰번호', '이메일', '생년월일', '주민등록번호', '외국인등록번호', '운전면허번호', '여권번호', '계좌번호', '신용카드번호', '체크카드번호', '우편번호', 'IP주소'];
        const shuffledPiiTypes = allPiiTypes.sort(() => 0.5 - Math.random());
        const numTypesToPick = Math.floor(Math.random() * 3) + 1;
        const randomPiiTypes = shuffledPiiTypes.slice(0, numTypesToPick);
        
        const piiDataToSend = {
            employee_id: employeeId,
            process_type: 'DETECT',
            file_type_name: randomFileType,
            filename: randomFilename,
            pii_types: randomPiiTypes,
            status: Math.random() > 0.1 ? '성공' : '실패',
            reason: null
        };
        if (piiDataToSend.status === '실패') {
            piiDataToSend.reason = '파일 암호화됨';
            piiDataToSend.pii_types = [];
        }
        
        const logResponse = await fetch('http://127.0.0.1:5001/api/log-pii', { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(piiDataToSend)
        });
        if (!logResponse.ok) throw new Error('로그 기록에 실패했습니다.');
        
        // --- ▼▼▼ (핵심 수정) response -> logResponse 로 변경 ▼▼▼ ---
        const logResult = await logResponse.json();
        // --- ▲▲▲ ---

        console.log('Log sent successfully:', logResult.message);
        logStatus.textContent = '로그 기록 완료!';
        
        setTimeout(() => { logStatus.textContent = ''; }, 2000);

    } catch (error) {
        console.error('Failed to send log:', error);
        logStatus.textContent = error.message;
    }
});

/**
 * UI 상태 업데이트 함수
 */
function updateUI() {
    const loggedOutView = document.getElementById('logged-out-view');
    const loggedInView = document.getElementById('logged-in-view');
    chrome.storage.local.get(['token'], (result) => {
        if (result.token) {
            loggedOutView.style.display = 'none';
            loggedInView.style.display = 'block';
        } else {
            loggedOutView.style.display = 'block';
            loggedInView.style.display = 'none';
        }
    });
}