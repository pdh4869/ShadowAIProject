from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import jwt
import datetime
from functools import wraps

app = Flask(__name__)
app.json.ensure_ascii = False
app.config['SECRET_KEY'] = 'q!w@e#123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:mysql@localhost/shadowai'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

CORS(app, resources={r"/api/*": {"origins": "chrome-extension://idcmhaehnimjicifehecnfffiifcnjnn"}})

# --- (핵심 변경) 데이터베이스 모델(테이블) 정의 ---
class User(db.Model):
    # 1. 자동 증가하는 숫자 id를 기본 키(Primary Key)로 추가
    id = db.Column(db.Integer, primary_key=True) 
    
    # 2. employee_id는 기본 키가 아닌, 고유한 값으로만 설정
    employee_id = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

# --- 이하 API 관련 코드는 이전과 동일 (변경 없음) ---
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    employee_id = data.get('employee_id')
    password = data.get('password')
    user = User.query.filter_by(employee_id=employee_id).first()

    if user and user.password == password:
        token = jwt.encode({
            'sub': user.employee_id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }, app.config['SECRET_KEY'], algorithm="HS256")
        return jsonify({'token': token})
    return jsonify({'message': 'Wrong id or password'}), 401

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        if not token:
            return jsonify({'message': 'No Token!'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.filter_by(employee_id=data['sub']).first()
            if not current_user:
                 return jsonify({'message': 'Invalid User'}), 401
        except Exception as e:
            return jsonify({'message': 'Invalid Token!', 'error': str(e)}), 401
        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/api/profile')
@token_required
def get_profile(current_user):
    return jsonify({
        'message': f'Welcome, {current_user.username}님!',
        'data': f'id: {current_user.employee_id}'
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001)