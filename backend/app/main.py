from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Smartdong MVP API",
    description="네이버 블로그 기반 쇼츠 자동 제작 API",
    version="0.1.0",
)

# React 개발 서버 주소
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


@app.get("/")
def root():
    return {
        "message": "Smartdong API is running!"
    }


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "smartdong-backend",
        "version": "0.1.0",
    }