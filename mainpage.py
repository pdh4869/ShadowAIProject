from flask import Flask, render_template_string, request, redirect, url_for, session, flash, jsonify, send_file
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
import os
import io

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_secret_key_1234567890")
app.permanent_session_lifetime = timedelta(minutes=10)  # 세션 10분

# ----------------------
# DB 설정
# ----------------------
DB_NAME = "resume_portal"
DB_USER = "root"
DB_PASSWORD = "mysql"
DB_HOST = "localhost"

def init_db():
    """DB와 테이블이 없으면 생성"""
    conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD)
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} DEFAULT CHARACTER SET 'utf8mb4'")
    conn.database = DB_NAME

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS uploads (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        filename VARCHAR(255),
        filedata LONGBLOB,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    cursor.close()
    conn.close()
    print("DB & 테이블 준비 완료!")

# ----------------------
# HTML 템플릿
# ----------------------
HEADER_HTML = """
<header class="bg-white shadow-md w-full">
  <div class="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
    <h1 class="text-2xl font-bold text-gray-800">
        <a href="/" class="hover:text-gray-900">Resume Portal</a>
    </h1>
    <nav>
      {% if 'user' in session %}
        <a href="/my-resumes" class="text-gray-600 hover:text-gray-900 mx-2">My Resumes</a>
        <span class="mx-2 text-gray-800">Hello, {{ session['user'] }}</span>
        <a href="/logout" class="text-white bg-red-500 hover:bg-red-600 px-3 py-1 rounded ml-2">Logout</a>
      {% else %}
        <a href="/login" class="text-white bg-blue-500 hover:bg-blue-600 px-3 py-1 rounded ml-2">Login</a>
        <a href="/signup" class="text-white bg-green-500 hover:bg-green-600 px-3 py-1 rounded ml-2">Sign Up</a>
      {% endif %}
    </nav>
  </div>
</header>
"""

MAIN_PAGE_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Resume Portal</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 flex flex-col min-h-screen">

""" + HEADER_HTML + """

<main class="flex-grow flex flex-col justify-center items-center px-4 py-10">
<div class="bg-white shadow-lg rounded-lg p-8 max-w-lg w-full">
<h2 class="text-xl font-semibold text-gray-700 mb-6 text-center">Upload Your Resume</h2>

{% if 'user' in session %}
<form id="uploadForm" class="flex flex-col gap-4" enctype="multipart/form-data">
    <input type="file" name="file" accept=".pdf,.docx,.hwp"
           class="border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" required>
    <button type="submit" class="bg-blue-500 text-white rounded px-4 py-2 hover:bg-blue-600 transition">Upload</button>
</form>

<div id="status" class="mt-4 text-center text-gray-600"></div>
{% else %}
<p class="text-gray-600 text-center">로그인 후 이력서를 업로드할 수 있습니다.</p>
{% endif %}
</div>
</main>

<footer class="bg-white shadow-inner mt-auto">
<div class="max-w-7xl mx-auto px-4 py-4 text-center text-gray-500">
&copy; 2025 Team Project. All rights reserved.
</div>
</footer>

<script>
const uploadForm = document.getElementById('uploadForm');
const status = document.getElementById('status');

if (uploadForm) {
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(uploadForm);
        status.textContent = "Uploading...";

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            status.textContent = result.message || "Upload successful!";
        } catch (err) {
            console.error(err);
            status.textContent = "Upload failed!";
        }
    });
}
</script>

</body>
</html>
"""

LOGIN_PAGE_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Login</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 flex flex-col min-h-screen">

""" + HEADER_HTML + """

<main class="flex-grow flex flex-col justify-center items-center px-4 py-10">
<div class="bg-white shadow-lg rounded-lg p-8 w-full max-w-md">
<h2 class="text-xl font-semibold text-gray-700 mb-6 text-center">Login</h2>

<form method="POST" class="flex flex-col gap-4 w-full">
  <input type="text" name="username" placeholder="Username" class="border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" required>
  <input type="password" name="password" placeholder="Password" class="border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" required>
  <button type="submit" class="bg-blue-500 text-white rounded px-4 py-2 hover:bg-blue-600 transition">Login</button>
  {% if error %}
    <p class="text-red-500 text-center">{{ error }}</p>
  {% endif %}
</form>
<div class="text-center mt-4">
  <a href="/signup" class="text-blue-500 hover:underline">Sign Up</a>
</div>
</div>
</main>

</body>
</html>
"""

SIGNUP_PAGE_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sign Up</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 flex flex-col min-h-screen">

""" + HEADER_HTML + """

<main class="flex-grow flex flex-col justify-center items-center px-4 py-10">
<div class="bg-white shadow-lg rounded-lg p-8 w-full max-w-md">
<h2 class="text-xl font-semibold text-gray-700 mb-6 text-center">Sign Up</h2>

<form method="POST" class="flex flex-col gap-4 w-full">
  <input type="text" name="username" placeholder="Username" class="border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500" required>
  <input type="password" name="password" placeholder="Password" class="border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500" required>
  <button type="submit" class="bg-green-500 text-white rounded px-4 py-2 hover:bg-green-600 transition">Sign Up</button>
  {% if error %}
    <p class="text-red-500 text-center">{{ error }}</p>
  {% endif %}
</form>
<div class="text-center mt-4">
  <a href="/login" class="text-blue-500 hover:underline">Login</a>
</div>
</div>
</main>

</body>
</html>
"""

MY_RESUMES_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>My Resumes</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 flex flex-col min-h-screen">

""" + HEADER_HTML + """

<main class="flex-grow flex flex-col items-center px-4 py-10">
<div class="bg-white shadow-lg rounded-lg p-8 max-w-lg w-full">
<h2 class="text-xl font-semibold text-gray-700 mb-6 text-center">My Resumes</h2>
<ul class="flex flex-col gap-2">
{% for resume in resumes %}
    <li class="flex justify-between items-center border-b border-gray-200 py-2">
        <span>{{ resume.filename }}</span>
        <a href="/view/{{ resume.id }}" target="_blank" class="text-blue-500 hover:underline">View</a>
    </li>
{% endfor %}
</ul>
</div>
</main>

</body>
</html>
"""

# ----------------------
# Flask 라우트
# ----------------------
@app.route("/")
def index():
    return render_template_string(MAIN_PAGE_HTML)

@app.route("/signup", methods=["GET","POST"])
def signup():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        pw_hash = generate_password_hash(password)
        try:
            conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, pw_hash))
            conn.commit()
            flash("회원가입 완료! 로그인하세요.")
            return redirect(url_for("login"))
        except mysql.connector.IntegrityError:
            error = "이미 존재하는 아이디입니다."
        finally:
            cursor.close()
            conn.close()
    return render_template_string(SIGNUP_PAGE_HTML, error=error)

@app.route("/login", methods=["GET","POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, password_hash FROM users WHERE username=%s", (username,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row and check_password_hash(row[1], password):
            session.permanent = True  # 세션 만료 설정
            session['user'] = username
            session['user_id'] = row[0]
            return redirect(url_for("index"))
        else:
            error = "아이디 또는 비밀번호가 올바르지 않습니다."
    return render_template_string(LOGIN_PAGE_HTML, error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/upload", methods=["POST"])
def upload():
    if 'user_id' not in session:
        return jsonify({"message": "로그인이 필요합니다."}), 401

    file = request.files.get("file")
    if not file:
        return jsonify({"message": "파일을 선택하세요."}), 400

    if not file.filename.lower().endswith((".pdf", ".docx", ".hwp")):
        return jsonify({"message": "허용되지 않은 파일 형식입니다."}), 400

    filename = file.filename
    filedata = file.read()

    conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO uploads (user_id, filename, filedata) VALUES (%s, %s, %s)",
        (session['user_id'], filename, filedata)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"message": f"{filename} 업로드 완료!"})

@app.route("/my-resumes")
def my_resumes():
    if 'user_id' not in session:
        return redirect(url_for("login"))

    conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, filename FROM uploads WHERE user_id=%s ORDER BY uploaded_at DESC", (session['user_id'],))
    resumes = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template_string(MY_RESUMES_HTML, resumes=resumes)

@app.route("/view/<int:file_id>")
def view_file(file_id):
    if 'user_id' not in session:
        return redirect(url_for("login"))

    conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT filename, filedata FROM uploads WHERE id=%s AND user_id=%s", (file_id, session['user_id']))
    file_row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not file_row:
        return "파일을 찾을 수 없습니다.", 404

    filename = file_row['filename']
    data = io.BytesIO(file_row['filedata'])
    ext = filename.split('.')[-1].lower()

    if ext == "pdf":
        # 브라우저에서 바로 보기
        return send_file(data, download_name=filename, as_attachment=False, mimetype="application/pdf")
    else:
        # DOCX/HWP 등은 다운로드
        return send_file(data, download_name=filename, as_attachment=True)

# ----------------------
# 앱 실행
# ----------------------
if __name__ == "__main__":
    init_db()  # DB 및 테이블 초기화
    app.run(debug=True)

