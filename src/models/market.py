from pydantic import BaseModel
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

class MarketSignals(BaseModel):
    timestamp: datetime
    btc_price: float
    order_book: OrderBookWalls
    funding: Optional[FundingInfo]
    liquidations: LiquidationData
