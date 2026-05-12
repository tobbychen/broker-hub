"""Decision (pending trade recommendations) API endpoints."""
from fastapi import APIRouter, HTTPException
from ..database import get_pending_decisions, resolve_decision
from ..models.schemas import DecisionCardSchema, DecisionResponseSchema

router = APIRouter()


@router.get("/pending", response_model=list[DecisionCardSchema])
async def list_pending():
    return await get_pending_decisions()


@router.post("/{decision_id}/resolve")
async def resolve(decision_id: int, response: DecisionResponseSchema):
    """Resolve a pending decision by ID."""
    if response.approved not in (True, False):
        raise HTTPException(status_code=400, detail="approved must be true or false")
    await resolve_decision(decision_id, response.approved)
    return {"id": decision_id, "status": "approved" if response.approved else "rejected"}
