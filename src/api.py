"""FastAPI приложение для обработки webhook."""
import logging
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager

from config import Config
from database import DatabaseManager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager для FastAPI."""
    logger.info("FastAPI starting...")
    yield
    logger.info("FastAPI shutting down...")


def create_app(config: Config, db_manager: DatabaseManager) -> FastAPI:
    """
    Создание FastAPI приложения.

    Args:
        config: Конфигурация приложения
        db_manager: Менеджер базы данных

    Returns:
        FastAPI: Приложение FastAPI
    """
    app = FastAPI(
        title="Numerology Bot API",
        description="Webhook endpoints для Manus и ЮKassa",
        lifespan=lifespan
    )

    # Сохраняем зависимости
    app.state.config = config
    app.state.db = db_manager

    # Импортируем роутеры webhook
    from webhooks.manus import router as manus_router
    from webhooks.yookassa import router as yookassa_router
    from handlers.n8n_webhook import router as n8n_router

    app.include_router(manus_router, prefix="/webhook/manus", tags=["manus"])
    app.include_router(yookassa_router, prefix="/webhook/yookassa", tags=["yookassa"])
    app.include_router(n8n_router)  # N8N роутер уже имеет prefix /webhook/n8n

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "ok"}

    return app
