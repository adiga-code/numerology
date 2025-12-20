import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Конфигурация приложения, загружаемая из переменных окружения."""
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    DATABASE_URL = os.getenv("DATABASE_URL")
