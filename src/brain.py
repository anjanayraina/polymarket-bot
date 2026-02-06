import json
import logging
from openai import OpenAI

class Brain:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
        self.logger = logging.getLogger("Brain")

    def analyze_market(self, signals, polymarket_odds):
        """Uses LLM to decide on a trade based on signals and current odds."""
        prompt = f"""
Analyze the provided BTC market data. Your goal is to identify if the 15-minute BTC direction is mispriced.

Market Signals:
{json.dumps(signals, indent=2)}

Polymarket Current Odds:
{json.dumps(polymarket_odds, indent=2)}

Instructions:
If Binance walls and funding suggest a drop, but 'DOWN' shares are still < $0.52, recommend 'BUY_DOWN'.
Conversely, if indicators suggest a pump and 'UP' shares are cheap, recommend 'BUY_UP'.

Output strictly in JSON: {{'action': 'BUY_UP'|'BUY_DOWN'|'WAIT', 'confidence': float, 'reasoning': string}}.
Only recommend a trade if confidence is > 0.80.
"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a high-frequency trading bot brain specializing in BTC/Polymarket arbitrage."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            decision = json.loads(response.choices[0].message.content)
            self.logger.info(f"AI Decision: {decision.get('action')} (Conf: {decision.get('confidence')})")
            return decision
            
        except Exception as e:
            self.logger.error(f"Error in Brain analysis: {e}")
            return {"action": "WAIT", "confidence": 0, "reasoning": f"Error: {str(e)}"}
