from pydantic import BaseModel

class PolymarketOdds(BaseModel):
    yes_price: float
    no_price: float

class MarketInfo(BaseModel):
    condition_id: str
    question: str
    yes_token: str
    no_token: str
    active: bool
