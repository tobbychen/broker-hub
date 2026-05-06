"""Decision (pending trade recommendations) API endpoints."""
from fastapi import APIRouter, HTTPException
from ..database import get_pending_decisions, resolve_decision
from ..models.schemas import DecisionCardSchema, DecisionResponseSchema

router = APIRouter()


@router.get("/pending", response_model=list[DecisionCardSchema])
async def list_pending():
    return await get_pending_decisions()


@router.post("/{decision_id}/resolve")
async def resolve(id: int, response: DecisionResponseSchema):
    if response.approved not in (True, False):
        raise HTTPException(status_code=400, detail="approved must be true or false")
    await resolve_decision(id, response.approved)
    return {"id": id, "status": "approved" if response.approved else "rejected"}
