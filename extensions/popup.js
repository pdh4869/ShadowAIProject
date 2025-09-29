document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('log-form').addEventListener('submit', handleLogFormSubmit);
});

async function handleLogFormSubmit(e) {
    e.preventDefault();
    const logStatus = document.getElementById('log-status-message');
    logStatus.textContent = '전송 중...';

    try {
        const employeeId = document.getElementById('employee_id').value;
        const filename = document.getElementById('log-filename').value || null;
        const piiTypesInput = document.getElementById('log-pii-types').value;
        const fileTypeName = document.getElementById('log-file-type').value || null;
        const status = document.getElementById('log-status').value;
        const reason = document.getElementById('log-reason').value || null;

        if (!employeeId) {
            logStatus.textContent = '오류: Employee ID를 입력하세요.';
            return;
        }

        // --- ⚠️ 수정된 부분 ⚠️ ---
        const piiTypes = piiTypesInput
            ? piiTypesInput.split(',').map(type => ({ type_name: type.trim() }))
            : [];
        // --- ⚠️ 수정된 부분 끝 ⚠️ ---
        
        const piiDataToSend = {
            employee_id: employeeId,
            process_type: 'DETECT',
            file_type_name: fileTypeName,
            filename: filename,
            pii_types: piiTypes,
            status: status,
            reason: reason
        };

        const logResponse = await fetch('http://127.0.0.1:5001/api/log-pii', { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(piiDataToSend)
        });
        
        if (!logResponse.ok) {
            const errorData = await logResponse.json();
            throw new Error(errorData.message || '로그 기록에 실패했습니다.');
        }

        const logResult = await logResponse.json();
        console.log('Log sent successfully:', logResult.message);
        logStatus.textContent = '로그 기록 완료!';
        
        setTimeout(() => { logStatus.textContent = ''; }, 2000);

    } catch (error) {
        console.error('Failed to send log:', error);
        logStatus.textContent = `오류: ${error.message}`;
    }
}