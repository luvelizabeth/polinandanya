import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "https://your-domain.vercel.app/api/webhook")
    
    DANILA_ID: int = int(os.getenv("DANILA_ID", "0"))
    POLINA_ID: int = int(os.getenv("POLINA_ID", "0"))
    CHAT_ID: int = int(os.getenv("CHAT_ID", "0"))
    
    POLINA_CITY: str = os.getenv("POLINA_CITY", "Moscow")
    WEATHER_API_KEY: str = os.getenv("WEATHER_API_KEY", "")
    
    # DB Configuration
    DB_URL: str = os.getenv("DB_URL", "sqlite+aiosqlite:///:memory:")

config = Config()
