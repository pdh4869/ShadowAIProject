from zoneinfo import ZoneInfo
from collections import Counter
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta, timezone
import traceback
import json
import re

# 1. Flask 앱 초기화 및 설정
app = Flask(__name__,
             template_folder='templates',
             static_folder='templates/assets',
             static_url_path='/assets'
)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shadowai.db'
app.config['SECRET_KEY'] = 'your-very-secret-key-for-dashboard'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.json.ensure_ascii = False
CORS(app)

db = SQLAlchemy(app)

# 2. Flask-Login 설정
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'dashboard_login_page'

# ⭐ Jinja 필터 'rjust' 추가 정의
def rjust_filter(s, width, fillchar=' '):
    """문자열을 오른쪽 정렬하고 남은 공간을 fillchar로 채우는 Jinja 필터"""
    return str(s).rjust(width, fillchar)

app.jinja_env.filters['rjust'] = rjust_filter

def to_local_string_filter(value):
     if value is None: return ''
     return f"{int(value):,}" if isinstance(value, (int, float)) else str(value)

app.jinja_env.filters['toLocaleString'] = to_local_string_filter

# UTC 시간을 KST 시간으로 변환하는 함수
def format_datetime_kst(dt_utc):
    """
    UTC datetime 객체를 KST로 변환하고 지정된 포맷으로 반환합니다.
    """
    if dt_utc is None or not isinstance(dt_utc, datetime):
        return '-'
    
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    
    dt_kst = dt_utc.astimezone(ZoneInfo('Asia/Seoul'))
    return dt_kst.strftime('%Y-%m-%d %H:%M:%S')

# User Agent를 짧은 브라우저 이름으로 변환하는 함수
def parse_browser_name(user_agent):
    if not user_agent:
        return '-'
    ua = user_agent.lower()
    if 'chrome' in ua and 'edg' not in ua:
        return 'Chrome'
    elif 'edg' in ua:
        return 'Edge'
    elif 'firefox' in ua:
        return 'Firefox'
    elif 'safari' in ua and 'chrome' not in ua:
        return 'Safari'
    elif 'opera' in ua:
        return 'Opera'
    else:
        return 'Unknown'

app.jinja_env.filters['kst'] = format_datetime_kst

# 💡 Jinja에서 현재 KST 시간을 사용할 수 있도록 등록
@app.context_processor
def inject_now():
    korea_tz = ZoneInfo("Asia/Seoul")
    return {'now': lambda: datetime.now(korea_tz)}

# =====================================================================
# 데이터베이스 모델 전체 정의
# =====================================================================

# LLM 유형 관리 테이블
class LlmType(db.Model):
    __tablename__ = 'llm_type'
    id = db.Column(db.Integer, primary_key=True)
    type_name = db.Column(db.String(50), unique=True, nullable=False)

# 대시보드 관리자 계정 테이블
class DashboardAdmin(UserMixin, db.Model):
    __tablename__ = 'dashboard_admin'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    privilege = db.Column(db.String(50), nullable=False, default='general')
    name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 대시보드 관리자 활동 로그 테이블
class DashboardLog(db.Model):
    __tablename__ = 'dashboard_log'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    admin_id = db.Column(db.Integer, db.ForeignKey('dashboard_admin.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    admin = db.relationship('DashboardAdmin', backref='dashboard_logs')

# PiiLog와 PiiType의 다대다 관계를 위한 연결 테이블
pii_log_pii_type_links = db.Table('pii_log_pii_type_links',
    db.Column('pii_log_id', db.Integer, db.ForeignKey('pii_log.id'), primary_key=True),
    db.Column('pii_type_id', db.Integer, db.ForeignKey('pii_type.id'), primary_key=True)
)

# 개인정보 탐지 로그 테이블
class PiiLog(db.Model):
    __tablename__ = 'pii_log'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    filename = db.Column(db.String(255), nullable=True)
    file_type_id = db.Column(db.Integer, db.ForeignKey('file_type.id'), nullable=False)
    llm_type_id = db.Column(db.Integer, db.ForeignKey('llm_type.id'), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='성공')
    reason = db.Column(db.String(512), nullable=True)
    session_url = db.Column(db.String(2048), nullable=True)
    user_agent = db.Column(db.String(512), nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    os_info = db.Column(db.String(128), nullable=True)
    hostname = db.Column(db.String(255), nullable=True) 
    validation_results = db.Column(db.JSON, nullable=True)
    pii_type_counts = db.Column(db.JSON, nullable=True) 

    file_type = db.relationship('FileType', backref='pii_logs')
    llm_type = db.relationship('LlmType', backref='pii_logs')
    pii_types = db.relationship('PiiType', secondary=pii_log_pii_type_links, backref='pii_logs', lazy='subquery')

# 파일/소스 유형 테이블
class FileType(db.Model):
    __tablename__ = 'file_type'
    id = db.Column(db.Integer, primary_key=True)
    type_name = db.Column(db.String(50), unique=True, nullable=False)

# 개인정보 유형 테이블
class PiiType(db.Model):
    __tablename__ = 'pii_type'
    id = db.Column(db.Integer, primary_key=True)
    type_name = db.Column(db.String(50), unique=True, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return DashboardAdmin.query.get(int(user_id))

# =====================================================================
# API 엔드포인트: PII 로그 수신 (클라이언트용) - 새로운 로직
# =====================================================================

def _get_or_create_generic(model, session, **kwargs):
    """
    단순한 get-or-create 헬퍼.
    1) 먼저 조회
    2) 없으면 추가 후 flush
    3) flush에서 IntegrityError가 나오면 rollback 후 다시 조회
    """
    instance = model.query.filter_by(**kwargs).first()
    if instance:
        return instance
    instance = model(**kwargs)
    session.add(instance)
    try:
        session.flush()
        return instance
    except IntegrityError:
        # 다른 세션이 같은 이름을 삽입했을 수 있음: 롤백하고 재조회
        session.rollback()
        instance = model.query.filter_by(**kwargs).first()
        return instance

@app.route('/api/log-pii', methods=['POST'])
def log_pii():
    data = request.get_json()
    required_fields = ['file_type_name', 'ip_address']

    if not all(field in data for field in required_fields):
        return jsonify({'status': 'error', 'message': f'필수 필드({", ".join(required_fields)})가 누락되었습니다.'}), 400

    try:
        # --- FileType 처리 로직 (기존 방식 유지, try/except flush 포함) ---
        file_type_name = data.get('file_type_name')
        file_type_obj = FileType.query.filter_by(type_name=file_type_name).first()
        if not file_type_obj:
            try:
                file_type_obj = FileType(type_name=file_type_name)
                db.session.add(file_type_obj)
                db.session.flush()
            except IntegrityError:
                db.session.rollback()
                file_type_obj = FileType.query.filter_by(type_name=file_type_name).first()

        # --- LlmType 처리 로직 (기존 방식 유지) ---
        llm_type_obj = None
        llm_type_name = data.get('llm_type_name')
        if llm_type_name:
            llm_type_obj = LlmType.query.filter_by(type_name=llm_type_name).first()
            if not llm_type_obj:
                try:
                    llm_type_obj = LlmType(type_name=llm_type_name)
                    db.session.add(llm_type_obj)
                    db.session.flush()
                except IntegrityError:
                    db.session.rollback()
                    llm_type_obj = LlmType.query.filter_by(type_name=llm_type_name).first()

        # 3. PiiType 처리 - combination_risk에서 LC 추출
        raw_pii_type_list = data.get('pii_types', []) or []
        
        # combination_risk.items에서 LC 타입 추출
        combination_risk = data.get('combination_risk', {})
        if combination_risk and 'items' in combination_risk:
            for item in combination_risk['items']:
                if item.get('type') == 'LC':
                    raw_pii_type_list.append('lc')
                    break
        
        pii_type_names = list(dict.fromkeys([name for name in raw_pii_type_list if isinstance(name, str) and name]))

        final_pii_objects = []
        if pii_type_names:
            for type_name in pii_type_names:
                pii_type_obj = PiiType.query.filter_by(type_name=type_name).first()
                if not pii_type_obj:
                    try:
                        pii_type_obj = PiiType(type_name=type_name)
                        db.session.add(pii_type_obj)
                        db.session.flush()
                    except IntegrityError:
                        db.session.rollback()
                        pii_type_obj = PiiType.query.filter_by(type_name=type_name).first()
                if pii_type_obj:
                    final_pii_objects.append(pii_type_obj)

        # 4. pii_type_counts 키 변환 및 combination_risk에서 LC 개수 추출
        pii_type_counts = data.get('pii_type_counts') or {}
        converted_counts = {}
        
        for key, value in pii_type_counts.items():
            # LC, LOC를 lc로 변환
            if key.upper() in ['LC', 'LOC']:
                converted_counts['lc'] = converted_counts.get('lc', 0) + value
            else:
                converted_counts[key] = value
        
        # combination_risk.items에서 LC 개수 세기
        combination_risk = data.get('combination_risk', {})
        if combination_risk and 'items' in combination_risk:
            lc_count = sum(1 for item in combination_risk['items'] if item.get('type') == 'LC')
            if lc_count > 0:
                converted_counts['lc'] = converted_counts.get('lc', 0) + lc_count
        
        pii_type_counts = converted_counts if converted_counts else None
        
        # 5. PiiLog 생성 - pii_types 없이 먼저 생성
        new_pii_log = PiiLog(
            filename=data.get('filename'),
            file_type=file_type_obj,
            llm_type=llm_type_obj,
            status='성공' if data.get('status') == 'success' else ('실패' if data.get('status') == 'failure' else data.get('status', '성공')),
            reason=data.get('reason'),
            ip_address=data.get('ip_address'),
            session_url=data.get('session_url'),
            user_agent=data.get('user_agent'),
            os_info=data.get('os_info'),
            hostname=data.get('hostname'),
            validation_results=data.get('validation_statuses'),
            pii_type_counts=pii_type_counts
        )
        
        db.session.add(new_pii_log)
        db.session.flush()
        
        # 6. 관계 설정 - 직접 SQL로 안전하게 삽입
        if final_pii_objects:
            for pii_obj in final_pii_objects:
                try:
                    db.session.execute(
                        pii_log_pii_type_links.insert().values(
                            pii_log_id=new_pii_log.id,
                            pii_type_id=pii_obj.id
                        )
                    )
                except IntegrityError:
                    pass  # 이미 존재하면 무시
        
        db.session.commit()

        success_msg = f"[PII 로그 저장 성공] PII 로그가 저장되었습니다. IP: {data.get('ip_address')}"
        print(success_msg.encode('utf-8', errors='replace').decode('utf-8'))
        return jsonify({'status': 'success', 'message': 'PII 로그가 성공적으로 저장되었습니다.'})

    except IntegrityError as e:
        db.session.rollback()
        error_msg = f"[PII 로그 저장 오류] IntegrityError: {str(e)}"
        print(error_msg.encode('utf-8', errors='replace').decode('utf-8'))
        return jsonify({'status': 'error', 'message': 'PII 로그 저장 중 중복 오류 발생'}), 500
    except Exception as e:
        db.session.rollback()
        error_msg = f"[PII 로그 저장 오류] {type(e).__name__}: {str(e)}"
        print(error_msg.encode('utf-8', errors='replace').decode('utf-8'))
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'PII 로그 저장 중 오류 발생: {type(e).__name__}'}), 500

# =====================================================================
# 대시보드 로그인/로그아웃 및 관리자 기능
# =====================================================================

def log_dashboard_action(action_type):
    """대시보드 관리자 행동을 기록하는 헬퍼 함수"""
    if not current_user.is_authenticated: return
    new_log = DashboardLog(admin_id=current_user.id, action=action_type)
    db.session.add(new_log)
    db.session.commit()

@app.route('/login')
def dashboard_login_page():
    return render_template('login.html')

@app.route('/api/dashboard_login', methods=['POST'])
def dashboard_login_api():
    data = request.get_json()
    employee_id = data.get('employee_id')
    password = data.get('password')
    user = DashboardAdmin.query.filter_by(employee_id=employee_id).first()
    if user and user.check_password(password):
        login_user(user)
        user.last_login = datetime.now(timezone.utc)
        db.session.commit()
        log_dashboard_action('login')
        return jsonify({'status': 'success', 'message': '로그인 성공'})
    return jsonify({'status': 'error', 'message': 'ID 또는 비밀번호가 잘못되었습니다.'}), 401

@app.route('/logout')
@login_required
def dashboard_logout():
    log_dashboard_action('logout')
    logout_user()
    return redirect(url_for('dashboard_login_page'))

@app.route('/admin_manage')
@login_required
def admin_manage():
    if current_user.privilege != 'super':
        abort(403)

    def sort_admins(admin):
        privilege_order = 0 if admin.privilege == 'super' else 1
        return (privilege_order, admin.employee_id)

    users_from_db = DashboardAdmin.query.all()
    sorted_users = sorted(users_from_db, key=sort_admins)
    
    users_for_template = [
        {
            "employee_id": u.employee_id if u.employee_id else '-',
            "name": u.name if u.name else '-',
            "email": u.email if u.email else '-',
            "privilege": u.privilege if u.privilege else 'general',
            "last_login": u.last_login,
            "created_at": u.created_at
        }
        for u in sorted_users
    ]
    
    return render_template('account_management.html', 
        users=users_for_template, 
        active_page='admin_manage'
    )

@app.route('/api/admin/create', methods=['POST'])
@login_required
def api_admin_create():
    if current_user.privilege != 'super': abort(403)
    data = request.get_json()
    if DashboardAdmin.query.filter_by(employee_id=data['emp']).first():
        return jsonify({'status': 'error', 'message': '이미 존재하는 사번입니다.'}), 400
    if DashboardAdmin.query.filter_by(email=data['email']).first():
        return jsonify({'status': 'error', 'message': '이미 존재하는 이메일입니다.'}), 400

    new_user = DashboardAdmin(
        employee_id=data['emp'],
        name=data['name'],
        email=data['email'],
        privilege='admin'
    )
    new_user.set_password(data['pwd'])
    db.session.add(new_user)
    db.session.commit()

    log_dashboard_action(f"create_admin:{data['emp']}")
    return jsonify({'status': 'success', 'message': '새 관리자 계정이 생성되었습니다.'})

@app.route('/api/admin/change_password', methods=['POST'])
@login_required
def api_admin_change_password():
    if current_user.privilege != 'super': abort(403)
    data = request.get_json()
    user_to_edit = DashboardAdmin.query.filter_by(employee_id=data['emp']).first_or_404()
    user_to_edit.set_password(data['pwd'])
    db.session.commit()

    log_dashboard_action(f"change_password:{data['emp']}")
    return jsonify({'status': 'success', 'message': '비밀번호가 변경되었습니다.'})

@app.route('/api/admin/delete', methods=['POST'])
@login_required
def api_admin_delete():
    if current_user.privilege != 'super': abort(403)
    data = request.get_json()
    user_to_delete = DashboardAdmin.query.filter_by(employee_id=data['emp']).first_or_404()
    if user_to_delete.privilege == 'super':
        return jsonify({'status': 'error', 'message': '최고 관리자 계정은 삭제할 수 없습니다.'}), 403
    if user_to_delete.id == current_user.id:
        return jsonify({'status': 'error', 'message': '자기 자신을 삭제할 수 없습니다.'}), 403
    db.session.delete(user_to_delete)
    db.session.commit()

    log_dashboard_action(f"delete_admin:{user_to_delete.employee_id}")
    return jsonify({'status': 'success', 'message': '계정이 삭제되었습니다.'})


# =====================================================================
# 대시보드 페이지 렌더링
# =====================================================================
@app.route('/test_input')
@login_required
def test_input_page():
    """PII 탐지 테스트 페이지"""
    return render_template('test_input.html', active_page='test_input')

@app.route('/')
@app.route('/main')
@login_required
def show_dashboard():
    """메인 대시보드 페이지를 위한 데이터를 조회하고 렌더링"""
    
    kpi_data = {'total_num': 0, 'total_delta': 0, 'high_risk_num': 0, 'high_risk_delta': 0, 'valid_num': 0, 'valid_delta': 0}
    today_stats = {'total': 0, 'types': []}
    top_users = []
    source_stats = []
    llm_stats = []
    recent_failures = []
    recent_suspicious = [] 
    
    try:
        # 1. 시간대 설정 (UTC 기준)
        now_utc = datetime.now(timezone.utc)
        seven_days_ago = (now_utc - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        fourteen_days_ago = (now_utc - timedelta(days=14)).replace(hour=0, minute=0, second=0, microsecond=0)
        # kst_timestamp = func.convert_tz(PiiLog.timestamp, 'UTC', 'Asia/Seoul')  # SQLite에서는 불필요

        # 2. 일별 탐지 추이 (TREND_DATA)
        trend_raw_query = db.session.query(
            PiiLog.timestamp,
            PiiLog.status,
            PiiType.type_name.label('pii_type')
        ).select_from(PiiLog).outerjoin(pii_log_pii_type_links).outerjoin(PiiType).filter(PiiLog.timestamp >= fourteen_days_ago).all()

        # ⭐ 수정: ip, name, ps, person, combination_risk 추가
        high_risk_types_names = ['ssn', 'card', 'account', 'alien_registration', 'passport', 'driver_license' ]
        trend_data_map = {}
        
        korea_tz = ZoneInfo('Asia/Seoul')
        for i in range(7):
            date = datetime.now(korea_tz).date() - timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            trend_data_map[date_str] = {'date': date_str, 'total': 0, 'highRisk': 0, 'failed': 0, 'success': 0}
        
        for timestamp, status, pii_type in trend_raw_query:
            if timestamp is None: continue
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            kst_time = timestamp.astimezone(korea_tz)
            date_str = kst_time.strftime('%Y-%m-%d')
            
            if date_str not in trend_data_map: continue

            trend_data_map[date_str]['total'] += 1
            if status == '실패':
                trend_data_map[date_str]['failed'] += 1
            elif status == '성공':
                trend_data_map[date_str]['success'] += 1
                if pii_type in high_risk_types_names: 
                    trend_data_map[date_str]['highRisk'] += 1

        TREND_DATA_FINAL = sorted(trend_data_map.values(), key=lambda x: x['date'], reverse=False)[-7:]

        # 3. KPI 데이터 (kpi_data)
        total_num = db.session.query(func.count(PiiLog.id)).filter(PiiLog.timestamp >= seven_days_ago).scalar() or 0
        last_period_total = db.session.query(func.count(PiiLog.id)).filter(
            PiiLog.timestamp < seven_days_ago, PiiLog.timestamp >= fourteen_days_ago
        ).scalar() or 0
        if last_period_total == 0:
            total_delta = 100 if total_num > 0 else 0
        else:
            total_delta = min(max(((total_num - last_period_total) / last_period_total) * 100, -100), 100)
        
        high_risk_types = PiiType.query.filter(PiiType.type_name.in_(high_risk_types_names)).all()
        high_risk_ids = [t.id for t in high_risk_types]
        
        # ⭐ 디버깅 로그 추가
        print(f"=== DEBUG: high_risk_types_names = {high_risk_types_names}")
        print(f"=== DEBUG: high_risk_ids = {high_risk_ids}")
        
        # 실제 DB에 있는 PII 타입들 확인
        all_pii_in_db = PiiType.query.all()
        print(f"=== DEBUG: All PII types in DB = {[p.type_name for p in all_pii_in_db]}")
        
        # pii_type_counts를 고려한 고위험 PII 개수 계산
        high_risk_count_current = 0
        total_pii_count_current = 0
        high_risk_count_last = 0
        total_pii_count_last = 0
        
        # 현재 기간 (최근 7일)
        current_logs = db.session.query(PiiLog).filter(
            PiiLog.timestamp >= seven_days_ago, PiiLog.status == '성공'
        ).all()
        
        for log in current_logs:
            if log.pii_type_counts:
                for pii_type, count in log.pii_type_counts.items():
                    total_pii_count_current += count
                    if pii_type in high_risk_types_names:
                        high_risk_count_current += count
            else:
                # pii_types 관계에서 고위험 타입 확인
                for pii_type in log.pii_types:
                    total_pii_count_current += 1
                    if pii_type.type_name in high_risk_types_names:
                        high_risk_count_current += 1
        
        # 이전 기간 (7-14일 전)
        last_logs = db.session.query(PiiLog).filter(
            PiiLog.timestamp < seven_days_ago, PiiLog.timestamp >= fourteen_days_ago, PiiLog.status == '성공'
        ).all()
        
        for log in last_logs:
            if log.pii_type_counts:
                for pii_type, count in log.pii_type_counts.items():
                    total_pii_count_last += count
                    if pii_type in high_risk_types_names:
                        high_risk_count_last += count
            else:
                for pii_type in log.pii_types:
                    total_pii_count_last += 1
                    if pii_type.type_name in high_risk_types_names:
                        high_risk_count_last += 1
        
        high_risk_num = (high_risk_count_current / (total_pii_count_current or 1)) * 100
        high_risk_ratio_last = (high_risk_count_last / (total_pii_count_last or 1)) * 100
        if high_risk_ratio_last == 0:
            high_risk_delta = 100 if high_risk_num > 0 else 0
        else:
            high_risk_delta = min(max(((high_risk_num - high_risk_ratio_last) / high_risk_ratio_last) * 100, -100), 100)

        
        # ⭐ Luhn/체크섬 통과율 (valid_num) 계산 로직
        def calculate_validation_metrics(start_time, end_time=None):
            query = db.session.query(PiiLog.validation_results).filter(
                PiiLog.timestamp >= start_time,
                PiiLog.validation_results.isnot(None)
            )
            if end_time:
                 query = query.filter(PiiLog.timestamp < end_time)
            
            validation_logs = query.all()
            
            total_validation_attempts = 0
            successful_validations = 0
            
            for log in validation_logs:
                results = log[0]
                if results and isinstance(results, list):
                    for status in results:
                        total_validation_attempts += 1
                        if status and 'valid' in status.lower():
                            successful_validations += 1
            
            ratio = (successful_validations / total_validation_attempts) * 100 if total_validation_attempts > 0 else 0
            return ratio

        now_time = datetime.now(timezone.utc)
        valid_num = calculate_validation_metrics(seven_days_ago, now_time)
        valid_ratio_last = calculate_validation_metrics(fourteen_days_ago, seven_days_ago)

        if valid_ratio_last == 0:
            valid_delta = 100 if valid_num > 0 else 0
        else:
            valid_delta = min(max(((valid_num - valid_ratio_last) / valid_ratio_last) * 100, -100), 100)
        
        kpi_data = {
            'total_num': total_num, 'total_delta': round(total_delta, 1),
            'high_risk_num': round(high_risk_num, 3),
            'high_risk_delta': round(high_risk_delta, 1),
            'valid_num': round(valid_num, 1), 'valid_delta': round(valid_delta, 1) 
        }

        # 4. 최근 7일 탐지 유형 (today_stats) - 실시간 데이터 포함
        seven_days_ago_utc = (datetime.now(timezone.utc) - timedelta(days=7))

        today_total = db.session.query(func.count(PiiLog.id)).filter(
            PiiLog.status == '성공'
        ).scalar() or 0
        top_5_today_query = db.session.query(PiiType.type_name, func.count(PiiLog.id)).select_from(PiiLog).join(
            pii_log_pii_type_links).join(PiiType).filter(
            PiiLog.status == '성공'
        ).group_by(PiiType.type_name).order_by(func.count(PiiLog.id).desc()).limit(5).all()

        today_stats = {
            'total': today_total, 'types': [{'type': r[0], 'count': r[1]} for r in top_5_today_query]
        }
        
        # ⭐ 디버깅 로그 추가
        print(f"--- TODAY_STATS (Last 7 Days) ---")
        print(f"Total Successful: {today_total}")
        print(f"Top 5 Types: {today_stats['types']}")
        print(f"Raw query result: {top_5_today_query}")
        print("-------------------------------------------------")

        # 5. 사용자별 탐지 빈도 (top_users)
        top_users_query = db.session.query(PiiLog.ip_address, func.count(PiiLog.id)).filter(
            PiiLog.status == '성공'
        ).group_by(PiiLog.ip_address).order_by(func.count(PiiLog.id).desc()).limit(5).all()
        top_ips = [r[0] for r in top_users_query]

        high_risk_counts_map = {}
        if top_ips and high_risk_ids:
            high_risk_counts_query = db.session.query(PiiLog.ip_address, func.count(PiiLog.id)).select_from(PiiLog).join(
                pii_log_pii_type_links).filter(
                PiiLog.ip_address.in_(top_ips), pii_log_pii_type_links.c.pii_type_id.in_(high_risk_ids), PiiLog.status == '성공'
            ).group_by(PiiLog.ip_address).all()
            high_risk_counts_map = {r[0]: r[1] for r in high_risk_counts_query}
        
        top_users = []
        for ip, total_count in top_users_query:
            high_risk_count = high_risk_counts_map.get(ip, 0)
            high_risk_percent = round((high_risk_count / total_count) * 100, 0) if total_count > 0 else 0
            top_users.append({'account': ip if ip else 'Unknown IP', 'count': total_count, 'high_risk': high_risk_percent})

        # 6. 파일 확장자별 분포 (source_stats) - 전체 데이터
        source_dist_query = db.session.query(FileType.type_name, func.count(PiiLog.id)).join(
            FileType, PiiLog.file_type_id == FileType.id
        ).filter(PiiLog.status == '성공').group_by(FileType.type_name).all()
        source_stats = [{'source': r[0], 'count': r[1]} for r in source_dist_query]

        # 7. LLM 유형별 분포 (llm_stats)
        llm_dist_query = db.session.query(LlmType.type_name, func.count(PiiLog.id)).join(
            LlmType, PiiLog.llm_type_id == LlmType.id
        ).filter(PiiLog.status == '성공').group_by(LlmType.type_name).all()
        llm_stats = [{'llm': r[0], 'count': r[1]} for r in llm_dist_query]

        # 8. 최근 탐지 실패 로그 (recent_failures)
        recent_failures_query = db.session.query(PiiLog).options(db.joinedload(PiiLog.file_type)).filter(
            PiiLog.status == '실패').order_by(PiiLog.timestamp.desc()).limit(8).all() 

        recent_failures = []
        for log in recent_failures_query:
            recent_failures.append({
                'id': log.id,
                'timestamp': format_datetime_kst(log.timestamp),
                'ip_address': str(log.ip_address) if log.ip_address else '-',
                'hostname': str(log.hostname) if log.hostname else '-',
                'file_type_name': str(log.file_type.type_name) if log.file_type else '-',
                'file': str(log.filename) if log.filename else '-',
                'reason': str(log.reason) if log.reason else '-',
            })

        # 9. 개인 식별 의심 목록 (recent_suspicious)
        suspicious_ids = high_risk_ids 

        recent_suspicious_query = db.session.query(PiiLog).options(db.joinedload(PiiLog.file_type)).join(
            pii_log_pii_type_links
        ).filter(
            PiiLog.status == '성공', pii_log_pii_type_links.c.pii_type_id.in_(suspicious_ids)
        ).order_by(PiiLog.timestamp.desc()).limit(8).all()
        
        recent_suspicious = []
        for log in recent_suspicious_query:
            recent_suspicious.append({
                'id': log.id,
                'timestamp': format_datetime_kst(log.timestamp),
                'ip_address': str(log.ip_address) if log.ip_address else '-',
                'hostname': str(log.hostname) if log.hostname else '-',
                'file_type_name': str(log.file_type.type_name) if log.file_type else '-',
                'file': str(log.filename) if log.filename else '-',
                'reason': str(log.reason) if log.reason else '-',
            })
        
        # 10. KPI 델타 클래스 설정 
        kpi_data['total_delta_class'] = 'ok' if kpi_data['total_delta'] > 0 else 'bad'
        kpi_data['high_risk_delta_class'] = 'bad' if kpi_data['high_risk_delta'] > 0 else 'ok'
        kpi_data['valid_delta_class'] = 'ok' if kpi_data['valid_delta'] > 0 else 'bad'

        return render_template(
            'main.html', 
            active_page='main', 
            KPI_DATA=kpi_data, TREND_DATA=TREND_DATA_FINAL, 
            TODAY_STATS=today_stats, TOP_USERS=top_users, 
            SOURCE_STATS=source_stats, LLM_STATS=llm_stats,
            RECENT_FAILURES=recent_failures, RECENT_SUSPICIOUS=recent_suspicious,
        )
        
    except Exception as e:
        error_msg = f"[대시보드 로딩 오류] {type(e).__name__}: {str(e)}"
        print(error_msg.encode('utf-8', errors='replace').decode('utf-8'))
        traceback.print_exc()
        return render_template(
             'main.html', active_page='main', 
             KPI_DATA=kpi_data, TREND_DATA=[], TODAY_STATS={'total': 0, 'types': []}, TOP_USERS=[], 
             SOURCE_STATS=[], LLM_STATS=[], RECENT_FAILURES=[], RECENT_SUSPICIOUS=[],
        )

# =====================================================================
# 상세/현황 페이지 라우트
# =====================================================================

@app.route('/detection_details')
@login_required 
def show_detection_details():
    """탐지 현황 페이지"""
    try:
        from_date = request.args.get('from')
        to_date = request.args.get('to')
        pii_type_filter = request.args.get('type')
        source_filter = request.args.get('source')
        status_filter = request.args.get('status')
        search_query = request.args.get('q')
        
        query = PiiLog.query.options(
            db.joinedload(PiiLog.file_type),
            db.joinedload(PiiLog.llm_type),
            db.joinedload(PiiLog.pii_types)
        )
        
        if from_date: query = query.filter(PiiLog.timestamp >= from_date)
        if to_date:
            try:
                to_date_end = datetime.strptime(to_date, '%Y-%m-%d').date() + timedelta(days=1)
                query = query.filter(PiiLog.timestamp < to_date_end)
            except ValueError:
                pass
        if pii_type_filter:
            query = query.join(PiiLog.pii_types).filter(PiiType.type_name == pii_type_filter)
        if source_filter:
            query = query.join(PiiLog.file_type).filter(FileType.type_name == source_filter)
        if status_filter:
            if status_filter == '개인 식별 의심':
                query = query.filter(PiiLog.status == '성공')
            else:
                query = query.filter(PiiLog.status == status_filter)
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.filter(or_(
                PiiLog.ip_address.ilike(search_pattern),
                PiiLog.os_info.ilike(search_pattern),
                PiiLog.hostname.ilike(search_pattern),
                PiiLog.llm_type.has(LlmType.type_name.ilike(search_pattern)),
                PiiLog.filename.ilike(search_pattern),
                PiiLog.session_url.ilike(search_pattern),
                PiiLog.reason.ilike(search_pattern)
            ))

        filtered_logs = query.order_by(PiiLog.timestamp.desc()).all()
        
        file_type_counts = Counter()
        for log in filtered_logs:
            file_type_name = log.file_type.type_name if log.file_type else None
            if file_type_name:
                file_type_counts[file_type_name] += 1
        
        bar_chart_data = [
            {'type': type_name, 'count': count}
            for type_name, count in sorted(file_type_counts.items(), key=lambda x: x[1], reverse=True)
        ]
        
        formatted_logs = []
        for log in filtered_logs:
            pii_types_names = [pii.type_name for pii in log.pii_types] if log.pii_types else []
            llm_type_name_safe = log.llm_type.type_name if log.llm_type else '-'
            
            # suspicious 계산
            high_risk_types = ['ssn', 'card', 'account', 'alien_registration', 'passport', 'driver_license', 'ip', 'name', 'ps', 'person', 'alien_reg', 'email', 'phone', 'face_image']
            all_pii_types = list(log.pii_type_counts.keys()) + pii_types_names if log.pii_type_counts else pii_types_names
            suspicious_result = any(pii_type in high_risk_types for pii_type in all_pii_types)
            
            # 개인 식별 의심 필터링 추가 처리
            if status_filter == '개인 식별 의심' and not suspicious_result:
                continue

            formatted_logs.append({
                'id': log.id,
                'status': log.status if log.status else '-',
                'timestamp': format_datetime_kst(log.timestamp), 
                'employee_id': log.ip_address if log.ip_address else '-',  
                'ip_address': log.ip_address if log.ip_address else '-',
                'hostname': log.hostname if log.hostname else '-',
                'os': log.os_info if log.os_info else '-',
                'browser': parse_browser_name(log.user_agent),
                'pii_types_names': pii_types_names,
                'pii_types_with_counts': [f"{k}:{v}" for k, v in log.pii_type_counts.items()] if log.pii_type_counts else [f"{pii_type}:1" for pii_type in pii_types_names],
                'pii_type_counts': log.pii_type_counts if log.pii_type_counts else {},
                'suspicious': suspicious_result,
                'file_type_name': log.file_type.type_name if log.file_type else '-',
                'llm_type_name': llm_type_name_safe,
                'filename': log.filename if log.filename else '-',
                'url': log.session_url if log.session_url else '-',
                'reason': log.reason if log.reason else '-',
                'validation_results': log.validation_results if log.validation_results else []
            })
        
        all_file_types = FileType.query.order_by(FileType.type_name).all()
        
        return render_template(
            'detection_details.html',
            active_page='detection_details',
            logs=formatted_logs,
            file_types=all_file_types,
            bar_chart_data=bar_chart_data,
            DETECTION_LOGS=formatted_logs,
            status_options=['성공', '실패', '개인 식별 의심']
        )
        
    except Exception as e:
        error_msg = f"[탐지 현황 로딩 오류] {str(e)}"
        print(error_msg.encode('utf-8', errors='replace').decode('utf-8'))
        traceback.print_exc()
        
        return render_template(
            'detection_details.html',
            active_page='detection_details',
            logs=[],
            file_types=[],
            bar_chart_data=[]
        )

@app.route('/user_type') 
@login_required
def show_user_type():
    """사용자별 현황 페이지를 위한 라우트 (user_type.html 렌더링)"""
    try:
        from_date = request.args.get('from')
        to_date = request.args.get('to')
        pii_type_name = request.args.get('type')
        source_type_name = request.args.get('source')
        status_filter = request.args.get('status')
        search_query = request.args.get('q')
        
        query = PiiLog.query.options(
            db.joinedload(PiiLog.file_type), 
            db.joinedload(PiiLog.llm_type),
            db.joinedload(PiiLog.pii_types)
        )
        
        if from_date: query = query.filter(PiiLog.timestamp >= from_date)
        if to_date:
            try:
                to_date_end = datetime.strptime(to_date, '%Y-%m-%d').date() + timedelta(days=1)
                query = query.filter(PiiLog.timestamp < to_date_end)
            except ValueError:
                pass
                
        if pii_type_name: query = query.join(PiiLog.pii_types).filter(PiiType.type_name == pii_type_name)
        if source_type_name: 
            query = query.join(PiiLog.file_type).filter(FileType.type_name == source_type_name)
        if status_filter:
            if status_filter == '개인 식별 의심':
                query = query.filter(PiiLog.status == '성공')
            else:
                query = query.filter(PiiLog.status == status_filter)

        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.filter(or_(
                PiiLog.ip_address.ilike(search_pattern),
                PiiLog.os_info.ilike(search_pattern),
                PiiLog.hostname.ilike(search_pattern),
                PiiLog.llm_type.has(LlmType.type_name.ilike(search_pattern)),
                PiiLog.filename.ilike(search_pattern),
                PiiLog.session_url.ilike(search_pattern),
                PiiLog.reason.ilike(search_pattern)
            ))

        logs_from_db = query.order_by(PiiLog.timestamp.desc()).all()

        logs = []
        user_counts = Counter()
        for log in logs_from_db:
            pii_types_list = [pii_type.type_name for pii_type in log.pii_types] if log.pii_types else []
            
            # suspicious 계산
            high_risk_types = ['ssn', 'card', 'account', 'alien_registration', 'passport', 'driver_license', 'ip', 'name', 'ps', 'person', 'alien_reg', 'email', 'phone', 'face_image']
            all_pii_types = list(log.pii_type_counts.keys()) + pii_types_list if log.pii_type_counts else pii_types_list
            suspicious_result = any(pii_type in high_risk_types for pii_type in all_pii_types)
            
            # 개인 식별 의심 필터링 추가 처리
            if status_filter == '개인 식별 의심' and not suspicious_result:
                continue
            
            ip_address = log.ip_address if log.ip_address else 'Unknown IP'
            if log.status == '성공':
                user_counts[ip_address] += 1
            
            logs.append({
                'id': log.id,
                'status': log.status if log.status else '-',
                'timestamp': format_datetime_kst(log.timestamp), 
                'emp': ip_address, 
                'ip_address': ip_address,
                'filename': log.filename if log.filename else '-',
                'reason': log.reason if log.reason else '',
                'source': log.file_type.type_name if log.file_type else '-', 
                'llm_type_name': log.llm_type.type_name if log.llm_type else '-',
                'types': pii_types_list,
                'pii_types_with_counts': [f"{k}:{v}" for k, v in log.pii_type_counts.items()] if log.pii_type_counts else [f"{pii_type}:1" for pii_type in pii_types_list],
                'pii_type_counts': log.pii_type_counts if log.pii_type_counts else {},
                'suspicious': suspicious_result,
                'os': log.os_info if log.os_info else '-', 
                'hostname': log.hostname if log.hostname else '-', 
                'browser': parse_browser_name(log.user_agent), 
                'url': log.session_url if log.session_url else '-', 
                'validation_results': log.validation_results if log.validation_results else [] 
            })
        
        chart_data = [{'emp': ip, 'count': count} for ip, count in user_counts.most_common(10)]
        
        all_pii_types = PiiType.query.order_by(PiiType.type_name).all()
        all_file_types = FileType.query.order_by(FileType.type_name).all()
        status_options = ['성공', '실패', '개인 식별 의심']

        return render_template(
            'user_type.html',
            active_page='user_type',
            logs_data=logs,
            chart_data=chart_data,
            pii_types=all_pii_types, 
            file_types=all_file_types,
            status_options=status_options
        )
    except Exception as e:
        error_msg = f"[사용자별 현황 로딩 오류] {type(e).__name__}: {str(e)}"
        print(error_msg.encode('utf-8', errors='replace').decode('utf-8'))
        traceback.print_exc()
        return render_template(
            'user_type.html', active_page='user_type', logs_data=[], chart_data=[], 
            pii_types=[], file_types=[], status_options=[]
        )
    
@app.route('/personal_information_type')
@login_required
def show_personal_information_type():
    """개인정보 유형별 현황 페이지"""
    try:
        from_date = request.args.get('from')
        to_date = request.args.get('to')
        pii_type_filter = request.args.get('type')
        source_filter = request.args.get('source')
        llm_filter = request.args.get('llm')
        status_filter = request.args.get('status')
        search_query = request.args.get('q')
        
        query = PiiLog.query.options(
            db.joinedload(PiiLog.file_type), 
            db.joinedload(PiiLog.llm_type),
            db.joinedload(PiiLog.pii_types)
        )

        if from_date: query = query.filter(PiiLog.timestamp >= from_date)
        if to_date:
            try:
                to_date_end = datetime.strptime(to_date, '%Y-%m-%d').date() + timedelta(days=1)
                query = query.filter(PiiLog.timestamp < to_date_end)
            except ValueError:
                pass

        if pii_type_filter: query = query.join(PiiLog.pii_types).filter(PiiType.type_name == pii_type_filter)
        if source_filter: query = query.join(PiiLog.file_type).filter(FileType.type_name == source_filter)
        if llm_filter: query = query.join(PiiLog.llm_type).filter(LlmType.type_name == llm_filter)
        if status_filter:
            if status_filter == '개인 식별 의심':
                query = query.filter(PiiLog.status == '성공')
            else:
                query = query.filter(PiiLog.status == status_filter)

        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.filter(or_(
                PiiLog.filename.ilike(search_pattern),
                PiiLog.ip_address.ilike(search_pattern),
                PiiLog.hostname.ilike(search_pattern),
                PiiLog.reason.ilike(search_pattern)
            ))
        
        logs_from_db = query.order_by(PiiLog.timestamp.desc()).all()

        logs = []
        pie_chart_counts = Counter()
        for log in logs_from_db:
            pii_types_list = [pii_type.type_name for pii_type in log.pii_types] if log.pii_types else []
            
            logs.append({
                'id': log.id,
                'status': log.status if log.status else '-',
                'timestamp': format_datetime_kst(log.timestamp), 
                'ip_address': log.ip_address if log.ip_address else '-',
                'filename': log.filename if log.filename else '-',
                'reason': log.reason if log.reason else '',
                'file_type_name': log.file_type.type_name if log.file_type else '-',
                'llm_type_name': log.llm_type.type_name if log.llm_type else '-',
                'pii_types_names': pii_types_list,
                'pii_types_with_counts': [f"{k}:{v}" for k, v in log.pii_type_counts.items()] if log.pii_type_counts else [f"{pii_type}:1" for pii_type in pii_types_list],
                'pii_type_counts': log.pii_type_counts if log.pii_type_counts else {},
                'suspicious': any(pii_type in ['ssn', 'card', 'account', 'alien_registration', 'passport', 'driver_license', 'ip', 'name', 'ps', 'person', 'email', 'phone', 'face_image'] for pii_type in (list(log.pii_type_counts.keys()) + pii_types_list if log.pii_type_counts else pii_types_list)),
                'validation_results': log.validation_results if log.validation_results else [],
                'os_info': log.os_info if log.os_info else '-', 
                'hostname': log.hostname if log.hostname else '-',
                'browser': parse_browser_name(log.user_agent), 
                'url': log.session_url if log.session_url else '-', 
            })
            
            if log.status == '성공':
                # pii_type_counts에서 개수 반영
                if log.pii_type_counts:
                    for name, count in log.pii_type_counts.items():
                        pie_chart_counts[name] += count
                else:
                    # 기존 방식
                    for name in pii_types_list:
                        pie_chart_counts[name] += 1
        
        pie_chart_data = [{'type': type, 'count': count} for type, count in pie_chart_counts.most_common()]

        all_pii_types = PiiType.query.order_by(PiiType.type_name).all()
        all_file_types = FileType.query.order_by(FileType.type_name).all()
        all_llm_types = LlmType.query.order_by(LlmType.type_name).all()
        status_options = ['성공', '실패', '개인 식별 의심']

        return render_template(
            'personal_information_type.html', 
            active_page='pii_type',
            logs=logs,
            pie_chart_data=pie_chart_data,
            pii_types=all_pii_types, 
            file_types=all_file_types, 
            llm_types=all_llm_types,
            status_options=status_options
        )
    except Exception as e:
        error_msg = f"[개인정보 유형 로딩 오류] {type(e).__name__}: {str(e)}"
        print(error_msg.encode('utf-8', errors='replace').decode('utf-8'))
        traceback.print_exc()
        return render_template(
            'personal_information_type.html', 
            active_page='pii_type', logs=[], pie_chart_data=[],
            pii_types=[], file_types=[], llm_types=[], status_options=[]
        )

# =====================================================================
# 서버 실행 및 테이블 생성
# =====================================================================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("All database tables created or already exist.")
        
    app.run(debug=True, port=5000, host='0.0.0.0')