import datetime
import json
from collections import Counter
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, or_
import pytz

# 1. Flask 앱 초기화 및 설정
app = Flask(__name__)

# server.py와 동일한 데이터베이스를 바라보도록 설정
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:mysql@localhost/shadowai'
CHROME_EXTENSION_ID = 'idcmhaehnimjicifehecnfffiifcnjnn'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.json.ensure_ascii = False

db = SQLAlchemy(app)
CORS(app, resources={r"/api/*": {"origins": f"chrome-extension://{CHROME_EXTENSION_ID}"}})


# =====================================================================
# 데이터베이스 모델 정의 (테이블 사용을 위해 필요)
# server.py에 정의된 테이블 구조를 참조하기 위해 동일하게 정의합니다.
# =====================================================================

pii_log_pii_type_links = db.Table('pii_log_pii_type_links',
    db.Column('pii_log_id', db.Integer, db.ForeignKey('pii_log.id'), primary_key=True),
    db.Column('pii_type_id', db.Integer, db.ForeignKey('pii_type.id'), primary_key=True)
)

class PiiLog(db.Model):
    __tablename__ = 'pii_log'
    id = db.Column(db.Integer, primary_key=True)
    process_type = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.now(pytz.timezone("Asia/Seoul")))
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


# =====================================================================
# API 엔드포인트 정의
# =====================================================================

# 1. 확장 프로그램으로부터 로그를 수신하는 API
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
        
        new_pii_log = PiiLog(
            employee_id=data.get('employee_id'),
            process_type=data.get('process_type'),
            filename=data.get('filename'),
            status=data.get('status', '성공'),
            reason=data.get('reason'),
            file_type=file_type_obj 
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
        
        return jsonify({'status': 'success', 'message': 'PII 로그가 성공적으로 저장되었습니다.'})
    except Exception as e:
        db.session.rollback()
        print(f"❌ [PII 로그 저장 오류] {e}")
        return jsonify({'status': 'error', 'message': f'PII 로그 저장 중 오류 발생: {e}'}), 500

# =====================================================================
# 페이지 렌더링 엔드포인트
# =====================================================================

@app.route('/')
@app.route('/dashboard')
def show_dashboard():
    try:
        # 1. 기간별 탐지 건수 (최근 7일)
        seven_days_ago = datetime.date.today() - datetime.timedelta(days=6)
        detections_over_time_query = db.session.query(
            func.date(PiiLog.timestamp).label('date'),
            func.count(PiiLog.id).label('count')
        ).filter(PiiLog.timestamp >= seven_days_ago).group_by('date').order_by('date').all()
        detections_over_time = [{'date': r.date.strftime('%Y-%m-%d'), 'count': r.count} for r in detections_over_time_query]

        # 2. 금일 탐지 유형
        today = datetime.date.today()
        today_types_query = db.session.query(
            PiiType.type_name, func.count(PiiLog.id).label('count')
        ).select_from(PiiLog).join(pii_log_pii_type_links).join(PiiType).filter(func.date(PiiLog.timestamp) == today, PiiLog.status == '성공').group_by(PiiType.type_name).all()
        today_stats = {
            'types': [{'type': r.type_name, 'count': r.count} for r in today_types_query],
            'total': sum(r.count for r in today_types_query)
        }
        
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
        pii_type_overall_stats = [
            {'type': r.type_name, 'count': r.count, 'percentage': (r.count / total_detections * 100) if total_detections > 0 else 0}
            for r in total_pii_types_query
        ]

        # --- ▼▼▼ (신규) 최근 탐지 실패 로그 3건 조회 ▼▼▼ ---
        recent_failures = PiiLog.query.filter_by(status='실패').order_by(PiiLog.timestamp.desc()).limit(3).all()
        # --- ▲▲▲ ---

        return render_template(
            'dashboard.html',
            active_page='dashboard',
            detections_over_time=detections_over_time,
            today_stats=today_stats,
            top_users=top_users,
            source_stats=source_stats,
            pii_type_overall_stats=pii_type_overall_stats,
            recent_failures=recent_failures  # 템플릿으로 전달
        )

    except Exception as e:
        print(f"❌ [대시보드 로딩 오류] {e}")
        return "대시보드를 불러오는 중 오류가 발생했습니다.", 500

@app.route('/pii_type_details')
def show_pii_type_details():
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
        related_users = set()
        for log in logs:
            related_users.add(log.employee_id)
            if log.status == '성공':
                for pii_type in log.pii_types:
                    pie_chart_counts[pii_type.type_name] += 1
        
        pie_chart_data = [{'type': name, 'count': count} for name, count in pie_chart_counts.items()]
        summary_data = {'total_logs': len(logs), 'related_users': len(related_users), 'from_date': from_date, 'to_date': to_date}
        
        all_pii_types = PiiType.query.order_by(PiiType.type_name).all()
        all_file_types = FileType.query.order_by(FileType.type_name).all()

        return render_template(
            'pii_type_details.html', 
            active_page='pii_type',
            logs=logs,
            pii_types=all_pii_types,
            file_types=all_file_types,
            pie_chart_data=pie_chart_data,
            summary=summary_data
        )
    except Exception as e:
        print(f"❌ [상세 페이지 로딩 오류] {e}")
        return "상세 페이지를 불러오는 중 오류가 발생했습니다.", 500

# receive_server.py (라우트 경로 수정)
# ... (상단 코드 및 /dashboard 등 다른 라우트는 동일) ...

# --- ▼▼▼ (핵심 수정) 라우트 경로 및 템플릿 파일명 변경 ▼▼▼ ---
@app.route('/personal_information_type')
def show_personal_information_type():
    try:
        # ... (내부 로직은 이전과 동일: 필터 값 가져오기, 쿼리 실행 등) ...
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
        related_users = set()
        for log in logs:
            related_users.add(log.employee_id)
            if log.status == '성공':
                for pii_type in log.pii_types:
                    pie_chart_counts[pii_type.type_name] += 1
        
        pie_chart_data = [{'type': name, 'count': count} for name, count in pie_chart_counts.items()]
        summary_data = {'total_logs': len(logs), 'related_users': len(related_users), 'from_date': from_date, 'to_date': to_date}
        
        all_pii_types = PiiType.query.order_by(PiiType.type_name).all()
        all_file_types = FileType.query.order_by(FileType.type_name).all()

        return render_template(
            'personal_information_type.html',  # 렌더링할 파일 이름 변경
            active_page='pii_type',
            logs=logs,
            pii_types=all_pii_types,
            file_types=all_file_types,
            pie_chart_data=pie_chart_data,
            summary=summary_data
        )
    except Exception as e:
        print(f"❌ [상세 페이지 로딩 오류] {e}")
        return "상세 페이지를 불러오는 중 오류가 발생했습니다.", 500
# --- ▲▲▲ ---


@app.route('/detection_status')
def show_detection_status():
    try:
        period = request.args.get('period', 'daily')
        now = datetime.datetime.utcnow()
        
        # --- ▼▼▼ (핵심 수정) 쿼리를 담을 변수 초기화 ▼▼▼ ---
        detection_counts_query = None
        
        if period == 'daily':
            today = datetime.date.today()
            # 시간을 무시하고 '날짜'만 비교하도록 func.date() 사용
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
            'detection_status.html',
            active_page='detection_status',
            active_period=period,
            detection_stats=detection_stats,
            total_count=total_count,
            logs=logs
        )
    except Exception as e:
        print(f"❌ [탐지 현황 로딩 오류] {e}")
        return "탐지 현황 페이지를 불러오는 중 오류가 발생했습니다.", 500
# --- ▲▲▲ ---

# --- ▼▼▼ (신규) 소스별 현황 상세 페이지 라우트 ▼▼▼ ---
@app.route('/source_details')
def show_source_details():
    try:
        # ... (필터링 로직은 이전과 동일) ...
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
        
        # --- ▼▼▼ (핵심 수정) 하드코딩된 리스트를 DB 조회로 변경 ▼▼▼ ---
        
        # 1. 필터링된 로그를 기반으로 소스별 카운트 집계
        bar_chart_counts = Counter()
        for log in logs:
            bar_chart_counts[log.file_type.type_name] += 1
        
        # 2. DB에 존재하는 모든 파일 유형(Source Type)을 가져옴
        all_source_types = FileType.query.order_by(FileType.type_name).all()
        
        # 3. 동적으로 조회한 전체 파일 유형 리스트를 기반으로 차트 데이터를 생성
        #    (필터링된 결과에 카운트가 없으면 0으로 표시)
        bar_chart_data = [{'source': ft.type_name, 'count': bar_chart_counts.get(ft.type_name, 0)} for ft in all_source_types]
        
        # --- ▲▲▲ ---

        all_file_types_for_filter = FileType.query.order_by(FileType.type_name).all()

        return render_template(
            'source_details.html', 
            active_page='source',
            logs=logs,
            file_types=all_file_types_for_filter,
            bar_chart_data=bar_chart_data
        )
    except Exception as e:
        print(f"❌ [소스별 현황 로딩 오류] {e}")
        return "소스별 현황 페이지를 불러오는 중 오류가 발생했습니다.", 500

# --- ▼▼▼ (핵심 수정) /alerts 라우트를 플레이스홀더에서 실제 기능으로 교체 ▼▼▼ ---
@app.route('/alerts')
def show_alerts():
    try:
        from_date = request.args.get('from')
        to_date = request.args.get('to')
        employee_id = request.args.get('emp')
        search_query = request.args.get('q')

        # 기본 쿼리를 '실패' 상태 로그로 설정
        query = PiiLog.query.filter_by(status='실패')

        if from_date: query = query.filter(PiiLog.timestamp >= from_date)
        if to_date:
            to_date_end = datetime.datetime.strptime(to_date, '%Y-%m-%d').date() + datetime.timedelta(days=1)
            query = query.filter(PiiLog.timestamp < to_date_end)
        if employee_id: query = query.filter(PiiLog.employee_id.ilike(f"%{employee_id}%"))
        if search_query:
            # 파일명 또는 실패 사유에서 검색
            query = query.filter(or_(
                PiiLog.filename.ilike(f"%{search_query}%"),
                PiiLog.reason.ilike(f"%{search_query}%")
            ))
            
        failed_logs = query.order_by(PiiLog.timestamp.desc()).all()
        
        return render_template(
            'alerts.html', 
            active_page='alerts',
            logs=failed_logs
        )
    except Exception as e:
        print(f"❌ [알림 페이지 로딩 오류] {e}")
        return "알림 페이지를 불러오는 중 오류가 발생했습니다.", 500
# --- ▲▲▲ ---

# =====================================================================
# 서버 실행 (테이블 생성 안 함)
# =====================================================================
if __name__ == '__main__':
    app.run(debug=True, port=5002)