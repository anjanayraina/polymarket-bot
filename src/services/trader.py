import json
from typing import List
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs
from py_clob_client.constants import POLYGON

from helpers.logger import logger
from helpers.constants import TAKER_FEE, BTC_MARKET_QUESTION_FILTER, TIME_FRAME_FILTER
from models.polymarket import PolymarketOdds, MarketInfo, ClobMarket

class PolymarketTrader:
    def __init__(self, private_key: str = None, api_key: str = None, secret: str = None, passphrase: str = None, host: str = "https://clob.polymarket.com"):
        self.is_public_only = not all([private_key, api_key, secret, passphrase])
        
        if self.is_public_only:
            logger.info("Initializing PolymarketTrader in PUBLIC-ONLY mode (No API keys provided).")
            # We can still initialize the client for public data
            self.client = ClobClient(host=host, chain_id=POLYGON)
        else:
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
            # Polymarket API returns a lot of old markets. We need to find the CURRENT ones.
            # We fetch a large batch and filter deeply.
            resp = self.client.get_markets()
            
            if isinstance(resp, dict):
                raw_markets = resp.get("data", [])
            elif isinstance(resp, list):
                raw_markets = resp
            else:
                return []

            # Parse with Pydantic for validation and easier access
            markets: List[ClobMarket] = []
            for m in raw_markets:
                try:
                    markets.append(ClobMarket(**m))
                except Exception as e:
                    # Skip malformed markets but log if it's a major issue
                    logger.debug(f"Skipping malformed market data: {e}")
            
            btc_15m_markets = []
            active_count = 0
            
            # Filter for markets that are actually open for business
            open_markets = [m for m in markets if m.active and not m.closed and m.accepting_orders]
            active_count = len(open_markets)
            
            logger.info(f"Retrieved {len(markets)} total markets. Found {active_count} currently active/open markets.")

            for m in open_markets:
                question = m.question or m.title or ""
                
                # BTC 15-minute markets are usually named "Bitcoin Price at [Time]" or "Will Bitcoin be above..."
                # High frequency markets often have "15-minute" or specific time formats.
                question_lower = question.lower()
                is_btc = "bitcoin" in question_lower or "btc" in question_lower
                
                # Check for 15m or the "at X:XX" pattern which is standard for price markets
                is_15m = any(x in question_lower for x in ["15-minute", "15 min", "15m", "bitcoin price at"])
                
                if is_btc and is_15m:
                    logger.info(f"MATCH FOUND: {question}")
                    
                    # Extract tokens. Key can be 'tokens' (list) or 'clobTokenIds'
                    if m.tokens and len(m.tokens) >= 2:
                        btc_15m_markets.append(MarketInfo(
                            condition_id=m.conditionId,
                            question=question,
                            yes_token=m.tokens[0].token_id,
                            no_token=m.tokens[1].token_id,
                            active=True
                        ))
                    elif m.clobTokenIds and len(m.clobTokenIds) >= 2:
                        btc_15m_markets.append(MarketInfo(
                            condition_id=m.conditionId,
                            question=question,
                            yes_token=m.clobTokenIds[0],
                            no_token=m.clobTokenIds[1],
                            active=True
                        ))
            
            if not btc_15m_markets and active_count > 0:
                # Log what we ARE finding to help narrow it down
                current_btc_samples = [m.question for m in open_markets if "btc" in (m.question or "").lower() or "bitcoin" in (m.question or "").lower()][:5]
                logger.warning(f"No 15m BTC markets in the {active_count} active markets. Samples: {current_btc_samples}")

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
        """Merges YES and NO shares to recover USDC (Requires Authorization)."""
        if self.is_public_only:
            logger.debug("Merge skipped: Authenticated actions are disabled in PUBLIC mode.")
            return None
            
        try:
            resp = self.client.post_merge(condition_id)
            logger.info(f"Merge outcome for {condition_id}: {resp}")
            return resp
        except Exception as e:
            logger.error(f"Merge error: {e}")
            return None
