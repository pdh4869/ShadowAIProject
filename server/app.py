from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import uvicorn

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# 임시 저장소 (실제로는 DB 사용 가능)
last_result = {}

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "result": last_result})

@app.post("/update_result/")
async def update_result(payload: dict):
    global last_result
    last_result = payload
    return {"status": "ok"}

if __name__ == "__main__":
    # 포트번호 9000으로 실행
    uvicorn.run(app, host="127.0.0.1", port=9000)
