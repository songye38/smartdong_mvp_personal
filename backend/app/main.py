from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.scrape import router as scrape_router
from app.routers.script import router as script_router
from app.routers.tts import router as tts_router
from app.routers.edit_plan import router as edit_plan_router


# 1. FastAPI 앱 생성
app = FastAPI(
    title="Smartdong MVP API",
    description="네이버 블로그 기반 쇼츠 자동 제작 API",
    version="0.1.0",
)


# 2. CORS 설정
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 3. 라우터 등록
app.include_router(scrape_router)
app.include_router(script_router)
app.include_router(tts_router)
app.include_router(edit_plan_router)

# 4. 기본 API
@app.get("/")
def root():
    return {
        "message": "Smartdong API is running!"
    }


# 5. 서버 상태 확인
@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "smartdong-backend",
        "version": "0.1.0",
    }

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app.mount(
    "/outputs",
    StaticFiles(directory=str(OUTPUT_DIR)),
    name="outputs",
)