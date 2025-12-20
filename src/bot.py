import logging
from aiogram import Bot, Dispatcher 

from config import Config
from handlers import CommandHandlers
from database import DatabaseManager

logging.basicConfig(level=logging.INFO)

class NumerologBot:
    def __init__(self, config: Config):
        self.config = config
        self.bot = Bot(token=self.config.BOT_TOKEN)
        self.dp = Dispatcher()

    async def _setup_handlers(self):
        """
        Инициализация обработчиков бота.

        :param self: Description
        """
        self.command_handlers = CommandHandlers()
        self.dp.include_router(self.command_handlers.router)

    async def _setup_components(self):
        """
        Инициализация компонентов бота.        
        
        :param self: Description
        """
        self.db_manager = DatabaseManager(self.config.DATABASE_URL)
        await self.db_manager.initialise()

    async def start(self):
        """
        Запуск бота.
        
        :param self: Description
        """
        logging.info("Starting Numerolog Bot...")
        await self._setup_handlers()
        await self._setup_components()
        await self.dp.start_polling(self.bot)