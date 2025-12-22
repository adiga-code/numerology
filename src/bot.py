"""Инициализация и настройка бота."""
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from config import Config
from database import DatabaseManager
from handlers import commands, order_flow, reviews

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class NumerologBot:
    """Класс для управления Telegram ботом."""

    def __init__(self, config: Config, db_manager: DatabaseManager):
        """
        Инициализация бота.

        Args:
            config: Конфигурация приложения
            db_manager: Менеджер базы данных
        """
        self.config = config
        self.db_manager = db_manager
        self.bot = Bot(token=config.BOT_TOKEN)

        # Redis для FSM storage
        self.redis = Redis.from_url(config.REDIS_URL)
        storage = RedisStorage(self.redis)

        self.dp = Dispatcher(storage=storage)
        self._setup_handlers()
        self._setup_middlewares()

    def _setup_handlers(self):
        """Регистрация обработчиков."""
        from handlers import payments

        self.dp.include_router(commands.router)
        self.dp.include_router(order_flow.router)
        self.dp.include_router(payments.router)
        self.dp.include_router(reviews.router)
        logger.info("Обработчики зарегистрированы")

    def _setup_middlewares(self):
        """Настройка middleware."""
        from aiogram import BaseMiddleware
        from aiogram.types import Update
        from typing import Callable, Dict, Any, Awaitable

        class DbSessionMiddleware(BaseMiddleware):
            """Middleware для добавления сессии БД."""

            def __init__(self, db_manager: DatabaseManager):
                super().__init__()
                self.db_manager = db_manager

            async def __call__(
                self,
                handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
                event: Update,
                data: Dict[str, Any]
            ) -> Any:
                async with self.db_manager.async_session() as session:
                    data["session"] = session
                    return await handler(event, data)

        self.dp.update.middleware(DbSessionMiddleware(self.db_manager))
        logger.info("Middleware настроены")

    async def _setup_bot_commands(self):
        """Настройка меню команд бота."""
        from aiogram.types import BotCommand

        commands = [
            BotCommand(command="start", description="🏠 Начало работы"),
            BotCommand(command="new", description="➕ Создать новый заказ"),
            BotCommand(command="history", description="📋 История заказов"),
            BotCommand(command="download", description="📥 Скачать отчёт повторно"),
            BotCommand(command="help", description="❓ Справка"),
            BotCommand(command="support", description="💬 Поддержка"),
            BotCommand(command="cancel", description="❌ Отменить текущий заказ"),
        ]

        await self.bot.set_my_commands(commands)
        logger.info("Меню команд настроено")

    async def start(self):
        """Запуск бота."""
        logger.info("Запуск Telegram бота...")

        # Инициализируем GPT клиента с книгой
        if self.config.OPENAI_API_KEY:
            from services.ai_service import initialize_gpt_with_book
            await initialize_gpt_with_book(self.config.OPENAI_API_KEY)
        else:
            logger.warning("OPENAI_API_KEY не настроен - GPT с книгой не будет доступен")

        # Настраиваем меню команд
        await self._setup_bot_commands()

        await self.dp.start_polling(self.bot)

    async def stop(self):
        """Остановка бота."""
        logger.info("Остановка Telegram бота...")
        await self.bot.session.close()
        await self.redis.close()
