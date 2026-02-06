import logging
import sys
import asyncio
from datetime import datetime

# Import Main
from src.main import main
from src.helpers.logger import logger

if __name__ == "__main__":
    logger.info("Starting Polymarket Sniper Bot Runner...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.error(f"Critical error in runner: {e}", exc_info=True)
        sys.exit(1)
