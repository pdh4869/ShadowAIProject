from backend import app, db, PiiLog, pii_log_pii_type_links

with app.app_context():
    # 연결 테이블 데이터 삭제
    db.session.execute(pii_log_pii_type_links.delete())
    
    # PII 로그 삭제
    PiiLog.query.delete()
    
    db.session.commit()
    print("All PII logs deleted successfully.")
