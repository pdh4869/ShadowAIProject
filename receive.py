import datetime
from collections import Counter
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, or_
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

# 1. Flask 앱 초기화 및 설정
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:mysql@localhost/shadowai'
app.config['SECRET_KEY'] = 'your-very-secret-key-for-dashboard' # 로그인 세션 관리를 위한 시크릿 키
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.json.ensure_ascii = False

db = SQLAlchemy(app)

# 2. Flask-Login 설정
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'dashboard_login_page' # 로그인 페이지 함수의 이름

# =====================================================================
# 데이터베이스 모델 전체 정의
# =====================================================================

class DashboardAdmin(UserMixin, db.Model):
    __tablename__ = 'dashboard_admin'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    privilege = db.Column(db.String(50), nullable=False, default='general')
    name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    last_login = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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
    status = db.Column(db.String(20), nullable=False, default='성공')
    reason = db.Column(db.String(255), nullable=True)
    
    file_type = db.relationship('FileType', backref='pii_logs')
    pii_types = db.relationship('PiiType', secondary=pii_log_pii_type_links, backref='pii_logs', lazy='subquery')

class FileType(db.Model):
    __tablename__ = 'file_type'
    id = db.Column(db.Integer, primary_key=True)
    type_name = db.Column(db.String(50), unique=True, nullable=False)

class PiiType(db.Model):
    __tablename__ = 'pii_type'
    id = db.Column(db.Integer, primary_key=True)
    type_name = db.Column(db.String(50), unique=True, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return DashboardAdmin.query.get(int(user_id))

# =====================================================================
# 로그인/로그아웃 및 관리자 기능 라우트
# =====================================================================

@app.route('/login')
def dashboard_login_page():
    return render_template('admin_login.html')

@app.route('/api/dashboard_login', methods=['POST'])
def dashboard_login_api():
    data = request.get_json()
    employee_id = data.get('employee_id')
    password = data.get('password')
    user = DashboardAdmin.query.filter_by(employee_id=employee_id).first()
    if user and user.check_password(password):
        login_user(user)
        user.last_login = datetime.datetime.now(datetime.timezone.utc)
        db.session.commit()
        return jsonify({'status': 'success', 'message': '로그인 성공'})
    return jsonify({'status': 'error', 'message': 'ID 또는 비밀번호가 잘못되었습니다.'}), 401

@app.route('/logout')
@login_required
def dashboard_logout():
    logout_user()
    return redirect(url_for('dashboard_login_page'))

@app.route('/admin/manage')
@login_required
def admin_manage():
    if current_user.privilege != 'super':
        abort(403)
    
    # 1. 데이터베이스에서 DashboardAdmin 객체 리스트를 가져옵니다.
    users_from_db = DashboardAdmin.query.order_by(DashboardAdmin.created_at.desc()).all()

    # --- ▼▼▼ (핵심 수정) 객체 리스트를 딕셔너리 리스트로 변환 ▼▼▼ ---
    # JavaScript가 이해할 수 있는 단순한 형태로 데이터를 가공합니다.
    users_for_template = [
        {
            "employee_id": u.employee_id,
            "name": u.name,
            "email": u.email,
            "privilege": u.privilege,
            # 날짜/시간 객체는 tojson이 처리할 수 있도록 문자열(ISO 형식)으로 변환합니다.
            "last_login": u.last_login.isoformat() if u.last_login else None,
            "created_at": u.created_at.isoformat() if u.created_at else None
        }
        for u in users_from_db
    ]
    # --- ▲▲▲ ---
    
    # 2. 이제 객체가 아닌, 가공된 딕셔너리 리스트를 템플릿으로 전달합니다.
    return render_template('admin_manage.html', users=users_for_template)

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
    return jsonify({'status': 'success', 'message': '새 관리자 계정이 생성되었습니다.'})

@app.route('/api/admin/change_password', methods=['POST'])
@login_required
def api_admin_change_password():
    if current_user.privilege != 'super': abort(403)
    data = request.get_json()
    user_to_edit = DashboardAdmin.query.filter_by(employee_id=data['emp']).first_or_404()
    user_to_edit.set_password(data['pwd'])
    db.session.commit()
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
    return jsonify({'status': 'success', 'message': '계정이 삭제되었습니다.'})

# =====================================================================
# 대시보드 페이지 렌더링 엔드포인트
# =====================================================================

@app.route('/')
@app.route('/dashboard')
@login_required
def show_dashboard():
    try:
        # 1. 기간별 탐지 건수 (최근 7일)
        seven_days_ago = datetime.date.today() - datetime.timedelta(days=6)
        detections_over_time_query = db.session.query(
            func.date(PiiLog.timestamp).label('date'),
            func.count(PiiLog.id).label('count')
        ).filter(PiiLog.timestamp >= seven_days_ago).group_by('date').order_by('date').all()
        detections_over_time = [{'date': r.date.strftime('%Y-%m-%d'), 'count': r.count} for r in detections_over_time_query]

        # 2. 금일 탐지 유형 (Top 5)
        today = datetime.date.today()
        total_today_count = db.session.query(func.count(PiiLog.id)).filter(
            func.date(PiiLog.timestamp) == today,
            PiiLog.status == '성공'
        ).scalar() or 0
        top_5_today_query = db.session.query(
            PiiType.type_name, func.count(PiiLog.id).label('count')
        ).select_from(PiiLog).join(pii_log_pii_type_links).join(PiiType).filter(
            func.date(PiiLog.timestamp) == today, PiiLog.status == '성공'
        ).group_by(PiiType.type_name).order_by(func.count(PiiLog.id).desc()).limit(5).all()
        today_stats = {'types': [{'type': r.type_name, 'count': r.count} for r in top_5_today_query], 'total': total_today_count}
        
        # 3. 사용자별 탐지 빈도 (TOP 5)
        top_users_query = db.session.query(
            PiiLog.employee_id, func.count(PiiLog.id).label('count')
        ).filter(PiiLog.status == '성공').group_by(PiiLog.employee_id).order_by(func.count(PiiLog.id).desc()).limit(5).all()
        top_users = [{'account': r.employee_id, 'count': r.count} for r in top_users_query]

        # 4. 소스별 분포
        source_dist_query = db.session.query(
            FileType.type_name, func.count(PiiLog.id).label('count')
        ).join(PiiLog).filter(PiiLog.status == '성공').group_by(FileType.type_name).all()
        source_stats = [{'source': r.type_name, 'count': r.count} for r in source_dist_query]

        # 5. 전체 탐지 유형별 통계
        total_pii_types_query = db.session.query(
            PiiType.type_name, func.count(PiiLog.id).label('count')
        ).select_from(PiiLog).join(pii_log_pii_type_links).join(PiiType).filter(PiiLog.status == '성공').group_by(PiiType.type_name).order_by(func.count(PiiLog.id).desc()).all()
        total_detections = sum(r.count for r in total_pii_types_query)
        pii_type_overall_stats = [{'type': r.type_name, 'count': r.count, 'percentage': (r.count / total_detections * 100) if total_detections > 0 else 0} for r in total_pii_types_query]

        # 6. 최근 탐지 실패 로그
        recent_failures = PiiLog.query.filter_by(status='실패').order_by(PiiLog.timestamp.desc()).limit(3).all()

        return render_template(
            'dashboard.html', active_page='dashboard', detections_over_time=detections_over_time,
            today_stats=today_stats, top_users=top_users, source_stats=source_stats,
            pii_type_overall_stats=pii_type_overall_stats, recent_failures=recent_failures
        )
    except Exception as e:
        print(f"❌ [대시보드 로딩 오류] {e}")
        return "대시보드를 불러오는 중 오류가 발생했습니다.", 500

@app.route('/detection_status')
@login_required
def show_detection_status():
    try:
        period = request.args.get('period', 'daily')
        now = datetime.datetime.utcnow()
        detection_counts_query = None
        
        if period == 'daily':
            today = datetime.date.today()
            detection_counts_query = db.session.query(
                PiiType.type_name, func.count(PiiLog.id).label('count')
            ).select_from(PiiLog).join(pii_log_pii_type_links).join(PiiType).filter(
                func.date(PiiLog.timestamp) == today, PiiLog.status == '성공'
            ).group_by(PiiType.type_name).all()
        elif period == 'weekly':
            start_of_week = now - datetime.timedelta(days=now.weekday())
            start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
            detection_counts_query = db.session.query(
                PiiType.type_name, func.count(PiiLog.id).label('count')
            ).select_from(PiiLog).join(pii_log_pii_type_links).join(PiiType).filter(
                PiiLog.timestamp >= start_of_week, PiiLog.status == '성공'
            ).group_by(PiiType.type_name).all()
        elif period == 'monthly':
            start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            detection_counts_query = db.session.query(
                PiiType.type_name, func.count(PiiLog.id).label('count')
            ).select_from(PiiLog).join(pii_log_pii_type_links).join(PiiType).filter(
                PiiLog.timestamp >= start_of_month, PiiLog.status == '성공'
            ).group_by(PiiType.type_name).all()

        detection_stats = {r.type_name: r.count for r in detection_counts_query}
        total_count = sum(detection_stats.values())
        logs = PiiLog.query.order_by(PiiLog.timestamp.desc()).limit(100).all()
        return render_template(
            'detection_status.html', active_page='detection_status', active_period=period,
            detection_stats=detection_stats, total_count=total_count, logs=logs
        )
    except Exception as e:
        print(f"❌ [탐지 현황 로딩 오류] {e}")
        return "탐지 현황 페이지를 불러오는 중 오류가 발생했습니다.", 500

@app.route('/personal_information_type')
@login_required
def show_personal_information_type():
    try:
        from_date = request.args.get('from')
        to_date = request.args.get('to')
        pii_type_name = request.args.get('type')
        source_type_name = request.args.get('source')
        employee_id = request.args.get('emp')
        search_query = request.args.get('q')

        query = PiiLog.query
        if from_date: query = query.filter(PiiLog.timestamp >= from_date)
        if to_date:
            to_date_end = datetime.datetime.strptime(to_date, '%Y-%m-%d').date() + datetime.timedelta(days=1)
            query = query.filter(PiiLog.timestamp < to_date_end)
        if pii_type_name: query = query.join(PiiLog.pii_types).filter(PiiType.type_name == pii_type_name)
        if source_type_name: query = query.join(PiiLog.file_type).filter(FileType.type_name == source_type_name)
        if employee_id: query = query.filter(PiiLog.employee_id.ilike(f"%{employee_id}%"))
        if search_query: query = query.filter(PiiLog.filename.ilike(f"%{search_query}%"))
            
        logs = query.order_by(PiiLog.timestamp.desc()).all()
        
        pie_chart_counts = Counter()
        for log in logs:
            if log.status == '성공':
                for pii_type in log.pii_types:
                    pie_chart_counts[pii_type.type_name] += 1
        
        pie_chart_data = [{'type': name, 'count': count} for name, count in pie_chart_counts.items()]
        
        all_pii_types = PiiType.query.order_by(PiiType.type_name).all()
        all_file_types = FileType.query.order_by(FileType.type_name).all()

        return render_template(
            'personal_information_type.html', active_page='pii_type', logs=logs,
            pii_types=all_pii_types, file_types=all_file_types,
            pie_chart_data=pie_chart_data
        )
    except Exception as e:
        print(f"❌ [개인정보 유형별 현황 로딩 오류] {e}")
        return "페이지를 불러오는 중 오류가 발생했습니다.", 500

@app.route('/source_details')
@login_required
def show_source_details():
    try:
        from_date = request.args.get('from')
        to_date = request.args.get('to')
        source_type_name = request.args.get('source')
        status = request.args.get('status')
        employee_id = request.args.get('emp')
        search_query = request.args.get('q')

        query = PiiLog.query
        if from_date: query = query.filter(PiiLog.timestamp >= from_date)
        if to_date:
            to_date_end = datetime.datetime.strptime(to_date, '%Y-%m-%d').date() + datetime.timedelta(days=1)
            query = query.filter(PiiLog.timestamp < to_date_end)
        if source_type_name: query = query.join(PiiLog.file_type).filter(FileType.type_name == source_type_name)
        if status: query = query.filter(PiiLog.status == status)
        if employee_id: query = query.filter(PiiLog.employee_id.ilike(f"%{employee_id}%"))
        if search_query: query = query.filter(PiiLog.filename.ilike(f"%{search_query}%"))
            
        logs = query.order_by(PiiLog.timestamp.desc()).all()
        
        bar_chart_counts = Counter()
        for log in logs:
            bar_chart_counts[log.file_type.type_name] += 1
        
        all_source_types = FileType.query.order_by(FileType.type_name).all()
        bar_chart_data = [{'source': ft.type_name, 'count': bar_chart_counts.get(ft.type_name, 0)} for ft in all_source_types]

        all_file_types_for_filter = FileType.query.order_by(FileType.type_name).all()

        return render_template(
            'source_details.html', active_page='source', logs=logs,
            file_types=all_file_types_for_filter, bar_chart_data=bar_chart_data
        )
    except Exception as e:
        print(f"❌ [소스별 현황 로딩 오류] {e}")
        return "소스별 현황 페이지를 불러오는 중 오류가 발생했습니다.", 500

@app.route('/alerts')
@login_required
def show_alerts():
    try:
        from_date = request.args.get('from')
        to_date = request.args.get('to')
        employee_id = request.args.get('emp')
        search_query = request.args.get('q')

        query = PiiLog.query.filter_by(status='실패')
        if from_date: query = query.filter(PiiLog.timestamp >= from_date)
        if to_date:
            to_date_end = datetime.datetime.strptime(to_date, '%Y-%m-%d').date() + datetime.timedelta(days=1)
            query = query.filter(PiiLog.timestamp < to_date_end)
        if employee_id: query = query.filter(PiiLog.employee_id.ilike(f"%{employee_id}%"))
        if search_query:
            query = query.filter(or_(
                PiiLog.filename.ilike(f"%{search_query}%"),
                PiiLog.reason.ilike(f"%{search_query}%")
            ))
            
        failed_logs = query.order_by(PiiLog.timestamp.desc()).all()
        
        return render_template('alerts.html', active_page='alerts', logs=failed_logs)
    except Exception as e:
        print(f"❌ [알림 페이지 로딩 오류] {e}")
        return "알림 페이지를 불러오는 중 오류가 발생했습니다.", 500

# =====================================================================
# 서버 실행 및 테이블 생성
# =====================================================================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("All tables created or already exist.")
    app.run(debug=True, port=5002)