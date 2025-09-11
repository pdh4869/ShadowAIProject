import mysql.connector
from flask import Flask, request, redirect, render_template_string, flash, send_file
from io import BytesIO

app = Flask(__name__)
app.secret_key = "supersecretkey"

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'hwp'}

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'mysql',
    'database': 'shadowai'
}

# 테이블 자동 생성
def create_table_if_not_exists():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id INT AUTO_INCREMENT PRIMARY KEY,
            filename VARCHAR(255) NOT NULL,
            filedata LONGBLOB NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

create_table_if_not_exists()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        if "file" not in request.files:
            flash("파일이 없습니다.")
            return redirect(request.url)

        file = request.files["file"]

        if file.filename == "":
            flash("선택된 파일이 없습니다.")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filedata = file.read()
            filename = file.filename

            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO uploads (filename, filedata) VALUES (%s, %s)",
                (filename, filedata)
            )
            conn.commit()
            cursor.close()
            conn.close()

            flash("파일 업로드 성공!")
            return redirect(request.url)
        else:
            flash("허용되지 않은 파일 형식입니다. (pdf, docx, hwp만 가능)")
            return redirect(request.url)

    # 업로드 폼 + DB에 저장된 파일 리스트 조회
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, uploaded_at FROM uploads ORDER BY uploaded_at DESC")
    files = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template_string("""
    <!doctype html>
    <title>이력서 업로드</title>
    <h1>이력서 업로드 (pdf, docx, hwp만 가능)</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    <p>{{ get_flashed_messages() }}</p>

    <h2>업로드된 파일</h2>
    <ul>
    {% for f in files %}
      <li>{{ f[1] }} ({{ f[2] }}) - <a href="{{ url_for('download_file', file_id=f[0]) }}">다운로드</a></li>
    {% endfor %}
    </ul>
    """, files=files)

@app.route("/download/<int:file_id>")
def download_file(file_id):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT filename, filedata FROM uploads WHERE id=%s", (file_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if result:
        filename, filedata = result
        return send_file(
            BytesIO(filedata),
            as_attachment=True,
            download_name=filename
        )
    else:
        flash("파일을 찾을 수 없습니다.")
        return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
