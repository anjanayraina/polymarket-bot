import logging
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, RequestArgs
from py_clob_client.constants import POLYGON

class PolymarketTrader:
    def __init__(self, private_key, api_key, secret, passphrase, host="https://clob.polymarket.com"):
        self.client = ClobClient(
            host=host,
            key=api_key,
            secret=secret,
            passphrase=passphrase,
            private_key=private_key,
            chain_id=POLYGON
        )
        self.logger = logging.getLogger("PolymarketTrader")
        self.taker_fee = 0.0315  # 3.15%

    def find_active_btc_markets(self):
        """Searches for active BTC 15-minute markets."""
        try:
            # Fetch markets and filter
            markets = self.client.get_markets()
            btc_15m_markets = []
            for m in markets:
                if "Bitcoin" in m.get("question", "") and "15-minute" in m.get("question", ""):
                    if m.get("active"):
                        btc_15m_markets.append(m)
            return btc_15m_markets
        except Exception as e:
            self.logger.error(f"Market search error: {e}")
            return []

    def get_market_odds(self, market_id):
        """Fetches current YES/NO prices for a specific market."""
        try:
            # Get orderbook for the market
            # For simplicity, we use mid price or top bid/ask
            orderbook = self.client.get_orderbook(market_id)
            yes_price = float(orderbook.bids[0].price) if orderbook.bids else 0.5
            no_price = float(orderbook.asks[0].price) if orderbook.asks else 0.5
            return {"yes_price": yes_price, "no_price": no_price}
        except Exception as e:
            self.logger.error(f"Error fetching odds for {market_id}: {e}")
            return {"yes_price": 0.5, "no_price": 0.5}

    def execute_trade(self, market_id, side, amount_usdc, price_limit):
        """Executes a trade with fee checks and slippage protection."""
        try:
            # 1. Fee Check
            total_cost = amount_usdc * (1 + self.taker_fee)
            potential_payout = amount_usdc / price_limit if price_limit > 0 else 0
            
            if potential_payout <= total_cost:
                self.logger.warning(f"Trade rejected: Payout (${potential_payout:.2f}) does not justify fee cost (${total_cost:.2f})")
                return None

            # 2. Post Order
            # side: 'BUY' or 'SELL'. Polymarket uses tokens (outcome_id).
            # We need to map 'BUY_UP' to 'YES' token and 'BUY_DOWN' to 'NO' token.
            order_args = OrderArgs(
                price=price_limit,
                size=amount_usdc / price_limit,
                side="BUY",
                token_id=market_id # outcome_id actually
            )
            
            resp = self.client.post_order(order_args)
            self.logger.info(f"Order posted: {resp}")
            return resp
            
        except Exception as e:
            self.logger.error(f"Execution error: {e}")
            return None

    def merge_shares(self, condition_id):
        """Merges YES and NO shares to recover USDC if bot holds both."""
        try:
            # Polymarket Client has a merge function
            resp = self.client.post_merge(condition_id)
            self.logger.info(f"Merge outcome: {resp}")
            return resp
        except Exception as e:
            self.logger.error(f"Merge error: {e}")
            return None
