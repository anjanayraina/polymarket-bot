import asyncio
import logging
import sys

# Update imports to new structure
from services.data_streamer import DataStreamer
from services.brain import Brain
from services.trader import PolymarketTrader
from helpers.constants import AI_CONFIDENCE_THRESHOLD, DEFAULT_TRADE_AMOUNT
from helpers.config import settings
from models.polymarket import MarketInfo
from models.ai import AIDecision

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Main")

async def main():
    # Environment Variables from Pydantic-like settings (though settings itself info/Config is a class)
    PK = settings.POLYGON_PRIVATE_KEY
    CLOB_API_KEY = settings.CLOB_API_KEY
    CLOB_SECRET = settings.CLOB_SECRET
    CLOB_PASSPHRASE = settings.CLOB_PASSPHRASE
    OPENAI_KEY = settings.OPENAI_API_KEY
    COINGLASS_KEY = settings.COINGLASS_API_KEY
    CRYPTOPANIC_KEY = settings.CRYPTOPANIC_API_KEY

    if not all([PK, CLOB_API_KEY, OPENAI_KEY]):
        logger.error("Missing critical environment variables. Check your config in src/resources/.")
        return

    # Initialize Components
    streamer = DataStreamer(
        coinglass_api_key=COINGLASS_KEY,
        cryptopanic_api_key=CRYPTOPANIC_KEY
    )
    brain = Brain(api_key=OPENAI_KEY)
    trader = PolymarketTrader(PK, CLOB_API_KEY, CLOB_SECRET, CLOB_PASSPHRASE)

    # Start Binance WebSocket in background
    asyncio.create_task(streamer.start_binance_websocket())

    # Market Discovery
    logger.info("Discovering active BTC 15-minute markets...")
    btc_markets = trader.find_active_btc_markets()
    market: MarketInfo = btc_markets[0] if btc_markets else None
    
    if market:
        logger.info(f"Connected to market: {market.question}")
    else:
        logger.warning("No active BTC 15-minute markets found. Will retry in loop.")

    while True:
        try:
            # Refresh market if none active
            if not market:
                btc_markets = trader.find_active_btc_markets()
                if btc_markets:
                    market = btc_markets[0]
                    logger.info(f"Market found: {market.question}")
                else:
                    await asyncio.sleep(60)
                    continue

            # 1. Get current BTC price
            if not streamer.binance_depth_bids:
                logger.warning("Waiting for Binance depth data...")
                await asyncio.sleep(5)
                continue
                
            current_btc_price = streamer.binance_depth_bids[0].price
            
            # 2. Get Signals (Returns MarketSignals Pydantic model)
            signals = streamer.get_all_signals(current_btc_price)
            
            # 3. Get Polymarket Odds (Returns PolymarketOdds Pydantic model)
            odds = trader.get_market_odds(market.yes_token)
            
            # 4. AI Decision (Returns AIDecision Pydantic model)
            decision: AIDecision = brain.analyze_market(signals, odds)
            
            if decision.confidence > AI_CONFIDENCE_THRESHOLD:
                logger.info(f"SIGNAL DETECTED: {decision.action} | Confidence: {decision.confidence}")
                logger.debug(f"Reasoning: {decision.reasoning}")
                
                if decision.action == "BUY_UP":
                    trader.execute_trade(market.yes_token, DEFAULT_TRADE_AMOUNT, odds.yes_price + 0.01)
                elif decision.action == "BUY_DOWN":
                    trader.execute_trade(market.no_token, DEFAULT_TRADE_AMOUNT, odds.no_price + 0.01)
                
            # 5. Auto Merging
            trader.merge_shares(market.condition_id)

        except Exception as e:
            logger.error(f"Loop error: {e}")
            
        await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
