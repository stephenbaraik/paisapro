from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from ...schemas.financial import AdvisorChatRequest, AdvisorChatResponse
from ...services.ai_advisor import get_advisor_response, stream_advisor_response

router = APIRouter(prefix="/advisor", tags=["AI Advisor"])


@router.post("/chat", response_model=AdvisorChatResponse)
async def chat(req: AdvisorChatRequest):
    """Non-streaming fallback."""
    return await get_advisor_response(req)


@router.post("/chat/stream")
async def chat_stream(req: AdvisorChatRequest):
    """Streaming endpoint — returns SSE tokens."""
    return StreamingResponse(
        stream_advisor_response(req),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
