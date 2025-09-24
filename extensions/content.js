function showLoginModal() {
  if (document.getElementById("login-modal")) return;

  const m = document.createElement("div");
  m.id = "login-modal";
  m.innerHTML = `
    <div style="position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:2147483646;"></div>
    <div style="position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);
                background:#fff;padding:20px;border-radius:10px;width:300px;">
      <h3>로그인</h3>
      <input id="empId" placeholder="사번" style="width:100%;margin-bottom:6px;padding:6px">
      <input id="empPw" type="password" placeholder="비밀번호" style="width:100%;margin-bottom:6px;padding:6px">
      <div style="text-align:right;">
        <button id="loginCancel">취소</button>
        <button id="loginSubmit">로그인</button>
      </div>
    </div>
  `;
  document.body.appendChild(m);

  m.querySelector("#loginCancel").onclick = () => m.remove();

  m.querySelector("#loginSubmit").onclick = async () => {
    const empId = m.querySelector("#empId").value.trim();
    const empPw = m.querySelector("#empPw").value.trim();
    if (!empId || !empPw) return alert("사번/비밀번호 입력");

    try {
      const res = await fetch("http://localhost:5000/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ employeeId: empId, password: empPw })
      });
      const data = await res.json();
      if (res.ok && data.token) {
        chrome.storage.local.set({ piiAuth: { employeeId: empId, token: data.token } });
        alert("로그인 성공");
        m.remove();
      } else {
        alert(data.message || "로그인 실패");
      }
    } catch (err) {
      console.error(err);
      alert("서버 연결 실패");
    }
  };
}

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.action === "showLoginModal") showLoginModal();
});
