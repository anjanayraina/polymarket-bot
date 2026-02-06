import asyncio
from helpers.logger import logger
from helpers.service_locator import service_locator
from helpers.constants import AI_CONFIDENCE_THRESHOLD, DEFAULT_TRADE_AMOUNT
from services.data_streamer import DataStreamer
from services.brain import Brain
from services.trader import PolymarketTrader
from models.polymarket import MarketInfo
from models.ai import AIDecision

class TradingEngine:
    def __init__(self):
        self.streamer: DataStreamer = None
        self.brain: Brain = None
        self.trader: PolymarketTrader = None
        self.market: MarketInfo = None

    def _resolve_dependencies(self):
        self.streamer = service_locator.get(DataStreamer)
        self.brain = service_locator.get(Brain)
        self.trader = service_locator.get(PolymarketTrader)

    async def run(self):
        """Starts the core trading workflow."""
        self._resolve_dependencies()
        logger.info("Trading Engine started. Initializing data streams...")
        
        # Start background tasks
        asyncio.create_task(self.streamer.start_binance_websocket())

        # Initial Market Discovery
        logger.info("Discovering active BTC 15-minute markets...")
        btc_markets = self.trader.find_active_btc_markets()
        self.market = btc_markets[0] if btc_markets else None
        
        if self.market:
            logger.info(f"Connected to market: {self.market.question}")
        else:
            logger.warning("No active BTC 15-minute markets found. Will retry in loop.")

        # Trading Loop
        while True:
            try:
                if not self.market:
                    btc_markets = self.trader.find_active_btc_markets()
                    if btc_markets:
                        self.market = btc_markets[0]
                        logger.info(f"Market found: {self.market.question}")
                    else:
                        await asyncio.sleep(60)
                        continue

                if not self.streamer.binance_depth_bids:
                    logger.warning("Waiting for Binance depth data...")
                    await asyncio.sleep(5)
                    continue
                    
                current_btc_price = self.streamer.binance_depth_bids[0].price
                signals = self.streamer.get_all_signals(current_btc_price)
                odds = self.trader.get_market_odds(self.market.yes_token)
                
                decision: AIDecision = self.brain.analyze_market(signals, odds)
                
                if decision.confidence > AI_CONFIDENCE_THRESHOLD:
                    logger.info(f"SIGNAL DETECTED: {decision.action} | Confidence: {decision.confidence}")
                    logger.debug(f"Reasoning: {decision.reasoning}")
                    
                    if decision.action == "BUY_UP":
                        self.trader.execute_trade(self.market.yes_token, DEFAULT_TRADE_AMOUNT, odds.yes_price + 0.01)
                    elif decision.action == "BUY_DOWN":
                        self.trader.execute_trade(self.market.no_token, DEFAULT_TRADE_AMOUNT, odds.no_price + 0.01)
                    
                self.trader.merge_shares(self.market.condition_id)

            except Exception as e:
                logger.error(f"Engine loop error: {e}")
                
            await asyncio.sleep(10)
