import logging
import json
from typing import List
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs
from py_clob_client.constants import POLYGON

from helpers.constants import TAKER_FEE, BTC_MARKET_QUESTION_FILTER, TIME_FRAME_FILTER
from models.polymarket import PolymarketOdds, MarketInfo

class PolymarketTrader:
    def __init__(self, private_key: str, api_key: str, secret: str, passphrase: str, host: str = "https://clob.polymarket.com"):
        self.client = ClobClient(
            host=host,
            key=api_key,
            secret=secret,
            passphrase=passphrase,
            private_key=private_key,
            chain_id=POLYGON
        )
        self.logger = logging.getLogger("PolymarketTrader")
        self.taker_fee = TAKER_FEE

    def find_active_btc_markets(self) -> List[MarketInfo]:
        """Searches for active BTC 15-minute markets."""
        try:
            markets = self.client.get_markets()
            btc_15m_markets = []
            for m in markets:
                question = m.get("question", "")
                if BTC_MARKET_QUESTION_FILTER in question and TIME_FRAME_FILTER in question:
                    if m.get("active"):
                        outcomes = json.loads(m.get("outcomes", "[]"))
                        token_ids = m.get("clobTokenIds", [])
                        if len(token_ids) >= 2:
                            btc_15m_markets.append(MarketInfo(
                                condition_id=m.get("conditionId"),
                                question=question,
                                yes_token=token_ids[0],
                                no_token=token_ids[1],
                                active=True
                            ))
            return btc_15m_markets
        except Exception as e:
            self.logger.error(f"Market search error: {e}")
            return []

    def get_market_odds(self, yes_token_id: str) -> PolymarketOdds:
        """Fetches current YES/NO prices for a specific market."""
        try:
            # Polymarket orderbook for a specific token
            orderbook = self.client.get_orderbook(yes_token_id)
            yes_price = float(orderbook.bids[0].price) if orderbook.bids else 0.5
            
            # This is a simplification. Usually you'd fetch both books.
            # For 15m BTC, No price is roughly 1 - Yes price.
            no_price = 1.0 - yes_price 
            
            return PolymarketOdds(yes_price=yes_price, no_price=no_price)
        except Exception as e:
            self.logger.error(f"Error fetching odds for {yes_token_id}: {e}")
            return PolymarketOdds(yes_price=0.5, no_price=0.5)

    def execute_trade(self, token_id: str, amount_usdc: float, price_limit: float):
        """Executes a trade with fee checks and slippage protection."""
        try:
            total_cost = amount_usdc * (1 + self.taker_fee)
            potential_payout = amount_usdc / price_limit if price_limit > 0 else 0
            
            if potential_payout <= total_cost:
                self.logger.warning(f"Trade rejected: Payout (${potential_payout:.2f}) <= Cost (${total_cost:.2f})")
                return None

            order_args = OrderArgs(
                price=price_limit,
                size=amount_usdc / price_limit,
                side="BUY",
                token_id=token_id
            )
            
            resp = self.client.post_order(order_args)
            self.logger.info(f"Order posted for {token_id}: {resp}")
            return resp
            
        except Exception as e:
            self.logger.error(f"Execution error: {e}")
            return None

    def merge_shares(self, condition_id: str):
        """Merges YES and NO shares to recover USDC."""
        try:
            resp = self.client.post_merge(condition_id)
            self.logger.info(f"Merge outcome for {condition_id}: {resp}")
            return resp
        except Exception as e:
            self.logger.error(f"Merge error: {e}")
            return None
