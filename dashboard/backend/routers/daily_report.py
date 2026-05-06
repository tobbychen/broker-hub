"""Daily report API endpoints."""
from datetime import date
from fastapi import APIRouter, BackgroundTasks
from ..database import get_daily_report

router = APIRouter()


@router.get("/{report_date}")
async def get_report(report_date: date):
    return await get_daily_report(report_date)


@router.get("/latest")
async def get_latest():
    return await get_daily_report(date.today())
