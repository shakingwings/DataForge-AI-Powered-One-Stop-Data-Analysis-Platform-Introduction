import json

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.core.agent import process_message, process_message_stream
from app.core.database import save_message
from app.core.logger import get_logger
from app.models.schemas import ChatRequest, ChatResponse

logger = get_logger("api.chat")
router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("")
async def chat(req: ChatRequest):
    logger.info(f"对话请求: {req.message[:50]}... (session={req.session_id})")
    await save_message(req.session_id, "user", req.message)
    result = await process_message(req.message, req.session_id)
    await save_message(req.session_id, "assistant", result.get("reply", ""))
    return ChatResponse(**result)


@router.post("/stream")
async def chat_stream(req: ChatRequest):
    logger.info(f"流式对话请求: {req.message[:50]}... (session={req.session_id})")
    await save_message(req.session_id, "user", req.message)

    async def event_generator():
        full_reply = ""
        async for chunk in process_message_stream(req.message, req.session_id):
            if chunk["type"] == "text":
                full_reply += chunk.get("content", "")
            yield {"event": chunk["type"], "data": json.dumps(chunk["content"], ensure_ascii=False, default=str)}
        if full_reply:
            await save_message(req.session_id, "assistant", full_reply)

    return EventSourceResponse(event_generator())
