import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File

from app.config import settings
from app.core.database import save_session
from app.core.logger import get_logger
from app.models.schemas import session_store, DataUploadResponse
from app.services.data_processor import load_from_file, get_data_info, get_page

logger = get_logger("api.data")
router = APIRouter(prefix="/api/data", tags=["data"])

MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB


@router.post("/upload", response_model=DataUploadResponse)
async def upload_data(file: UploadFile = File(...), session_id: str = "default"):
    logger.info(f"上传文件: {file.filename} (session={session_id})")

    # Stream file to disk
    upload_dir = settings.UPLOAD_DIR
    upload_dir.mkdir(exist_ok=True)
    file_path = upload_dir / f"{session_id}_{file.filename}"

    total_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks
    with open(file_path, "wb") as f:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > MAX_FILE_SIZE:
                f.close()
                file_path.unlink(missing_ok=True)
                return {"error": f"文件过大，最大支持 500MB"}
            f.write(chunk)

    logger.info(f"文件已保存: {file_path} ({total_size / 1024 / 1024:.1f}MB)")

    # Load data
    try:
        df = load_from_file(file_path)
    except Exception as e:
        file_path.unlink(missing_ok=True)
        logger.error(f"数据加载失败: {e}")
        return {"error": f"数据加载失败: {str(e)}"}

    session = session_store.get(session_id)
    session["df"] = df
    session["filename"] = file.filename
    session["file_path"] = str(file_path)

    info = get_data_info(df)
    preview = get_page(df, page=1, page_size=50)

    await save_session(session_id, file.filename, info["rows"], info["columns"], info["column_names"])
    logger.info(f"数据加载完成: {info['rows']} 行 x {info['columns']} 列")

    return DataUploadResponse(
        filename=file.filename,
        rows=info["rows"],
        columns=info["columns"],
        column_names=info["column_names"],
        dtypes=info["dtypes"],
        preview=preview["data"],
    )


@router.get("/info")
async def get_info(session_id: str = "default"):
    session = session_store.get(session_id)
    df = session.get("df")
    if df is None:
        return {"error": "请先上传数据"}
    return get_data_info(df)


@router.get("/page")
async def get_page_data(session_id: str = "default", page: int = 1, page_size: int = 50):
    session = session_store.get(session_id)
    df = session.get("df")
    if df is None:
        return {"error": "请先上传数据"}
    return get_page(df, page=page, page_size=page_size)


@router.get("/preview")
async def preview_data(session_id: str = "default", rows: int = 20):
    session = session_store.get(session_id)
    df = session.get("df")
    if df is None:
        return {"error": "请先上传数据"}
    return {"data": df.head(rows).to_dict(orient="records"), "columns": list(df.columns)}


@router.delete("/clear")
async def clear_data(session_id: str = "default"):
    session = session_store.get(session_id)
    file_path = session.get("file_path")
    if file_path:
        Path(file_path).unlink(missing_ok=True)
    session_store.clear(session_id)
    logger.info(f"已清除会话数据: {session_id}")
    return {"message": "数据已清除"}
