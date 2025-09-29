import uvicorn # ASGI 서버 실행용
import LocalServer
from typing import List
from fastapi import FastAPI, UploadFile, File # FastAPI = API 앱 생성에 사용, File/Form = POST 요청에서 파일이나 폼 데이터 받을 때 사용                        
from fastapi.responses import JSONResponse # JSONResponse = 텍스트의 경우, 결과물을 JSON 형식으로 반환할 때 사용
from Logic import handle_input_raw, detect_by_ner, detect_by_regex, encrypt_data, send_to_backend, apply_masking, apply_face_mosaic
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

class TextInput(BaseModel):
    text: str

Key = b"1234567890abcdef"
IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "bmp", "webp", "tif", "tiff"]
app = FastAPI() # FastAPI 앱 객체를 생성. 아래에서 이 객체에 엔드 포인트를 붙이게 됨.

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 적용시에는 ["chrome-extension://<확장ID>"], 그러니까 ["chrome-extension://abcdefghijklmno"] 형식
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/") # 브라우저에서 http://127.0.0.1:8000으로 접속하면 기본적으로 GET 요청을 보낸다.
def root(): # 근데 우린 POST만 정의했지, 우리가 쓸 API 서버는 GET이 아니라 POST를 받아야 한다.
    return {"message": "로컬 서버 정상 작동 중. POST /mask-file 또는 /mask-text 구문을 이용할 것."}
    # GET / 요청이 들어오면 간단한 안내 메시지를 JSON 형태로 반환
    # 본격적인 기능은 POST에 있으므로 이건 “서버 살아있냐” 체크 용도

@app.post("/mask-files/")
async def mask_multiple_files(Files: List[UploadFile] = File(...)):
    results = {}
    password_protected = False

    for uploaded_file in Files:
        filename = uploaded_file.filename
        extension = filename.split('.')[-1].lower()
        try:
            content = await uploaded_file.read()
            if extension in IMAGE_EXTENSIONS:
                content = apply_face_mosaic(content)
            detected, file_bytes, media_type, masked_text, backend_status = handle_input_raw(content, extension)

            if detected:
                results[filename] = {
                    "status": "처리 완료",
                    "detected": detected,
                    "masked_text": masked_text,
                    "backend_transmission": "성공" if backend_status else "실패"
                }
            else:
                results[filename] = {
                    "status": "탐지된 민감정보 없음"
                }

        except ValueError as ve:
            results[filename] = {
                "status": "에러",
                "message": str(ve)
            }
            password_protected = True

        except Exception as e:
            results[filename] = {
                "status": "에러",
                "message": f"처리 실패: {str(e)}"
            }

    return JSONResponse(
        content={"result_summary": results},
        status_code=200 if not password_protected else 400
    )

@app.post("/mask-text/")
async def mask_text(input: TextInput):
    try:
        text = input.text
        print("[INFO] 텍스트 입력으로 감지됨")

        detected = detect_by_regex(text) + detect_by_ner(text)

        if not detected:
            return JSONResponse(
                content={"result_summary": {
                    "입력 텍스트": {
                        "status": "탐지된 민감정보 없음"
                    }
                }},
                status_code=200
            )

        masked_text = apply_masking(text, detected)
        encrypted = encrypt_data(masked_text.encode("utf-8"), Key)
        ok = send_to_backend(encrypted)

        result_summary = {
            "입력 텍스트": {
                "status": "처리 완료",
                "detected": detected,
                "masked_text": masked_text,
                "backend_transmission": "성공" if ok else "실패"
            }
        }

        return JSONResponse(content={"result_summary": result_summary}, status_code=200)

    except Exception as e:
        return JSONResponse(
            content={"result_summary": {
                "입력 텍스트": {
                    "status": "에러",
                    "message": str(e)
                }
            }},
            status_code=500
        )

if __name__ == "__main__":
    uvicorn.run(LocalServer.app, host="127.0.0.1", port=8000, reload=False)
    LocalServer.py
    # 파일 안의 app 객체를 실행
    # 로컬호스트 기준으로만 열림 (외부 노출 X)
    # 포트 8000 사용
    # 파일 수정되면 자동 재시작 (개발 편의성)