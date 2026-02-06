import asyncio
import json
import anthropic
from helpers.logger import logger

from helpers.constants import AI_MODEL, AI_CONFIDENCE_THRESHOLD, SYSTEM_PROMPT, BRAIN_PROMPT_TEMPLATE
from models.market import MarketSignals
from models.polymarket import PolymarketOdds
from models.ai import AIDecision

class Brain:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)

    def analyze_market(self, signals: MarketSignals, odds: PolymarketOdds) -> AIDecision:
        """Uses Claude to decide on a trade based on signals and current odds."""
        prompt = BRAIN_PROMPT_TEMPLATE.format(
            signals=signals.model_dump_json(indent=2),
            odds=odds.model_dump_json(indent=2),
            threshold=AI_CONFIDENCE_THRESHOLD
        ).strip()
        
        try:
            message = self.client.messages.create(
                model=AI_MODEL,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = message.content[0].text
            decision = AIDecision.model_validate_json(content)
            logger.info(f"Claude Decision: {decision.action} (Conf: {decision.confidence})")
            return decision
            
        except Exception as e:
            logger.error(f"Error in Brain analysis (Claude): {e}")
            return AIDecision(
                action="WAIT", 
                confidence=0.0, 
                reasoning=f"Error: {str(e)}"
            )
