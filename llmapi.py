from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import os
import io
import google.generativeai as genai
import docx
from pypdf import PdfReader

# Flask 애플리케이션 및 파일 업로드 경로 설정
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Gemini API 설정
# TODO: YOUR_API_KEY를 실제 API 키로 교체하세요.
GOOGLE_API_KEY = "AIzaSyAMnkxFSHnvh90fokMkI3qVOSHfrDykoKY"
genai.configure(api_key=GOOGLE_API_KEY)

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(file):
    """업로드된 파일에서 텍스트를 추출합니다."""
    file_extension = file.filename.rsplit('.', 1)[1].lower()
    text_content = ""

    # 파일 커서를 맨 앞으로 이동시켜야 라이브러리가 파일을 읽을 수 있음
    file.seek(0)

    if file_extension == 'pdf':
        try:
            reader = PdfReader(file)
            for page in reader.pages:
                text_content += page.extract_text() or ""
        except Exception as e:
            return f"PDF 파일을 읽는 중 오류 발생: {e}"

    elif file_extension == 'docx':
        try:
            doc = docx.Document(file)
            for para in doc.paragraphs:
                text_content += para.text + "\n"
        except Exception as e:
            return f"DOCX 파일을 읽는 중 오류 발생: {e}"
            
    # HWP 파일은 파이썬 라이브러리로 직접 읽기 어려움
    # 복잡한 문서 분석은 Gemini Vision API를 사용하는 것이 더 효과적일 수 있음

    return text_content

@app.route('/')
def upload_form():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "파일을 찾을 수 없습니다."}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "파일을 선택하세요."}), 400

    if file and allowed_file(file.filename):
        # 1. 파일에서 텍스트 추출
        extracted_text = extract_text_from_file(file)

        if not extracted_text:
            return jsonify({"error": "파일에서 텍스트를 추출할 수 없거나 빈 파일입니다."}), 400

        # 2. 추출한 텍스트를 Gemini API에 보내서 분석 요청
        try:
            model = genai.GenerativeModel('gemini-2.5-pro')
            prompt = f"다음 문서 내용을 분석하고 요약해줘:\n\n{extracted_text}"
            response = model.generate_content(prompt)
            analysis_result = response.text
        except Exception as e:
            return jsonify({"error": f"Gemini API 호출 오류: {e}"}), 500

        # 3. 분석 결과를 JSON 형태로 반환
        return jsonify({"filename": file.filename, "analysis": analysis_result})
    else:
        return jsonify({"error": "허용되지 않는 파일 형식입니다."}), 400

if __name__ == '__main__':
    app.run(debug=True)