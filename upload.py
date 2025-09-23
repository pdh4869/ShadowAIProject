import os
from openai import OpenAI
import docx
from pypdf import PdfReader
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

# --- 앱 및 데이터베이스 설정 ---
app = Flask(__name__)
# 세션 관리를 위한 시크릿 키, 실제 운영 환경에서는 강력한 키로 변경해야 합니다.
app.config['SECRET_KEY'] = 'your-very-secret-key-for-shadowai'
DB_NAME = "shadowai"

# --- 데이터베이스 초기화 함수 ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # 사용자 테이블 생성 (username은 고유해야 함)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# --- Flask-Login 설정 ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # 로그인하지 않은 사용자가 접근 시 리디렉션할 페이지

# --- 사용자 모델 정의 (UserMixin 사용) ---
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    """사용자 ID를 기반으로 사용자 객체를 로드하는 함수"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    if user_data:
        return User(id=user_data[0], username=user_data[1], password=user_data[2])
    return None

# --- OpenAI API 설정 ---
try:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
    client = OpenAI(api_key=api_key)
except Exception as e:
    print(f"OpenAI API 설정 중 오류 발생: {e}")

# --- 파일 처리 함수 ---
ALLOWED_EXTENSIONS = {'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(file):
    ext = file.filename.rsplit('.', 1)[1].lower()
    text = ""
    file.seek(0)
    try:
        if ext == "pdf":
            reader = PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() or ""
        elif ext == "docx":
            doc = docx.Document(file)
            for para in doc.paragraphs:
                text += para.text + "\n"
    except Exception as e:
        return f"파일 읽기 오류: {e}"
    return text

# --- 라우팅 ---
@app.route('/')
@login_required
def form():
    """파일 업로드 폼을 렌더링 (로그인된 사용자만 접근 가능)"""
    return render_template('upload.html', username=current_user.username)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """로그인 페이지 렌더링 및 로그인 처리"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user WHERE username = ?", (username,))
        user_data = cursor.fetchone()
        conn.close()

        if user_data and check_password_hash(user_data[2], password):
            user = User(id=user_data[0], username=user_data[1], password=user_data[2])
            login_user(user)
            return redirect(url_for('form'))
        else:
            flash("사용자 이름 또는 비밀번호가 올바르지 않습니다.")
            
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """회원가입 페이지 렌더링 및 사용자 등록 처리"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO user (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            conn.close()
            flash("회원가입이 완료되었습니다. 로그인해주세요.")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("이미 존재하는 사용자 이름입니다.")
        
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    """로그아웃 처리"""
    logout_user()
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    """파일을 받아 텍스트를 추출하고 ChatGPT로 분석 요청"""
    if 'file' not in request.files:
        return jsonify({"error": "요청에 파일이 없습니다."}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "파일이 선택되지 않았습니다."}), 400
        
    if file and allowed_file(file.filename):
        text = extract_text_from_file(file)
        if not text.strip():
            return jsonify({"error": "파일에서 텍스트를 추출할 수 없습니다."}), 400
        
        try:
            prompt = f"다음 문서를 분석하고 핵심 내용을 3줄로 요약해주세요:\n\n{text}"
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            return jsonify({
                "filename": file.filename,
                "analysis": response.choices[0].message.content
            })
        except Exception as e:
            return jsonify({"error": f"OpenAI API 호출 오류: {e}"}), 500
            
    return jsonify({"error": "허용되지 않는 파일 형식입니다. (pdf, docx만 가능)"}), 400

if __name__ == "__main__":
    init_db()  # 앱 실행 시 데이터베이스 초기화
    app.run(host='0.0.0.0', port=5000, debug=True)