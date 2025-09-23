// popup.js
document.addEventListener("DOMContentLoaded", async () => {
  const modeEl = document.getElementById("mode");
  const minEl = document.getElementById("min");
  const inlineEl = document.getElementById("inline");
  const status = document.getElementById("status");

  // load saved
  chrome.storage.local.get(["pii_config"], (res) => {
    const cfg = res.pii_config || { mode: "warn", min_findings_to_alert: 1, show_inline_highlight: true };
    modeEl.value = cfg.mode;
    minEl.value = cfg.min_findings_to_alert;
    inlineEl.checked = cfg.show_inline_highlight;
  });

  document.getElementById("save").addEventListener("click", () => {
    const cfg = {
      mode: modeEl.value,
      min_findings_to_alert: Number(minEl.value) || 1,
      show_inline_highlight: !!inlineEl.checked
    };
    chrome.storage.local.set({ pii_config: cfg }, () => {
      status.innerText = "저장 완료";
      // 콘텐츠 스크립트에 새 설정 전달 (모든 탭)
      chrome.tabs.query({}, (tabs) => {
        for (const t of tabs) {
          chrome.tabs.sendMessage(t.id, { type: "SET_CONFIG", config: cfg }, (resp) => {});
        }
      });
      setTimeout(() => { status.innerText = ""; }, 1500);
    });
  });
});
