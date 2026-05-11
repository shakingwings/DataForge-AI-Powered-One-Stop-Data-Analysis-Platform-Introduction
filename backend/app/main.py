import time
import traceback
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import data, analysis, visualization, chat, export, cleaning
from app.api.history import router as history_router
from app.config import settings
from app.core.database import set_db_path, init_db
from app.core.logger import setup_logging, get_logger

setup_logging()
logger = get_logger("main")

DB_DIR = Path(__file__).parent.parent / "data"
DB_DIR.mkdir(exist_ok=True)
set_db_path(str(DB_DIR / "app.db"))

app = FastAPI(title="DataForge-AI-Powered-One-Stop-Data-Analysis-Platform-Introduction", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = round((time.time() - start) * 1000, 1)
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({elapsed}ms)")
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.method} {request.url.path}: {exc}")
    logger.debug(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"error": "服务器内部错误，请稍后重试", "detail": str(exc)},
    )


@app.on_event("startup")
async def startup():
    await init_db()
    logger.info("数据库初始化完成")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")


app.include_router(data.router)
app.include_router(analysis.router)
app.include_router(visualization.router)
app.include_router(chat.router)
app.include_router(export.router)
app.include_router(history_router)
app.include_router(cleaning.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "llm_provider": settings.LLM_PROVIDER}


@app.get("/api/config")
async def get_config():
    return {
        "llm_provider": settings.LLM_PROVIDER,
        "openai_model": settings.OPENAI_MODEL,
        "ollama_model": settings.OLLAMA_MODEL,
        "ollama_url": settings.OLLAMA_BASE_URL,
    }


@app.post("/api/config")
async def update_config(body: dict):
    if "llm_provider" in body:
        settings.LLM_PROVIDER = body["llm_provider"]
    if "openai_api_key" in body:
        settings.OPENAI_API_KEY = body["openai_api_key"]
    if "openai_base_url" in body:
        settings.OPENAI_BASE_URL = body["openai_base_url"]
    if "openai_model" in body:
        settings.OPENAI_MODEL = body["openai_model"]
    if "ollama_model" in body:
        settings.OLLAMA_MODEL = body["ollama_model"]
    if "ollama_url" in body:
        settings.OLLAMA_BASE_URL = body["ollama_url"]
    logger.info(f"配置已更新: provider={settings.LLM_PROVIDER}")
    return {"status": "ok"}
