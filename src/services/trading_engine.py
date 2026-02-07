import asyncio
from helpers.logger import logger
from helpers.service_locator import service_locator
from helpers.constants import AI_CONFIDENCE_THRESHOLD, DEFAULT_TRADE_AMOUNT
from services.data_streamer import DataStreamer
from services.brain import Brain
from services.trader import PolymarketTrader
from services.notification_service import NotificationService
from models.polymarket import MarketInfo
from models.ai import AIDecision

class TradingEngine:
    def __init__(self):
        self.streamer: DataStreamer = None
        self.brain: Brain = None
        self.trader: PolymarketTrader = None
        self.market: MarketInfo = None
        
        # State exposure for API
        self.latest_signals = None
        self.latest_odds = None
        self.latest_brief = None
        self.confirmation_queue = asyncio.Queue()

    def _resolve_dependencies(self):
        self.streamer = service_locator.get(DataStreamer)
        self.brain = service_locator.get(Brain)
        self.trader = service_locator.get(PolymarketTrader)
        self.notifier = service_locator.get(NotificationService)

    def _generate_trade_brief(self, decision: AIDecision, signals, odds, fee):
        """Prints a structured Trade Brief to the terminal."""
        print("\n" + "="*60)
        print(" 🎯 SIGNAL SNIPER: TRADE BRIEF")
        print("="*60)
        print(f"Action: {decision.action} | Confidence: {decision.confidence:.2f}")
        print("-" * 60)
        print(f"15m BTC Trend: {decision.reasoning[:100]}...") # Trend info from reasoning
        print(f"BTC Price: ${signals.btc_price:,.2f}")
        
        print("\n[Binance Order Book Walls]")
        for bid in signals.order_book.top_bid_walls[:1]:
            print(f"  BID Wall: ${bid.price:,.2f} | Volume: {bid.volume:.2f}")
        for ask in signals.order_book.top_ask_walls[:1]:
            print(f"  ASK Wall: ${ask.price:,.2f} | Volume: {ask.volume:.2f}")

        print(f"\n[Liquidations & Funding]")
        print(f"  Funding Rate: {signals.funding.current_funding_rate * 100:.4f}%")
        print(f"  Short Liqs (1h): ${signals.liquidations.short_vol:,.0f}")
        print(f"  Long Liqs (1h): ${signals.liquidations.long_vol:,.0f}")

        print(f"\n[Polymarket Odds]")
        print(f"  YES Price: ${odds.yes_price:.2f} | NO Price: ${odds.no_price:.2f}")

        print(f"\n[Fee Architecture 2026]")
        print(f"  Estimated Taker Fee: {fee * 100:.2f}%")
        if fee > 0.008:
            print("  ⚠️ WARNING: Taker fee is HIGH (Price near $0.50 range).")
        
        print("\n[AI Reasoning Breakdown]")
        print(decision.reasoning)
        print("="*60 + "\n")

    async def run(self):
        """Starts the core trading workflow."""
        self._resolve_dependencies()
        logger.info("Signal Sniper Agent started. Initializing data streams...")
        
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
                
                # Update state for API
                self.latest_signals = signals
                self.latest_odds = odds
                
                decision: AIDecision = self.brain.analyze_market(signals, odds)
                
                if decision.confidence > AI_CONFIDENCE_THRESHOLD and decision.action != "WAIT":
                    # Calculate fee for the brief
                    price_limit = odds.yes_price + 0.01 if decision.action == "BUY_UP" else odds.no_price + 0.01
                    dist = abs(price_limit - 0.50)
                    fee = 0.001 + (0.009 * (1 - (dist / 0.5)))

                    self._generate_trade_brief(decision, signals, odds, fee)
                    
                    # Store brief for API
                    self.latest_brief = {
                        "action": decision.action,
                        "confidence": decision.confidence,
                        "reasoning": decision.reasoning,
                        "btc_price": signals.btc_price,
                        "fee": fee,
                        "timestamp": signals.timestamp.isoformat()
                    }
                    
                    # Notification System
                    if "BUY" in decision.action:
                        self.notifier.notify_signal(
                            decision.action, 
                            decision.confidence, 
                            decision.reasoning,
                            price_limit,
                            self.market.yes_token if decision.action == "BUY_UP" else self.market.no_token
                        )

                    # Interactive Verification (Dual Mode: Terminal + API Queue)
                    print("\n[REQUEST REVIEW] Review the Trade Brief above.")
                    print("Type 'CONTINUE' in terminal OR POST to /trade/confirm via API.")
                    
                    async def wait_for_terminal():
                        return await asyncio.to_thread(input, "Type 'CONTINUE' to log Dry Run execution or 'SKIP' to ignore: ")

                    async def wait_for_api():
                        return await self.confirmation_queue.get()

                    # Wait for first response
                    done, pending = await asyncio.wait(
                        [asyncio.create_task(wait_for_terminal()), asyncio.create_task(wait_for_api())],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    user_input = list(done)[0].result()
                    for task in pending:
                        task.cancel()
                    
                    if user_input.strip().upper() == 'CONTINUE':
                        if decision.action == "BUY_UP":
                            self.trader.execute_trade(self.market.yes_token, DEFAULT_TRADE_AMOUNT, odds.yes_price + 0.01)
                        elif decision.action == "BUY_DOWN":
                            self.trader.execute_trade(self.market.no_token, DEFAULT_TRADE_AMOUNT, odds.no_price + 0.01)
                        self.latest_brief = None # Clear after execution
                    else:
                        logger.info("Signal skipped.")
                        self.latest_brief = None
                    
                # NOTE: merge_shares is removed here to support public-only mode
            except Exception as e:
                logger.error(f"Engine loop error: {e}")
                
            await asyncio.sleep(10)
