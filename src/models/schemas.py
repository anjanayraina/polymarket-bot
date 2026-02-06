from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class OrderBookWall(BaseModel):
    price: float
    volume: float

class OrderBookWalls(BaseModel):
    top_bid_walls: List[OrderBookWall]
    top_ask_walls: List[OrderBookWall]

class FundingInfo(BaseModel):
    current_funding_rate: float
    funding_rate_1h_avg: float

class LiquidationData(BaseModel):
    short_vol: float
    long_vol: float

class NewsSentiment(BaseModel):
    sentiment_score: float
    headlines: List[str]

class MarketSignals(BaseModel):
    timestamp: datetime
    btc_price: float
    order_book: OrderBookWalls
    funding: Optional[FundingInfo]
    liquidations: LiquidationData
    news: NewsSentiment

class PolymarketOdds(BaseModel):
    yes_price: float
    no_price: float

class AIDecision(BaseModel):
    action: str = Field(..., pattern="^(BUY_UP|BUY_DOWN|WAIT)$")
    confidence: float
    reasoning: str

class MarketInfo(BaseModel):
    condition_id: str
    question: str
    yes_token: str
    no_token: str
    active: bool
