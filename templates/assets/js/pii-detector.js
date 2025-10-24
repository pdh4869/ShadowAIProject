// PII 탐지 및 자동 전송 모듈

class PIIDetector {
    constructor() {
        this.patterns = {
            name: /[가-힣]{2,4}|[A-Za-z]{2,20}\s[A-Za-z]{2,20}/g,
            phone: /01[0-9]-?\d{3,4}-?\d{4}/g,
            email: /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g,
            ssn: /\d{6}-?[1-4]\d{6}/g,
            card: /\d{4}-?\d{4}-?\d{4}-?\d{4}/g,
            ip: /\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b/g,
            account: /\d{3}-?\d{2,6}-?\d{2,7}/g
        };
        this.setupTextInputMonitoring();
    }

    detectPII(text) {
        const detected = [];
        const matches = {};

        for (const [type, pattern] of Object.entries(this.patterns)) {
            const found = text.match(pattern);
            if (found && found.length > 0) {
                detected.push(type);
                matches[type] = found;
            }
        }

        // 조합위험도 판단 (2개 이상 PII 유형 탐지 시)
        if (detected.length >= 2) {
            detected.push('combination_risk');
        }

        // ps는 name의 별칭으로 처리
        if (detected.includes('name')) {
            detected.push('ps');
        }

        return {
            types: [...new Set(detected)],
            matches: matches
        };
    }

    async sendPIILog(detectedPII, inputText) {
        if (detectedPII.types.length === 0) return;

        const logData = {
            file_type_name: "text_input",
            ip_address: this.getClientIP(),
            filename: "user_text_input.txt",
            status: "성공",
            reason: `텍스트 입력 PII 탐지: ${detectedPII.types.join(', ')}`,
            pii_types: detectedPII.types,
            hostname: window.location.hostname,
            os_info: navigator.platform,
            user_agent: navigator.userAgent,
            session_url: window.location.href
        };

        try {
            const response = await fetch('/api/log-pii', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(logData)
            });

            if (response.ok) {
                console.log('PII 탐지 로그 전송 성공:', detectedPII.types);
                
                // 사용자에게 탐지 알림 표시
                this.showDetectionNotification(detectedPII.types);
                
                // 메인 페이지인 경우 3초 후 자동 새로고침
                if (window.location.pathname === '/' || window.location.pathname === '/main') {
                    setTimeout(() => {
                        window.location.reload();
                    }, 3000);
                }
            }
        } catch (error) {
            console.error('PII 로그 전송 실패:', error);
        }
    }

    getClientIP() {
        // 실제 환경에서는 서버에서 IP를 가져와야 하지만, 
        // 테스트용으로 랜덤 IP 생성
        return `192.168.1.${Math.floor(Math.random() * 254) + 1}`;
    }

    showDetectionNotification(types) {
        const typeMap = {
            'name': '이름', 'phone': '전화번호', 'email': '이메일', 
            'ssn': '주민등록번호', 'card': '카드번호', 'ip': 'IP주소',
            'account': '계좌번호', 'combination_risk': '조합위험도', 'ps': '이름'
        };
        
        const koreanTypes = types.map(type => typeMap[type] || type).join(', ');
        
        // 간단한 알림 표시
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed; top: 20px; right: 20px; z-index: 9999;
            background: #10b981; color: white; padding: 12px 20px;
            border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            font-size: 14px; max-width: 300px;
        `;
        notification.textContent = `PII 탐지: ${koreanTypes}`;
        
        document.body.appendChild(notification);
        
        // 3초 후 제거
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 3000);
    }

    setupTextInputMonitoring() {
        let debounceTimer;
        let lastDetectedTypes = new Set();
        
        // 모든 텍스트 입력 요소 모니터링
        document.addEventListener('input', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    const text = e.target.value;
                    if (text.length > 5) { // 최소 길이 체크
                        const detected = this.detectPII(text);
                        if (detected.types.length > 0) {
                            // 중복 탐지 방지
                            const currentTypes = new Set(detected.types);
                            const isDifferent = detected.types.length !== lastDetectedTypes.size || 
                                              detected.types.some(type => !lastDetectedTypes.has(type));
                            
                            if (isDifferent) {
                                this.sendPIILog(detected, text);
                                lastDetectedTypes = currentTypes;
                            }
                        }
                    }
                }, 2000); // 2초 디바운스로 증가
            }
        });

        // 붙여넣기 이벤트도 모니터링
        document.addEventListener('paste', (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                setTimeout(() => {
                    const text = e.target.value;
                    const detected = this.detectPII(text);
                    if (detected.types.length > 0) {
                        this.sendPIILog(detected, text);
                    }
                }, 100);
            }
        });
    }
}

// 페이지 로드 시 PII 탐지기 초기화
document.addEventListener('DOMContentLoaded', () => {
    window.piiDetector = new PIIDetector();
    console.log('PII 탐지기가 활성화되었습니다.');
});

// 수동 PII 탐지 함수 (테스트용)
window.testPIIDetection = function(text) {
    if (window.piiDetector) {
        const result = window.piiDetector.detectPII(text);
        console.log('탐지된 PII:', result);
        return result;
    }
};