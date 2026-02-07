import os
from datetime import datetime
from helpers.logger import logger

class NotificationService:
    def __init__(self, log_file: str = "suggestions.log"):
        self.log_file = log_file

    def notify_signal(self, action: str, confidence: float, reasoning: str, price: float, token_id: str):
        """Logs a BUY signal to the local suggestions file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = (
            f"[{timestamp}] SIGNAL DETECTED\n"
            f"Action: {action} | Confidence: {confidence:.2f}\n"
            f"Price: ${price:.2f} | Token: {token_id}\n"
            f"Reasoning: {reasoning}\n"
            f"{'-'*50}\n"
        )
        
        try:
            with open(self.log_file, "a") as f:
                f.write(entry)
            logger.info(f"Notification written to {self.log_file}")
        except Exception as e:
            logger.error(f"Failed to write notification: {e}")
