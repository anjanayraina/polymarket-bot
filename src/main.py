import asyncio
from helpers.logger import logger
from helpers.config import settings
from helpers.service_locator import service_locator

# Import Services
from services.data_streamer import DataStreamer
from services.brain import Brain
from services.trader import PolymarketTrader
from services.trading_engine import TradingEngine

async def main():
    """
    Application Bootstrapper.
    Responsible for setting up configuration, initializing services, 
    and registering them in the Service Locator.
    """
    logger.info("Bootstrapping Polymarket Sniper Bot...")

    try:
        # 1. Verify critical configuration
        if not all([settings.POLYGON_PRIVATE_KEY, settings.CLOB_API_KEY, settings.ANTHROPIC_API_KEY]):
            logger.error("Missing critical environment variables. Bot cannot start.")
            return

        # 2. Initialize Services
        streamer = DataStreamer(
            coinglass_api_key=settings.COINGLASS_API_KEY,
            cryptopanic_api_key=settings.CRYPTOPANIC_API_KEY
        )
        brain = Brain(api_key=settings.ANTHROPIC_API_KEY)
        trader = PolymarketTrader(
            settings.POLYGON_PRIVATE_KEY, 
            settings.CLOB_API_KEY, 
            settings.CLOB_SECRET, 
            settings.CLOB_PASSPHRASE
        )
        engine = TradingEngine()

        # 3. Register Services in Locator
        service_locator.register(DataStreamer, streamer)
        service_locator.register(Brain, brain)
        service_locator.register(PolymarketTrader, trader)
        service_locator.register(TradingEngine, engine)

        logger.info("Application bootstrap complete. Starting Trading Engine...")

        # 4. Start the Application Workflow
        await engine.run()

    except Exception as e:
        logger.critical(f"Failed to bootstrap application: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
