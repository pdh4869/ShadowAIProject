# server.py (수정된 최종본)

import datetime
import json
import jwt
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

app = Flask(__name__)
app.json.ensure_ascii = False
app.config['SECRET_KEY'] = 'q!w@e#123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:mysql@localhost/shadowai'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
CORS(app, resources={r"/api/*": {"origins": "chrome-extension://idcmhaehnimjicifehecnfffiifcnjnn"}})

class DashboardAdmin(UserMixin, db.Model):
    __tablename__ = 'dashboard_admin'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    privilege = db.Column(db.String(50), nullable=False, default='general')
    
    # --- ▼▼▼ (핵심 추가) 새로운 컬럼들 ▼▼▼ ---
    name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    last_login = db.Column(db.DateTime, nullable=True)
    # --- ▲▲▲ ---

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
# --- 데이터베이스 모델 정의 ---
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(80), unique=True, nullable=False)

pii_log_pii_type_links = db.Table('pii_log_pii_type_links',
    db.Column('pii_log_id', db.Integer, db.ForeignKey('pii_log.id'), primary_key=True),
    db.Column('pii_type_id', db.Integer, db.ForeignKey('pii_type.id'), primary_key=True)
)

class PiiLog(db.Model):
    __tablename__ = 'pii_log'
    id = db.Column(db.Integer, primary_key=True)
    process_type = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    employee_id = db.Column(db.String(80), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=True)
    file_type_id = db.Column(db.Integer, db.ForeignKey('file_type.id'), nullable=False)
    
    # --- ▼▼▼ 두 개의 컬럼 추가 ▼▼▼ ---
    status = db.Column(db.String(20), nullable=False, default='성공') # 상태 (예: 성공, 실패)
    reason = db.Column(db.String(255), nullable=True) # 실패 사유
    # --- ▲▲▲ ---
    
    # --- 👇 (핵심 수정 1) FileType과의 관계를 명시적으로 추가 ---
    file_type = db.relationship('FileType', backref='pii_logs')
    
    pii_types = db.relationship('PiiType', secondary=pii_log_pii_type_links, backref='pii_logs', lazy=True)

class FileType(db.Model):
    __tablename__ = 'file_type'
    id = db.Column(db.Integer, primary_key=True)
    type_name = db.Column(db.String(50), unique=True, nullable=False)

class PiiType(db.Model):
    __tablename__ = 'pii_type'
    id = db.Column(db.Integer, primary_key=True)
    type_name = db.Column(db.String(50), unique=True, nullable=False)

# --- API 엔드포인트 정의 ---
@app.route('/api/log-pii', methods=['POST'])
def log_pii():
    data = request.get_json()
    if not data or 'employee_id' not in data:
        return jsonify({'status': 'error', 'message': 'employee_id가 누락되었습니다.'}), 400
    try:
        file_type_name = data.get('file_type_name')
        if not file_type_name:
            return jsonify({'status': 'error', 'message': 'file_type_name이 누락되었습니다.'}), 400
        
        file_type_obj = FileType.query.filter_by(type_name=file_type_name).first()
        if not file_type_obj:
            file_type_obj = FileType(type_name=file_type_name)
            db.session.add(file_type_obj)
        
        # --- 👇 (핵심 수정 2) id 대신 객체 자체를 할당 ---
        new_pii_log = PiiLog(
            employee_id=data.get('employee_id'),
            process_type=data.get('process_type'),
            filename=data.get('filename'),
            file_type=file_type_obj  # id 대신 file_type_obj 객체를 직접 연결
        )
        
        pii_type_names = data.get('pii_types', [])
        for type_name in pii_type_names:
            pii_type_obj = PiiType.query.filter_by(type_name=type_name).first()
            if not pii_type_obj:
                pii_type_obj = PiiType(type_name=type_name)
                db.session.add(pii_type_obj)
            new_pii_log.pii_types.append(pii_type_obj)
            
        db.session.add(new_pii_log)
        db.session.commit()
        
        print(f"✅ [PII 로그 저장 성공] Employee ID: {data.get('employee_id')}의 PII 로그가 저장되었습니다.")
        return jsonify({'status': 'success', 'message': 'PII 로그가 성공적으로 저장되었습니다.'})
    except Exception as e:
        db.session.rollback()
        print(f"❌ [PII 로그 저장 오류] {e}")
        return jsonify({'status': 'error', 'message': f'PII 로그 저장 중 오류 발생: {e}'}), 500

# --- (이하 인증 관련 API 및 서버 실행 코드는 동일) ---
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    employee_id = data.get('employee_id')
    user = User.query.filter_by(employee_id=employee_id).first()
    if user:
        token = jwt.encode({'sub': user.employee_id, 'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)}, app.config['SECRET_KEY'], algorithm="HS256")
        return jsonify({'token': token})
    return jsonify({'message': '존재하지 않는 사번입니다.'}), 401

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers: token = request.headers['Authorization'].split(" ")[1]
        if not token: return jsonify({'message': '토큰이 없습니다!'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.filter_by(employee_id=data['sub']).first()
            if not current_user: return jsonify({'message': '유효하지 않은 사용자입니다.'}), 401
        except: return jsonify({'message': '토큰이 유효하지 않습니다!'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/api/profile')
@token_required
def get_profile(current_user):
    return jsonify({'employee_id': current_user.employee_id})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("All tables created successfully.")
    app.run(debug=True, port=5001)