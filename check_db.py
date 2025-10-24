from backend import app, db, PiiLog, PiiType

with app.app_context():
    # 모든 PII 타입 확인
    all_types = PiiType.query.all()
    print("=== DB에 저장된 PII 타입들 ===")
    for pii_type in all_types:
        print(f"- {pii_type.type_name}")
    
    print("\n=== 최근 로그 5개의 PII 타입 ===")
    recent_logs = PiiLog.query.order_by(PiiLog.timestamp.desc()).limit(5).all()
    for log in recent_logs:
        print(f"\nLog ID: {log.id}")
        print(f"  pii_types: {[p.type_name for p in log.pii_types]}")
        print(f"  pii_type_counts: {log.pii_type_counts}")
