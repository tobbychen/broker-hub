"""Pydantic schemas for API request/response models."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PositionSchema(BaseModel):
    id: int
    asset_class: str
    symbol: str
    exchange: Optional[str] = ""
    quantity: float
    avg_cost: float
    currency: str = "CNY"
    notes: Optional[str] = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AllocationItem(BaseModel):
    cost: float
    pct: float


class PortfolioSummarySchema(BaseModel):
    total_value: float
    allocation: dict[str, AllocationItem]
    by_class: list[dict]

    class Config:
        from_attributes = True


class WatchlistItemSchema(BaseModel):
    id: int
    asset_class: str
    symbol: str
    exchange: Optional[str] = ""
    notes: Optional[str] = ""
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DecisionCardSchema(BaseModel):
    id: int
    decision_type: str
    asset_class: str
    symbol: str
    exchange: Optional[str] = ""
    quantity: Optional[float] = None
    action_price: Optional[float] = None
    confidence: Optional[float] = None
    reasoning: Optional[str] = ""
    risk_level: Optional[str] = ""
    status: str = "pending"
    timeout_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DecisionResponseSchema(BaseModel):
    approved: bool
    message: Optional[str] = ""


class ChatMessageSchema(BaseModel):
    id: int
    decision_id: int
    role: str
    content: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatSendSchema(BaseModel):
    decision_id: int
    message: str


class AgentStatusSchema(BaseModel):
    agent_name: str
    status: str
    last_check: Optional[datetime] = None
    error: Optional[str] = None
    event_count_today: int = 0

    class Config:
        from_attributes = True
