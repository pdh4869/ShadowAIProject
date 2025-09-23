// background.js
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "NOTIFY") {
    const { title, message } = msg;
    chrome.notifications.create({
      type: "basic",
      iconUrl: "icon128.png",
      title: title || "PII 알림",
      message: message || ""
    });
    sendResponse({ ok: true });
  } else if (msg.type === "GET_CONFIG") {
    chrome.storage.local.get(["pii_config"], (res) => {
      sendResponse({ ok: true, config: res.pii_config || null });
    });
    return true; // async
  } else if (msg.type === "SET_CONFIG") {
    chrome.storage.local.set({ pii_config: msg.config }, () => sendResponse({ ok: true }));
    return true;
  }
});

// 팝업/콘텐츠와 통신: 콘텐츠 알림 쉽게 호출
chrome.runtime.onMessageExternal?.addListener?.(() => {});
