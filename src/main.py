"""Главный модуль приложения."""
import asyncio
import logging

import uvicorn
from config import Config
from database import DatabaseManager
from bot import NumerologBot
from api import create_app

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска приложения."""
    # Загрузка конфигурации
    config = Config()
    logger.info("Конфигурация загружена")

    # Инициализация БД
    db_manager = DatabaseManager(config.DATABASE_URL)
    await db_manager.init_db()
    logger.info("База данных инициализирована")

    # Создание бота
    bot_instance = NumerologBot(config, db_manager)

    # Создание FastAPI приложения
    fastapi_app = create_app(config, db_manager)

    # Сохраняем bot instance для доступа из webhooks
    fastapi_app.state.bot = bot_instance.bot

    # Запуск FastAPI в отдельном процессе
    fastapi_config = uvicorn.Config(
        fastapi_app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
    server = uvicorn.Server(fastapi_config)

    async def run_bot():
        """Запуск бота."""
        try:
            await bot_instance.start()
        except Exception as e:
            logger.error(f"Ошибка в боте: {e}")
        finally:
            await bot_instance.stop()
            await db_manager.close()

    async def run_fastapi():
        """Запуск FastAPI."""
        try:
            await server.serve()
        except Exception as e:
            logger.error(f"Ошибка в FastAPI: {e}")

    # Запуск обоих сервисов параллельно
    logger.info("Запуск приложения...")
    await asyncio.gather(
        run_bot(),
        run_fastapi()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Приложение остановлено")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
