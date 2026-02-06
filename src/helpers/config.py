import os
from pathlib import Path
from dotenv import load_dotenv

class Config:
    def __init__(self):
        # 1. Determine environment (default to local)
        self.app_env = os.getenv("APP_ENV", "local").lower()
        
        # 2. Construct path to resources folder (it's now two levels up from this file)
        base_dir = Path(__file__).resolve().parent.parent
        env_file_name = f".env.{self.app_env}"
        env_path = base_dir / "resources" / env_file_name
        
        # 3. Load the environment file
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
            print(f"Loaded configuration from {env_path}")
        else:
            print(f"Warning: Configuration file not found at {env_path}. Using system environment variables.")

        # 4. Map values
        self.POLYGON_PRIVATE_KEY = os.getenv("POLYGON_PRIVATE_KEY")
        self.CLOB_API_KEY = os.getenv("CLOB_API_KEY")
        self.CLOB_SECRET = os.getenv("CLOB_SECRET")
        self.CLOB_PASSPHRASE = os.getenv("CLOB_PASSPHRASE")
        self.CLOB_HOST = os.getenv("CLOB_HOST", "https://clob.polymarket.com")
        
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
        
        self.BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
        self.BINANCE_SECRET = os.getenv("BINANCE_SECRET")
        self.COINGLASS_API_KEY = os.getenv("COINGLASS_API_KEY")
        self.CRYPTOPANIC_API_KEY = os.getenv("CRYPTOPANIC_API_KEY")

settings = Config()
