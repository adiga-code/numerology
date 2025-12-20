from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

class CommandHandlers:
    def __init__(self):
        self.router = Router()
        self.router.message(Command('start'))(self.start_handler)
        self.router.message(Command('help'))(self.help_handler)
    
    async def start_handler(self, message: Message):
        """Обработчик команды /start."""
        await message.answer('Добро пожаловать в бота по нумерологии!')

    async def help_handler(self, message: Message):
        """Обработчик команды /help."""
        await message.answer('Это бот, который поможет вам с нумерологией. Используйте /start для начала.')

    async def new_order_handler(self, message: Message):
        """Обработчик новой заявки."""
        await message.answer('Ваша заявка принята!')
    
    async def get_history_handler(self, message: Message):
        """Обработчик получения истории заявок."""
        await message.answer('Вот ваша история заявок.')

    async def support_handler(self, message: Message):
        """Обработчик поддержки пользователей."""
        await message.answer('Свяжитесь с нашей поддержкой по адресу')
