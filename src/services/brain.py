import json
import logging
from openai import OpenAI

from helpers.constants import AI_MODEL, AI_CONFIDENCE_THRESHOLD, SYSTEM_PROMPT, BRAIN_PROMPT_TEMPLATE
from models.market import MarketSignals
from models.polymarket import PolymarketOdds
from models.ai import AIDecision

class Brain:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.logger = logging.getLogger("Brain")

    def analyze_market(self, signals: MarketSignals, odds: PolymarketOdds) -> AIDecision:
        """Uses LLM to decide on a trade based on signals and current odds."""
        # signals.model_dump_json() avoids dictionary access
        prompt = BRAIN_PROMPT_TEMPLATE.format(
            signals=signals.model_dump_json(indent=2),
            odds=odds.model_dump_json(indent=2),
            threshold=AI_CONFIDENCE_THRESHOLD
        )
        try:
            response = self.client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            # Parse into Pydantic model
            decision = AIDecision.model_validate_json(content)
            self.logger.info(f"AI Decision: {decision.action} (Conf: {decision.confidence})")
            return decision
            
        except Exception as e:
            self.logger.error(f"Error in Brain analysis: {e}")
            return AIDecision(
                action="WAIT", 
                confidence=0.0, 
                reasoning=f"Error: {str(e)}"
            )
