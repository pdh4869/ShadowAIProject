from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os
import io
from datetime import timedelta

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
# Flask 라우트
# ----------------------
@app.route("/")
def index():
    return render_template("index.html")

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
    return render_template("signup.html", error=error)

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
            session.permanent = True
            session['user'] = username
            session['user_id'] = row[0]
            return redirect(url_for("index"))
        else:
            error = "아이디 또는 비밀번호가 올바르지 않습니다."
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/upload", methods=["POST"])
def upload():
    if 'user_id' not in session:
        return {"message": "로그인이 필요합니다."}, 401

    file = request.files.get("file")
    if not file:
        return {"message": "파일을 선택하세요."}, 400

    if not file.filename.lower().endswith((".pdf", ".docx", ".hwp")):
        return {"message": "허용되지 않은 파일 형식입니다."}, 400

    filename = file.filename
    filedata = file.read()

    conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO uploads (user_id, filename, filedata) VALUES (%s, %s, %s)",
                   (session['user_id'], filename, filedata))
    conn.commit()
    cursor.close()
    conn.close()

    return {"message": f"{filename} 업로드 완료!"}

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
    return render_template("my_resumes.html", resumes=resumes)

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
        return send_file(data, download_name=filename, as_attachment=False, mimetype="application/pdf")
    else:
        return send_file(data, download_name=filename, as_attachment=True)

# ----------------------
# 앱 실행
# ----------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
