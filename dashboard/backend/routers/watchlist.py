"""Watchlist management API."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..database import (
    upsert_watchlist_item,
    get_watchlist_items,
    delete_watchlist_item,
    get_watchlist_prices,
)

router = APIRouter()


class WatchlistItem(BaseModel):
    asset_class: str
    symbol: str
    exchange: str = ""
    notes: str = ""


class WatchlistPriceItem(BaseModel):
    id: int
    asset_class: str
    symbol: str
    exchange: str
    notes: str
    raw_data: str | None
    fetched_at: str | None


@router.get("/", response_model=list[WatchlistItem])
async def list_watchlist(asset_class: str = ""):
    """List all watchlist items, optionally filtered by asset class."""
    return await get_watchlist_items(asset_class or "")


@router.get("/prices", response_model=list[WatchlistPriceItem])
async def list_watchlist_prices(asset_class: str = ""):
    """List watchlist items with their latest cached prices."""
    return await get_watchlist_prices(asset_class or "")


@router.post("/", response_model=dict)
async def add_watchlist_item(item: WatchlistItem):
    """Add or update a watchlist item."""
    valid_classes = ("stock", "crypto", "forex", "options", "sports_card")
    if item.asset_class not in valid_classes:
        raise HTTPException(400, f"asset_class must be one of {valid_classes}")
    row_id = await upsert_watchlist_item(
        asset_class=item.asset_class,
        symbol=item.symbol,
        exchange=item.exchange,
        notes=item.notes,
    )
    return {"id": row_id, "added": True}


@router.delete("/{item_id}", response_model=dict)
async def remove_watchlist_item(item_id: int):
    """Remove a watchlist item by its ID."""
    deleted = await delete_watchlist_item(item_id)
    if not deleted:
        raise HTTPException(404, "Watchlist item not found")
    return {"deleted": True}
