// ===== content.js (완성본) =====
(function () {
  // 전송 중복 방지
  const state = { lastText: "", lastTs: 0 };

  // 동적으로 추가되는 file input/드래그&드롭도 커버
  const filesSet = new Set();

  // --- 파일명 수집 (입력창에서 즉시 스캔) ---
  function collectFileNamesFromInputs() {
    const names = [];
    document.querySelectorAll('input[type="file"]').forEach((inp) => {
      try {
        if (inp.files && inp.files.length) {
          for (const f of Array.from(inp.files)) {
            if (f && f.name) names.push(f.name);
          }
        }
      } catch {}
    });
    return names;
  }

  // --- 동적 file input 감시 + 드래그&드롭 파일명 수집 ---
  function observeFileInputs(root = document) {
    // 기존 input
    root.querySelectorAll('input[type="file"]').forEach((inp) => {
      if (inp.__pii_watched) return;
      inp.__pii_watched = true;
      inp.addEventListener(
        "change",
        () => {
          try {
            Array.from(inp.files || [])
              .map((f) => f.name)
              .filter(Boolean)
              .forEach((n) => filesSet.add(n));
          } catch {}
        },
        true
      );
    });
    // 동적 추가
    const mo = new MutationObserver((muts) => {
      muts.forEach((m) => {
        m.addedNodes.forEach((node) => {
          if (node.nodeType !== 1) return;
          if (node.matches?.('input[type="file"]')) {
            if (!node.__pii_watched) {
              node.__pii_watched = true;
              node.addEventListener(
                "change",
                () => {
                  try {
                    Array.from(node.files || [])
                      .map((f) => f.name)
                      .filter(Boolean)
                      .forEach((n) => filesSet.add(n));
                  } catch {}
                },
                true
              );
            }
          }
          node.querySelectorAll?.('input[type="file"]').forEach((inp) => {
            if (!inp.__pii_watched) {
              inp.__pii_watched = true;
              inp.addEventListener(
                "change",
                () => {
                  try {
                    Array.from(inp.files || [])
                      .map((f) => f.name)
                      .filter(Boolean)
                      .forEach((n) => filesSet.add(n));
                  } catch {}
                },
                true
              );
            }
          });
        });
      });
    });
    mo.observe(root, { childList: true, subtree: true });
  }

  function observeDragAndDrop(root = document) {
    root.addEventListener(
      "drop",
      (e) => {
        try {
          Array.from(e.dataTransfer?.files || [])
            .map((f) => f.name)
            .filter(Boolean)
            .forEach((n) => filesSet.add(n));
        } catch {}
      },
      true
    );
  }

  // --- 포커스된 입력값 추출 ---
  function getFocusedText() {
    const a = document.activeElement;
    if (a) {
      if (a.tagName === "TEXTAREA") return a.value || "";
      if (a.tagName === "INPUT" && (a.type === "text" || a.type === "search"))
        return a.value || "";
      if (a.isContentEditable) return a.innerText || a.textContent || "";
    }
    const ta = document.querySelector("textarea,[contenteditable='true']");
    if (!ta) return "";
    return ta.tagName === "TEXTAREA"
      ? ta.value || ""
      : ta.innerText || ta.textContent || "";
  }

  // --- 중복 전송 방지 ---
  function dedup(text) {
    const now = Date.now();
    if (text === state.lastText && now - state.lastTs < 300) return true;
    state.lastText = text;
    state.lastTs = now;
    return false;
  }

  // --- payload 구성 (파일은 문자열 배열) ---
  function buildPayload(text, files) {
    // files: ["a.pdf","b.png"] 형태
    return {
      agent_id: "browser-agent",
      timestamp: new Date().toISOString(),
      source_url: location.href,
      page_title: document.title,
      raw_text: text || "",
      files: files || [],
      tab: { ua: navigator.userAgent },
    };
  }

  // --- 백그라운드로 전송 ---
  function send(payload) {
    console.log("[content] send", payload);
    if (chrome?.runtime?.sendMessage) {
      chrome.runtime.sendMessage({ type: "PII_EVENT", payload }, (response) => {
        if (chrome.runtime.lastError) {
          console.warn(
            "[content] sendMessage error:",
            chrome.runtime.lastError.message
          );
        } else {
          console.log("[content] sendMessage ack:", response);
        }
      });
    } else {
      console.error("[content] chrome.runtime.sendMessage not available");
    }
  }

  // --- 전송 트리거 (Enter/버튼) ---
  document.addEventListener(
    "keydown",
    async (e) => {
      if (e.key !== "Enter" || e.shiftKey || e.ctrlKey || e.altKey || e.metaKey)
        return;
      const text = (getFocusedText() || "").trim();
      if (!text || dedup(text)) return;

      // 파일명: 동적 감시로 쌓인 것 + 현재 input 스캔을 합침
      const names = [
        ...new Set([...Array.from(filesSet), ...collectFileNamesFromInputs()]),
      ];
      send(buildPayload(text, names));
      filesSet.clear();
    },
    true
  );

  function isSendLike(el) {
    if (!el) return false;
    const t = (el.innerText || el.textContent || "").toLowerCase();
    const aria = (el.getAttribute?.("aria-label") || "").toLowerCase();
    const testid = (el.getAttribute?.("data-testid") || "").toLowerCase();
    return (
      t.includes("send") ||
      t.includes("전송") ||
      t.includes("보내기") ||
      aria.includes("send") ||
      aria.includes("전송") ||
      testid.includes("send")
    );
  }

  document.addEventListener(
    "click",
    async (e) => {
      let el = e.target;
      for (let i = 0; i < 4 && el; i++, el = el.parentElement) {
        if (isSendLike(el)) {
          const text = (getFocusedText() || "").trim();
          if (!text || dedup(text)) return;

          const names = [
            ...new Set([
              ...Array.from(filesSet),
              ...collectFileNamesFromInputs(),
            ]),
          ];
          send(buildPayload(text, names));
          filesSet.clear();
          break;
        }
      }
    },
    true
  );

  // 초기화
  observeFileInputs();
  observeDragAndDrop();

  console.log("[content] script loaded on", window.location.href);
})();
