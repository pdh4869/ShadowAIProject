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
        // 익명 모드에서는 프로필이 없으므로 오류 응답
        sendResponse({ error: "No profile available in anonymous mode." });
        return true;
    }
});
