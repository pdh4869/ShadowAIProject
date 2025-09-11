from flask import Blueprint, render_template, request, session, redirect, url_for, send_file, jsonify
import mysql.connector
import io
from db import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST

upload_bp = Blueprint("upload", __name__, template_folder="templates")

@upload_bp.route("/")
def index():
    return render_template("index.html")

@upload_bp.route("/upload", methods=["POST"])
def upload_file():
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

@upload_bp.route("/my-resumes")
def my_resumes():
    if 'user_id' not in session:
        return redirect(url_for("auth.login"))
    conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, filename FROM uploads WHERE user_id=%s ORDER BY uploaded_at DESC", (session['user_id'],))
    resumes = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("my_resumes.html", resumes=resumes)

@upload_bp.route("/view/<int:file_id>")
def view_file(file_id):
    if 'user_id' not in session:
        return redirect(url_for("auth.login"))
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
