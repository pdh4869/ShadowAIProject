// login.html 페이지로부터 메시지를 수신 대기
chrome.runtime.onMessageExternal.addListener((message, sender, sendResponse) => {
    if (message.action === "storeToken") {
        // 전달받은 토큰을 chrome.storage에 안전하게 저장
        chrome.storage.local.set({ token: message.token }, () => {
            console.log("Token stored successfully.");
            sendResponse({ status: "success" });
        });
        return true; // 비동기 응답을 위해 true를 반환
    }
});

// popup.js로부터 메시지를 수신 대기
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === 'getProfile') {
        // 저장된 토큰을 가져옵니다.
        chrome.storage.local.get(['token'], async (result) => {
            if (!result.token) {
                sendResponse({ error: "Not logged in. Please log in first." });
                return;
            }

            try {
                // 토큰을 헤더에 담아 보호된 API를 호출합니다.
                const response = await fetch('http://127.0.0.1:5001/api/profile', {
                    method: 'GET',
                    headers: {
                        'Authorization': `Bearer ${result.token}`
                    }
                });

                const data = await response.json();

                if (response.ok) {
                    sendResponse({ data: data });
                } else {
                    // 토큰이 만료되었거나 유효하지 않을 경우
                    sendResponse({ error: data.message || 'Failed to fetch profile.' });
                }
            } catch (error) {
                sendResponse({ error: 'Network error or server is down.' });
            }
        });

        return true; // 비동기 응답을 위해 true를 반환
    }
});