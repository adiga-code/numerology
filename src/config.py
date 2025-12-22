"""Конфигурация приложения."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Конфигурация приложения, загружаемая из переменных окружения."""

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    # Telegram
    BOT_TOKEN: str

    # AI Services
    MANUS_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_ASSISTANT_ID: str = ""  # ID Assistant с базой знаний (опционально)
    GEMINI_API_KEY: str = ""

    # Payments
    YOOKASSA_SHOP_ID: str = ""
    YOOKASSA_SECRET_KEY: str = ""

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Webhook
    WEBHOOK_DOMAIN: str = ""
    WEBHOOK_PATH: str = "/webhook"

    @property
    def webhook_url(self) -> str:
        """Полный URL webhook."""
        return f"{self.WEBHOOK_DOMAIN}{self.WEBHOOK_PATH}"
