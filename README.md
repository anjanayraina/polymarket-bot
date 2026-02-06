# Polymarket BTC Sniper Bot

AI-Powered "Taker" Sniper Bot for Polymarket's 15-minute BTC Up/Down markets.

## Features
- **Real-time Data ingestion**: Streams Binance Order Book via WebSockets.
- **Multi-Signal Analysis**: Analyzes Funding Rates, Liquidation Spikes (Coinglass), and News Sentiment (CryptoPanic).
- **AI Brain**: Powered by OpenAI `gpt-4o-mini` for fast, low-latency decision making.
- **Execution Guardrails**:
  - Taker Fee check (3.15% threshold).
  - Slippage protection with price limits.
  - Automatic share merging to recover USDC.

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and fill in your keys:
   ```bash
   cp .env.example .env
   ```

3. **Run the Bot**:
   ```bash
   python src/main.py
   ```

## Architecture
- `src/data_streamer.py`: Handles Binance WebSocket and REST APIs for Coinglass/CryptoPanic.
- `src/brain.py`: Sends signals to OpenAI for trade decisions.
- `src/trader.py`: Manages Polymarket CLOB interactions and trade execution.
- `src/main.py`: Orchestrates the trading loop every 10 seconds.

## Disclaimer
This is a trading bot and carries financial risk. Use at your own risk. Ensure you have sufficient USDC on Polygon and the necessary allowances set for the Polymarket CLOB.
