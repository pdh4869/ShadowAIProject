# receive_server.py 파일에서 Flask app과 db, DashboardAdmin 모델을 가져옵니다.
from receive import app, db, DashboardAdmin

def create_super_admin(employee_id, password):
    """최초의 '최고 관리자(super)' 계정을 생성하는 함수"""
    
    # Flask 애플리케이션의 컨텍스트 안에서 데이터베이스 작업을 수행합니다.
    with app.app_context():
        # 이미 해당 ID의 관리자가 있는지 확인합니다.
        if DashboardAdmin.query.filter_by(employee_id=employee_id).first():
            print(f"관리자 ID '{employee_id}'는 이미 존재합니다.")
            return

        # 새 관리자 객체를 생성하고 권한을 'super'로 지정합니다.
        new_admin = DashboardAdmin(
            employee_id=employee_id,
            privilege='super'
        )
        # 비밀번호를 해시하여 설정합니다.
        new_admin.set_password(password)

        # 데이터베이스에 추가하고 변경사항을 저장합니다.
        db.session.add(new_admin)
        db.session.commit()
        print(f"최고 관리자 '{employee_id}' 계정이 성공적으로 생성되었습니다.")

if __name__ == '__main__':
    # 여기에 생성하고 싶은 최초 관리자의 ID와 비밀번호를 설정하세요.
    # 이 스크립트를 실행한 후에는 이 값으로 로그인할 수 있습니다.
    admin_id = "superadmin"
    admin_password = "password1234"

    print("최초 관리자 계정 생성을 시도합니다...")
    create_super_admin(admin_id, admin_password)