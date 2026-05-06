"""Chat API endpoints."""
from fastapi import APIRouter
from ..database import add_chat_message, get_chat_history
from ..models.schemas import ChatMessageSchema, ChatSendSchema

router = APIRouter()


@router.get("/{decision_id}", response_model=list[ChatMessageSchema])
async def get_chat(decision_id: int):
    return await get_chat_history(decision_id)


@router.post("/send")
async def send_message(payload: ChatSendSchema):
    await add_chat_message(payload.decision_id, "human", payload.message)
    return {"ok": True}
