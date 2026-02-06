import asyncio
import json
import logging
import requests
import websockets
from datetime import datetime, timedelta

class DataStreamer:
    def __init__(self, binance_api_key=None, coinglass_api_key=None, cryptopanic_api_key=None):
        self.binance_api_key = binance_api_key
        self.coinglass_api_key = coinglass_api_key
        self.cryptopanic_api_key = cryptopanic_api_key
        
        self.binance_depth = {"bids": [], "asks": []}
        self.logger = logging.getLogger("DataStreamer")

    async def start_binance_websocket(self, symbol="btcusdt"):
        """Streams Binance depth data via WebSocket."""
        url = f"wss://stream.binance.com:9443/ws/{symbol.lower()}@depth20@100ms"
        while True:
            try:
                async with websockets.connect(url) as websocket:
                    self.logger.info(f"Connected to Binance WebSocket for {symbol}")
                    while True:
                        message = await websocket.recv()
                        data = json.loads(message)
                        self.binance_depth["bids"] = [[float(p), float(q)] for p, q in data["bids"]]
                        self.binance_depth["asks"] = [[float(p), float(q)] for p, q in data["asks"]]
            except Exception as e:
                self.logger.error(f"Binance WebSocket error: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)

    def get_order_book_walls(self, current_price, range_pct=0.005):
        """Identifies Bid and Ask walls within a percentage range of current price."""
        lower_bound = current_price * (1 - range_pct)
        upper_bound = current_price * (1 + range_pct)
        
        bid_walls = [b for b in self.binance_depth["bids"] if b[0] >= lower_bound]
        ask_walls = [a for a in self.binance_depth["asks"] if a[0] <= upper_bound]
        
        # Sort by volume to find the biggest walls
        bid_walls.sort(key=lambda x: x[1], reverse=True)
        ask_walls.sort(key=lambda x: x[1], reverse=True)
        
        return {
            "top_bid_walls": bid_walls[:3],
            "top_ask_walls": ask_walls[:3]
        }

    def get_binance_funding_rate(self, symbol="BTCUSDT"):
        """Fetches current and historical funding rate for delta calculation."""
        try:
            # Current funding rate
            url = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}"
            response = requests.get(url).json()
            current_rate = float(response.get("lastFundingRate", 0))
            
            # Simplified average (in a real bot, we'd store history or fetch historical endpoint)
            # For brevity, let's assume we just fetch the current rate for now.
            return {
                "current_funding_rate": current_rate,
                "funding_rate_1h_avg": current_rate # Placeholder for delta
            }
        except Exception as e:
            self.logger.error(f"Error fetching Binance funding rate: {e}")
            return None

    def get_coinglass_liquidations(self, symbol="BTC"):
        """Fetches liquidation data from Coinglass."""
        if not self.coinglass_api_key:
            return {"short_vol": 0, "long_vol": 0}
        
        try:
            url = f"https://open-api.coinglass.com/public/v2/liquidation_info?symbol={symbol}&time_type=h1"
            headers = {"accept": "application/json", "coinglassApi": self.coinglass_api_key}
            response = requests.get(url, headers=headers).json()
            
            if response.get("code") == "0" and response.get("data"):
                data = response["data"][0]
                return {
                    "short_vol": data.get("shortVolUsd", 0),
                    "long_vol": data.get("longVolUsd", 0)
                }
        except Exception as e:
            self.logger.error(f"Error fetching Coinglass liquidations: {e}")
            
        return {"short_vol": 0, "long_vol": 0}

    def get_cryptopanic_sentiment(self):
        """Fetches latest news sentiment from CryptoPanic."""
        if not self.cryptopanic_api_key:
            return {"sentiment_score": 5, "headlines": []}
            
        try:
            url = f"https://cryptopanic.com/api/v1/posts/?auth_token={self.cryptopanic_api_key}&currencies=BTC"
            response = requests.get(url).json()
            
            posts = response.get("results", [])[:3]
            headlines = [p.get("title") for p in posts]
            
            # Simple sentiment proxy (real sentiment would need another LLM or NLP)
            # CryptoPanic provides 'votes' for positive/negative.
            pos_votes = sum(p.get("votes", {}).get("positive", 0) for p in posts)
            neg_votes = sum(p.get("votes", {}).get("negative", 0) for p in posts)
            
            total = pos_votes + neg_votes
            sentiment_score = 5
            if total > 0:
                sentiment_score = (pos_votes / total) * 10
                
            return {
                "sentiment_score": round(sentiment_score, 2),
                "headlines": headlines
            }
        except Exception as e:
            self.logger.error(f"Error fetching CryptoPanic sentiment: {e}")
            
        return {"sentiment_score": 5, "headlines": []}

    def get_all_signals(self, current_btc_price):
        """Aggregates all signals for the AI Brain."""
        walls = self.get_order_book_walls(current_btc_price)
        funding = self.get_binance_funding_rate()
        liquidations = self.get_coinglass_liquidations()
        news = self.get_cryptopanic_sentiment()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "btc_price": current_btc_price,
            "order_book": walls,
            "funding": funding,
            "liquidations": liquidations,
            "news": news
        }
