import json
from typing import List
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs
from py_clob_client.constants import POLYGON

from helpers.logger import logger
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
            logger.error(f"Market search error: {e}")
            return []

    def get_market_odds(self, yes_token_id: str) -> PolymarketOdds:
        """Fetches current YES/NO prices for a specific market."""
        try:
            orderbook = self.client.get_orderbook(yes_token_id)
            yes_price = float(orderbook.bids[0].price) if orderbook.bids else 0.5
            no_price = 1.0 - yes_price 
            return PolymarketOdds(yes_price=yes_price, no_price=no_price)
        except Exception as e:
            logger.error(f"Error fetching odds for {yes_token_id}: {e}")
            return PolymarketOdds(yes_price=0.5, no_price=0.5)

    def execute_trade(self, token_id: str, amount_usdc: float, price_limit: float):
        """Dry Run mode: Logs what would have been executed but sends no transactions."""
        try:
            # Dynamic Fee Logic (2026): Fees are highest near $0.50
            # Let's calculate the distance from 0.50
            distance_from_mid = abs(price_limit - 0.50)
            # Example dynamic fee: base 0.001 + surcharge based on proximity to 0.50
            # Peak fee at 0.50 could be 0.01 (1%)
            dynamic_fee = 0.001 + (0.009 * (1 - (distance_from_mid / 0.5)))
            
            total_cost = amount_usdc * (1 + dynamic_fee)
            potential_payout = amount_usdc / price_limit if price_limit > 0 else 0
            
            logger.info("--- DRY RUN EXECUTION ---")
            logger.info(f"WOULD POST ORDER: {amount_usdc / price_limit:.2f} shares of {token_id} at ${price_limit:.2f}")
            logger.info(f"Estimated Dynamic Fee: {dynamic_fee*100:.2f}% (Price: ${price_limit:.2f})")
            logger.info(f"Total Cost: ${total_cost:.2f} | Potential Payout: ${potential_payout:.2f}")
            
            if potential_payout <= total_cost:
                logger.warning(f"DRY RUN ALERT: Trade would be UNPROFITABLE after fees.")
            
            # Return a mock response
            return {
                "status": "DRY_RUN",
                "token_id": token_id,
                "amount": amount_usdc,
                "price": price_limit,
                "dynamic_fee": dynamic_fee
            }
            
        except Exception as e:
            logger.error(f"Dry run error: {e}")
            return None

    def merge_shares(self, condition_id: str):
        """Merges YES and NO shares to recover USDC."""
        try:
            resp = self.client.post_merge(condition_id)
            logger.info(f"Merge outcome for {condition_id}: {resp}")
            return resp
        except Exception as e:
            logger.error(f"Merge error: {e}")
            return None
