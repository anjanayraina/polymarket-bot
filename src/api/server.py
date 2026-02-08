from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import asyncio

from helpers.service_locator import service_locator
from services.trading_engine import TradingEngine
from services.data_streamer import DataStreamer
from services.trader import PolymarketTrader

app = FastAPI(title="Polymarket Signal Sniper API")

class StatusResponse(BaseModel):
    btc_price: float
    market_question: Optional[str]
    latest_brief: Optional[dict]

class CommandRequest(BaseModel):
    command: str # 'CONTINUE' or 'SKIP'

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/signals")
async def get_signals():
    engine = service_locator.get(TradingEngine)
    return {"signals": engine.latest_signals}

@app.get("/status", response_model=StatusResponse)
async def get_status():
    engine = service_locator.get(TradingEngine)
    if not engine.latest_signals:
        raise HTTPException(status_code=404, detail="No data received from streams yet.")
    
    return StatusResponse(
        btc_price=engine.latest_signals.btc_price,
        market_question=engine.market.question if engine.market else "N/A",
        latest_brief=engine.latest_brief
    )

@app.get("/suggestions")
async def get_suggestions():
    """Reads the last 10 entries from suggestions.log"""
    try:
        with open("suggestions.log", "r") as f:
            lines = f.readlines()
            return {"logs": lines[-50:]} # Return last 50 lines
    except FileNotFoundError:
        return {"logs": []}

@app.post("/trade/confirm")
async def confirm_trade(request: CommandRequest):
    engine = service_locator.get(TradingEngine)
    if not engine.latest_brief:
        raise HTTPException(status_code=400, detail="No pending trade brief to confirm.")
    
    await engine.confirmation_queue.put(request.command)
    return {"message": f"Command '{request.command}' sent to engine."}

@app.get("/trade/latest")
async def get_latest_brief():
    engine = service_locator.get(TradingEngine)
    return {"brief": engine.latest_brief}

@app.get("/markets")
async def list_markets():
    engine = service_locator.get(TradingEngine)
    trader = service_locator.get(PolymarketTrader)
    markets = trader.find_active_btc_markets()
    return {"active_markets": markets}

@app.post("/merge")
async def merge_shares():
    engine = service_locator.get(TradingEngine)
    if not engine.market:
        raise HTTPException(status_code=400, detail="No active market connected.")
    
    resp = engine.trader.merge_shares(engine.market.condition_id)
    return {"status": "success", "response": resp}
