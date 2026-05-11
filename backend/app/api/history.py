from fastapi import APIRouter

from app.core.database import get_sessions, get_session_detail, delete_session
from app.core.logger import get_logger

logger = get_logger("api.history")
router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/sessions")
async def list_sessions():
    sessions = await get_sessions()
    return {"sessions": sessions}


@router.get("/sessions/{session_id}")
async def session_detail(session_id: str):
    detail = await get_session_detail(session_id)
    if not detail:
        return {"error": "会话不存在"}
    return detail


@router.delete("/sessions/{session_id}")
async def remove_session(session_id: str):
    deleted = await delete_session(session_id)
    if deleted:
        logger.info(f"已删除会话: {session_id}")
        return {"message": "已删除"}
    return {"error": "会话不存在"}
