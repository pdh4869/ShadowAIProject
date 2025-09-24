from flask import Flask, request, jsonify
from flask_cors import CORS

# 1. Flask 앱 초기화
app = Flask(__name__)

# --- ▼▼▼ 사용자 환경에 맞게 수정 ▼▼▼ ---
# 통신을 허용할 확장 프로그램의 고유 ID
CHROME_EXTENSION_ID = 'idcmhaehnimjicifehecnfffiifcnjnn' 
# --- ▲▲▲ 사용자 환경에 맞게 수정 ▲▲▲ ---

# 2. CORS 설정
# 특정 확장 프로그램으로부터의 API 요청만 허용합니다.
CORS(app, resources={r"/api/*": {"origins": f"chrome-extension://{CHROME_EXTENSION_ID}"}})


# 3. API 엔드포인트 정의
# '/api/receive-data' 경로로 POST 요청을 받습니다.
@app.route('/api/receive-data', methods=['POST'])
def receive_data():
    # 요청으로 들어온 JSON 데이터를 확인합니다.
    data = request.get_json()

    # 데이터나 employee_id 필드가 없는 경우 에러를 반환합니다.
    if not data or 'employee_id' not in data:
        return jsonify({'status': 'error', 'message': 'employee_id가 누락되었습니다.'}), 400
    
    employee_id = data['employee_id']
    
    # 터미널(콘솔)에 수신된 사번을 출력하여 확인합니다.
    print(f"✅ [데이터 수신 성공] Employee ID: {employee_id}")
    
    # 확장 프로그램에 성공적으로 받았다고 응답을 보냅니다.
    return jsonify({
        'status': 'success',
        'message': f'서버가 사번 {employee_id}를 성공적으로 수신했습니다.'
    })

# 4. 서버 실행
if __name__ == '__main__':
    # 다른 서버와 충돌하지 않도록 5002번 포트에서 실행합니다.
    app.run(debug=True, port=5002)