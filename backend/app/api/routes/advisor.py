from fastapi import APIRouter
from ...schemas.financial import AdvisorChatRequest, AdvisorChatResponse
from ...services.ai_advisor import get_advisor_response

router = APIRouter(prefix="/advisor", tags=["AI Advisor"])


@router.post("/chat", response_model=AdvisorChatResponse)
async def chat(req: AdvisorChatRequest):
    """Conversational AI investment advisor powered by Claude."""
    return await get_advisor_response(req)
