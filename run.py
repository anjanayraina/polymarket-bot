import logging
import sys
import asyncio
from datetime import datetime

# Import Main
from src.main import main

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"bot_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)

logger = logging.getLogger("Runner")

if __name__ == "__main__":
    logger.info("Starting Polymarket Sniper Bot Runner...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.error(f"Critical error in runner: {e}", exc_info=True)
        sys.exit(1)
