# Polymarket BTC Signal Sniper

Autonomous Suggestion Agent for Polymarket's 15-minute BTC Up/Down markets. This bot acts as a "Human-in-the-Loop" advisor, identifying high-conviction signals without auto-executing trades.

## Features
- **Real-time Signal Analysis**: Streams Binance Order Book via WebSockets.
- **Advanced Context**: Analyzes Funding Rates and Liquidation Clusters (Coinglass).
- **AI Reasoning**: Powered by Claude 3.5 Sonnet for detailed "Trade Briefs".
- **Human-in-the-Loop**: Presents structured briefs in the terminal and waits for user confirmation before logging a "Dry Run".
- **Dynamic Fee Engine (2026)**: Simulates taker fees that dynamically adjust based on price proximity to the $0.50 range.
- **Persistent Suggestions**: Automatically logs high-confidence trade signals to `suggestions.log`.

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**:
   Copy `src/resources/.env.example` to `src/resources/.env.local` and fill in your keys.

3. **Run the Agent**:
   ```bash
   python src/main.py
   ```

## Architecture
- `src/services/data_streamer.py`: Handles Binance WebSocket and Coinglass API.
- `src/services/brain.py`: Sends aggregated signals to Claude for analysis.
- `src/services/trader.py`: Manages dry-run logic and simulated execution.
- `src/services/notification_service.py`: Logs suggestions to a local file.
- `src/services/trading_engine.py`: Orchestrates the sniped signal loop and user interaction.

## Disclaimer
This is for informational purposes only. Trading involves risk. Use the "Dry Run" mode to test strategies before considering live deployment.
