# AI Brain Constants
AI_MODEL = "claude-3-5-sonnet-20240620"
AI_CONFIDENCE_THRESHOLD = 0.80

SYSTEM_PROMPT = "You are a high-frequency trading bot brain specializing in BTC/Polymarket arbitrage. You must respond ONLY in a valid JSON object."

BRAIN_PROMPT_TEMPLATE = """
Analyze the provided BTC market data. Your goal is to identify if the 15-minute BTC direction is mispriced.

Market Signals:
{signals}

Polymarket Current Odds:
{odds}

Instructions:
If Binance walls and funding suggest a drop, but 'DOWN' shares are still < $0.52, recommend 'BUY_DOWN'.
Conversely, if indicators suggest a pump and 'UP' shares are cheap, recommend 'BUY_UP'.

Output strictly in JSON: {{'action': 'BUY_UP'|'BUY_DOWN'|'WAIT', 'confidence': float, 'reasoning': string}}.
Only recommend a trade if confidence is > {threshold}.
"""

# Polymarket Trader Constants
TAKER_FEE = 0.0315  # 3.15%
BTC_MARKET_QUESTION_FILTER = "Bitcoin"
TIME_FRAME_FILTER = "15-minute"
DEFAULT_TRADE_AMOUNT = 10

# Data Streamer Constants
BINANCE_WS_URL_TEMPLATE = "wss://stream.binance.com:9443/ws/{symbol}@depth20@100ms"
BINANCE_FUNDING_URL_TEMPLATE = "https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}"
COINGLASS_LIQUIDATION_URL = "https://open-api.coinglass.com/public/v2/liquidation_info"
CRYPTOPANIC_API_URL = "https://cryptopanic.com/api/v1/posts/"

DEFAULT_CRYPTO_SYMBOL = "BTC"
DEFAULT_BINANCE_SYMBOL = "BTCUSDT"
DEFAULT_WS_SYMBOL = "btcusdt"
