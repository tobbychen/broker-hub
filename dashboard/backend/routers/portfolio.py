"""Portfolio API endpoints."""
from fastapi import APIRouter
from ..database import get_all_positions, get_portfolio_summary
from ..models.schemas import PositionSchema, PortfolioSummarySchema

router = APIRouter()


@router.get("/summary", response_model=PortfolioSummarySchema)
async def portfolio_summary():
    return await get_portfolio_summary()


@router.get("/positions", response_model=list[PositionSchema])
async def list_positions():
    return await get_all_positions()
