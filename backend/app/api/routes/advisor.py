import logging
import uuid
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse

from ...schemas.financial import AdvisorChatRequest, AdvisorChatResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/advisor", tags=["AI Advisor"])


@router.post("/chat", response_model=AdvisorChatResponse)
async def advisor_chat(request: AdvisorChatRequest):
    """Non-streaming AI advisor response."""
    from ...services.advisor.advisor_service import get_advisor_response
    return await get_advisor_response(request)


@router.post("/chat/stream")
async def advisor_chat_stream(request: AdvisorChatRequest):
    """
    Streaming AI advisor response via Server-Sent Events.

    Yields JSON events:
      - {"token": "word"} for each word
      - {"status": "message"} for progressive status updates during tool calls
      - {"error": "message"} on error
      - [DONE] when complete
    """
    from ...services.advisor.advisor_service import stream_advisor_response

    return StreamingResponse(
        stream_advisor_response(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
