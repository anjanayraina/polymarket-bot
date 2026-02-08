import asyncio
from helpers.logger import logger
from helpers.config import settings
from helpers.service_locator import service_locator

from services.data_streamer import DataStreamer
from services.brain import Brain
from services.trader import PolymarketTrader
from services.trading_engine import TradingEngine
from services.notification_service import NotificationService

async def main():
    """
    Application Bootstrapper.
    Responsible for setting up configuration, initializing services, 
    and registering them in the Service Locator.
    """
    logger.info("Bootstrapping Polymarket Sniper Bot...")

    try:
        # 1. Verify critical configuration (Only AI key is strictly mandatory for Signal Sniper)
        if not settings.ANTHROPIC_API_KEY:
            logger.error("Missing ANTHROPIC_API_KEY. Bot cannot analyze signals.")
            return

        if not all([settings.POLYGON_PRIVATE_KEY, settings.CLOB_API_KEY]):
            logger.warning("Polymarket API keys missing. Bot will run in PUBLIC-ONLY mode.")

        # 2. Initialize Services
        streamer = DataStreamer(
            coinglass_api_key=settings.COINGLASS_API_KEY
        )
        brain = Brain(api_key=settings.ANTHROPIC_API_KEY)
        trader = PolymarketTrader(
            settings.POLYGON_PRIVATE_KEY, 
            settings.CLOB_API_KEY, 
            settings.CLOB_SECRET, 
            settings.CLOB_PASSPHRASE
        )
        notifier = NotificationService()
        engine = TradingEngine()

        # 3. Register Services in Locator
        service_locator.register(DataStreamer, streamer)
        service_locator.register(Brain, brain)
        service_locator.register(PolymarketTrader, trader)
        service_locator.register(NotificationService, notifier)
        service_locator.register(TradingEngine, engine)
        
        # 4. Initialize API Server
        import uvicorn
        from api.server import app
        config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
        server = uvicorn.Server(config)

        logger.info("Application bootstrap complete. Starting Trading Engine & API Server (Port 8000)...")

        # 5. Start the Application Workflow and API Server concurrently
        await asyncio.gather(
            engine.run(),
            server.serve()
        )

    except Exception as e:
        logger.critical(f"Failed to bootstrap application: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
