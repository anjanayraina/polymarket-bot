from pydantic import BaseModel, Field

class AIDecision(BaseModel):
    action: str = Field(..., pattern="^(BUY_UP|BUY_DOWN|WAIT)$")
    confidence: float
    reasoning: str
