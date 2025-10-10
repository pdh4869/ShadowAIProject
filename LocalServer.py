import uvicorn # ASGI 서버 실행용
import LocalServer
import json 
import os
import shutil
import platform
import socket
import datetime
from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI, UploadFile, Request, Form, File # FastAPI = API 앱 생성에 사용, File/Form = POST 요청에서 파일이나 폼 데이터 받을 때 사용                        
from fastapi.responses import JSONResponse # JSONResponse = 텍스트의 경우, 결과물을 JSON 형식으로 반환할 때 사용
from Logic import handle_input_raw, detect_by_ner, detect_by_regex, send_to_backend
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from collections import Counter

class TextInput(BaseModel):
    text: str
    tab: dict | None = None
    agent_id: str | None = None
    source_url: str | None = None

image_folder = "processed_faces"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 시작 시
    if os.path.exists(image_folder):
        shutil.rmtree(image_folder)
    print("[INFO] processed_faces 초기화 완료")

    yield  # 여기서 애플리케이션 실행

    # 서버 종료 시
    if os.path.exists(image_folder):
        shutil.rmtree(image_folder)
    print("[INFO] processed_faces 삭제 완료")

# app = FastAPI() # FastAPI 앱 객체를 생성. 아래에서 이 객체에 엔드 포인트를 붙이게 됨.
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["chrome-extension://noladakejgehkjpjfgbimihbmipjkink"],  # 실제 적용시에는 ["chrome-extension://<확장ID>"], 그러니까 ["chrome-extension://abcdefghijklmno"] 형식
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)
os.makedirs(image_folder, exist_ok=True)
app.mount("/processed_faces", StaticFiles(directory="processed_faces"), name="faces")

@app.get("/") # 브라우저에서 http://127.0.0.1:8000으로 접속하면 기본적으로 GET 요청을 보낸다.
def root(): # 근데 우린 POST만 정의했지, 우리가 쓸 API 서버는 GET이 아니라 POST를 받아야 한다.
    return {"message": "로컬 서버 정상 작동 중. POST /mask-file 또는 /mask-text 구문을 이용할 것."}
    # GET / 요청이 들어오면 간단한 안내 메시지를 JSON 형태로 반환
    # 본격적인 기능은 POST에 있으므로 이건 “서버 살아있냐” 체크 용도

@app.post("/mask-files/")
async def mask_multiple_files(
    request: Request,
    Files: List[UploadFile] = File(...),
    tab: str | None = Form(None),
    agent_id: str | None = Form(None),
    source_url: str | None = Form(None)
):
    results = {}
    password_protected = False

    # 안전한 tab 파싱
    try:
        tab_info = json.loads(tab) if tab and tab.strip() not in ["", "null", "undefined"] else {}
    except json.JSONDecodeError:
        tab_info = {}

    # 시스템·접속 정보 수집
    # client_host = request.client.host if request.client else "unknown"
    # form = await request.form()
    # client_ip = form.get("client_ip") or request.client.host
    try:
        hostname = socket.gethostname()
        client_ip = socket.gethostbyname(hostname)  # 사설 IP
    except Exception:
        client_ip = "unknown"
    computer_name = socket.gethostname()
    os_info = f"{platform.system()} {platform.release()}"
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # AI 서비스 종류 추출 (예: ChatGPT, Claude 등)
    ai_service = None
    if isinstance(tab_info, dict):
        ai_service = tab_info.get("service") or tab_info.get("site") or "unknown"

    for uploaded_file in Files:
        filename = uploaded_file.filename
        extension = filename.split('.')[-1].lower()
        try:
            content = await uploaded_file.read()
            meta_info = {
                "agent_id": agent_id,
                "source_url": source_url,
                "tab": tab_info,
                "ip": client_ip,
                "computer_name": computer_name,
                "os_info": os_info,
                "ai_service": ai_service,
                "timestamp": current_time
                }
            detected, parsed_Text, backend_status, face_path = handle_input_raw(content, extension, meta_info)
            if backend_status == "no_text":
                results[filename] = {"status": "OCR 실패 또는 텍스트 없음"}
            elif backend_status == "no_detection":
                results[filename] = {"status": "탐지된 민감정보 없음"}
            elif backend_status == "face_only":
                results[filename] = {
                    "status": "얼굴 탐지됨",
                    "detected": detected,
                    "face_image_path": face_path
                    }
            elif backend_status == "send_fail":
                results[filename] = {
                    "status": "탐지됨",
                    "detected": detected,
                    # "parsed_Text": parsed_Text,
                    "backend_transmission": "실패"
                    }
                if face_path:  # 문서 내부 얼굴 감지 시에도 표시
                    results[filename]["face_image_path"] = face_path
            elif backend_status == "sent_ok":
                results[filename] = {
                    "status": "탐지됨",
                    "detected": detected,
                    # "parsed_Text": parsed_Text,
                    "backend_transmission": "성공"
                    }
                if face_path:  # 문서 내부 얼굴 감지 시에도 표시
                    results[filename]["face_image_path"] = face_path
            else:
                results[filename] = {"status": "처리 실패 또는 비정상 응답"} # 예외적 반환 형태(백엔드 로직 불일치) 방어
            # if detected:
            #     results[filename] = {
            #         "status": "처리 완료",
            #         "detected": detected,
            #         "parsed_Text": parsed_Text,
            #         "backend_transmission": "성공" if backend_status else "실패"
            #     }
            # else:
            #     results[filename] = {"status": "탐지된 민감정보 없음"}
        except ValueError as ve:
            # results[filename] = {"status": "에러", "message": str(ve)}
            # password_protected = True
                msg = str(ve)
                if "암호" in msg or "password" in msg.lower():
                    results[filename] = {"status": "에러", "message": "암호로 보호된 파일입니다."}
                else:
                    results[filename] = {"status": "에러", "message": msg}
        except Exception as e:
            results[filename] = {"status": "에러", "message": f"처리 실패: {str(e)}"}

    # 탐지 결과 요약
    # detected_types = []
    detected_type_counts = Counter()
    validation_card_total = validation_card_valid = validation_card_invalid = 0
    validation_ssn_total = validation_ssn_valid = validation_ssn_invalid = 0
    for v in results.values():
        if isinstance(v, dict) and "detected" in v:
            for d in v["detected"]:
                t = d.get("type")
                st = d.get("status", "").lower()
                if t == "card":
                    validation_card_total += 1
                    if st == "valid":
                        validation_card_valid += 1
                    else:
                        validation_card_invalid += 1
                elif t == "ssn":
                    validation_ssn_total += 1
                    if st == "valid":
                        validation_ssn_valid += 1
                    else:
                        validation_ssn_invalid += 1
                dtype = d.get("type")
                if dtype:
                    detected_type_counts[dtype] += 1
                # if dtype and dtype not in detected_types:
                #     detected_types.append(dtype)
    validation_summary = {
        "card": {
        "total": validation_card_total,
        "valid": validation_card_valid,
        "invalid": validation_card_invalid
        },
    "ssn": {
        "total": validation_ssn_total,
        "valid": validation_ssn_valid,
        "invalid": validation_ssn_invalid
        }
    }

    # 메타데이터 통합
    results["_meta"] = {
        "agent_id": agent_id,
        "source_url": source_url,
        "tab": tab_info,
        "ip": client_ip,
        "computer_name": computer_name,
        "os_info": os_info,
        "ai_service": ai_service,
        "timestamp": current_time,
        "filename": filename,
        "detected_summary": dict(detected_type_counts), # detected_types
        "validation_summary": validation_summary 
    }

    return JSONResponse(
        content={"result_summary": results}, status_code=200)

@app.post("/mask-text/")
async def mask_text(
    request: Request,
    text: str = Form(...),
    tab: str | None = Form(None),
    agent_id: str | None = Form(None),
    source_url: str | None = Form(None)
    ):
    try:
        tab_info = json.loads(tab) if tab else {}
        ua = tab_info.get("ua") if tab_info else None
        # client_host = request.client.host if request.client else "unknown"
        # form = await request.form()
        # client_ip = form.get("client_ip") or request.client.host
        try:
            hostname = socket.gethostname()
            client_ip = socket.gethostbyname(hostname)  # 사설 IP
        except Exception:
            client_ip = "unknown"
        computer_name = socket.gethostname()
        os_info = f"{platform.system()} {platform.release()}"
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ai_service = None
        if isinstance(tab_info, dict):
            ai_service = tab_info.get("service") or tab_info.get("site") or "unknown"

        print("[INFO] 텍스트 입력으로 감지됨")

        detected = detect_by_regex(text) + detect_by_ner(text)
        detected_types = list({d.get("type") for d in detected if d.get("type")})
        detected_type_counts = Counter([d.get("type") for d in detected if d.get("type")])
        card_total = card_valid = card_invalid = 0
        ssn_total = ssn_valid = ssn_invalid = 0
        for d in detected:
            t = d.get("type")
            st = d.get("status", "").lower()
            if t == "card":
                card_total += 1
                if st == "valid":
                    card_valid += 1
                else:
                    card_invalid += 1
            elif t == "ssn":
                ssn_total += 1
                if st == "valid":
                    ssn_valid += 1
                else:
                    ssn_invalid += 1
        
        validation_summary = {
            "card": {"total": card_total, "valid": card_valid, "invalid": card_invalid},
            "ssn":  {"total": ssn_total,  "valid": ssn_valid,  "invalid": ssn_invalid}
            }

        if not detected:
            return JSONResponse(
                content={"result_summary": {
                    "입력 텍스트": {"status": "탐지된 민감정보 없음"}
                }},
                status_code=200
            )
        
        ok = send_to_backend(json.dumps(detected, ensure_ascii=False).encode("utf-8"))

        result_summary = {
            "입력 텍스트": {
                "status": "처리 완료",
                "detected": detected,
                # "text": text,
                "backend_transmission": "성공" if ok else "실패"
            }
        }
        result_summary["_meta"] = {
            "agent_id": agent_id,
            "source_url": source_url,
            "tab": tab_info,
            "ip": client_ip,
            "computer_name": computer_name,
            "os_info": os_info,
            "ai_service": ai_service,
            "timestamp": current_time,
            "detected_summary": dict(detected_type_counts), # detected_types
            "validation_summary": validation_summary,
            }

        return JSONResponse(content={"result_summary": result_summary}, status_code=200)

    except Exception as e:
        return JSONResponse(
            content={"result_summary": {
                "입력 텍스트": {"status": "에러", "message": str(e)}
            }},
            status_code=500
        )

if __name__ == "__main__":
    uvicorn.run(LocalServer.app, host="127.0.0.1", port=8000, reload=False)
    # LocalServer.py
    # 파일 안의 app 객체를 실행
    # 로컬호스트 기준으로만 열림 (외부 노출 X)
    # 포트 8000 사용
    # 파일 수정되면 자동 재시작 (개발 편의성)