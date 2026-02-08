from pydantic import BaseModel
from typing import List, Optional

class PolymarketOdds(BaseModel):
    yes_price: float
    no_price: float

class MarketInfo(BaseModel):
    condition_id: str
    question: str
    yes_token: str
    no_token: str
    active: bool

class ClobToken(BaseModel):
    model_config = {"extra": "ignore"}
    token_id: str
    outcome: str

class ClobMarket(BaseModel):
    model_config = {"extra": "ignore"}
    
    conditionId: str
    question: Optional[str] = None
    title: Optional[str] = None
    active: bool = False
    closed: bool = False
    accepting_orders: bool = False
    tokens: Optional[List[ClobToken]] = None
    clobTokenIds: Optional[List[str]] = None
