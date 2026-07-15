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
    _raw_db_url = os.getenv("DB_URL", "sqlite+aiosqlite:///:memory:")
    if _raw_db_url.startswith("postgres://"):
        DB_URL = _raw_db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif _raw_db_url.startswith("postgresql://"):
        DB_URL = _raw_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    else:
        DB_URL = _raw_db_url

config = Config()
