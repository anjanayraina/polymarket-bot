import asyncio
import json
import requests
import websockets
from datetime import datetime
from typing import List

from helpers.logger import logger
from helpers.constants import (
    BINANCE_WS_URL_TEMPLATE,
    BINANCE_FUNDING_URL_TEMPLATE,
    COINGLASS_LIQUIDATION_URL,
    DEFAULT_CRYPTO_SYMBOL,
    DEFAULT_BINANCE_SYMBOL,
    DEFAULT_WS_SYMBOL
)
from models.market import (
    MarketSignals, 
    OrderBookWall, 
    OrderBookWalls, 
    FundingInfo, 
    LiquidationData
)

class DataStreamer:
    def __init__(self, coinglass_api_key: str = None):
        self.coinglass_api_key = coinglass_api_key
        
        self.binance_depth_bids: List[OrderBookWall] = []
        self.binance_depth_asks: List[OrderBookWall] = []

    async def start_binance_websocket(self, symbol: str = DEFAULT_WS_SYMBOL):
        """Streams Binance depth data via WebSocket."""
        url = BINANCE_WS_URL_TEMPLATE.format(symbol=symbol.lower())
        while True:
            try:
                async with websockets.connect(url) as websocket:
                    logger.info(f"Connected to Binance WebSocket for {symbol}")
                    while True:
                        message = await websocket.recv()
                        data = json.loads(message)
                        self.binance_depth_bids = [OrderBookWall(price=float(p), volume=float(q)) for p, q in data["bids"]]
                        self.binance_depth_asks = [OrderBookWall(price=float(p), volume=float(q)) for p, q in data["asks"]]
            except Exception as e:
                logger.error(f"Binance WebSocket error: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)

    def get_order_book_walls(self, current_price: float, range_pct: float = 0.005) -> OrderBookWalls:
        """Identifies Bid and Ask walls within a percentage range of current price."""
        lower_bound = current_price * (1 - range_pct)
        upper_bound = current_price * (1 + range_pct)
        
        bid_walls = [b for b in self.binance_depth_bids if b.price >= lower_bound]
        ask_walls = [a for a in self.binance_depth_asks if a.price <= upper_bound]
        
        bid_walls.sort(key=lambda x: x.volume, reverse=True)
        ask_walls.sort(key=lambda x: x.volume, reverse=True)
        
        return OrderBookWalls(
            top_bid_walls=bid_walls[:3],
            top_ask_walls=ask_walls[:3]
        )

    def get_binance_funding_rate(self, symbol: str = DEFAULT_BINANCE_SYMBOL) -> FundingInfo:
        """Fetches current and historical funding rate for delta calculation."""
        try:
            url = BINANCE_FUNDING_URL_TEMPLATE.format(symbol=symbol)
            response = requests.get(url).json()
            current_rate = float(response.get("lastFundingRate", 0))
            
            return FundingInfo(
                current_funding_rate=current_rate,
                funding_rate_1h_avg=current_rate
            )
        except Exception as e:
            logger.error(f"Error fetching Binance funding rate: {e}")
            return FundingInfo(current_funding_rate=0.0, funding_rate_1h_avg=0.0)

    def get_coinglass_liquidations(self, symbol: str = DEFAULT_CRYPTO_SYMBOL) -> LiquidationData:
        """Fetches liquidation data from Coinglass."""
        if not self.coinglass_api_key:
            return LiquidationData(short_vol=0, long_vol=0)
        
        try:
            url = f"{COINGLASS_LIQUIDATION_URL}_info?symbol={symbol}&time_type=h1"
            headers = {"accept": "application/json", "coinglassApi": self.coinglass_api_key}
            response = requests.get(url, headers=headers).json()
            
            if response.get("code") == "0" and response.get("data"):
                data = response["data"][0]
                return LiquidationData(
                    short_vol=float(data.get("shortVolUsd", 0)),
                    long_vol=float(data.get("longVolUsd", 0))
                )
        except Exception as e:
            logger.error(f"Error fetching Coinglass liquidations: {e}")
            
        return LiquidationData(short_vol=0, long_vol=0)

    def get_all_signals(self, current_btc_price: float) -> MarketSignals:
        """Aggregates all signals for the AI Brain."""
        return MarketSignals(
            timestamp=datetime.now(),
            btc_price=current_btc_price,
            order_book=self.get_order_book_walls(current_btc_price),
            funding=self.get_binance_funding_rate(),
            liquidations=self.get_coinglass_liquidations()
        )
