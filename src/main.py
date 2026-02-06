import asyncio
import json
import logging
import sys

from data_streamer import DataStreamer
from brain import Brain
from trader import PolymarketTrader

from config import settings

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Main")

async def main():
    # Environment Variables
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
    if not btc_markets:
        logger.warning("No active BTC 15-minute markets found. Will retry in loop.")
        market = None
    else:
        market = btc_markets[0]
        logger.info(f"Connected to market: {market.get('question')}")

    while True:
        try:
            # Refresh market if none found
            if not market:
                btc_markets = trader.find_active_btc_markets()
                if btc_markets:
                    market = btc_markets[0]
                    logger.info(f"Market found: {market.get('question')}")
                else:
                    await asyncio.sleep(60)
                    continue

            # 1. Get current BTC price
            if not streamer.binance_depth["bids"]:
                logger.warning("Waiting for Binance depth data...")
                await asyncio.sleep(5)
                continue
                
            current_btc_price = streamer.binance_depth["bids"][0][0]
            
            # 2. Get Signals
            signals = streamer.get_all_signals(current_btc_price)
            
            # 3. Get Polymarket Odds
            tokens = json.loads(market.get("outcomes", "[]"))
            # tokens is usually ['Yes', 'No'] or similar. 
            # We need the clobTokenIds which are in market.get('clobTokenIds')
            token_ids = market.get("clobTokenIds", [])
            if len(token_ids) < 2:
                logger.error("Market token IDs not found.")
                market = None
                continue

            # Map Yes/No to Token IDs
            yes_token = token_ids[0]
            no_token = token_ids[1]

            odds = trader.get_market_odds(yes_token) # Odds are usually per token book
            
            # 4. AI Decision
            decision = brain.analyze_market(signals, odds)
            
            if decision.get("confidence", 0) > 0.80:
                action = decision.get("action")
                reasoning = decision.get("reasoning")
                
                logger.info(f"SIGNAL DETECTED: {action} | Confidence: {decision['confidence']}")
                logger.debug(f"Reasoning: {reasoning}")
                
                amount_usdc = 10 # Default size
                if action == "BUY_UP":
                    # Buy YES shares
                    trader.execute_trade(yes_token, "BUY", amount_usdc, odds["yes_price"] + 0.01)
                elif action == "BUY_DOWN":
                    # Buy NO shares
                    trader.execute_trade(no_token, "BUY", amount_usdc, odds["no_price"] + 0.01)
                
            # 5. Auto Merging
            condition_id = market.get("conditionId")
            if condition_id:
                trader.merge_shares(condition_id)

        except Exception as e:
            logger.error(f"Loop error: {e}")
            
        await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
