"""Управление подключением к базе данных."""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from config import Config
from database.models import Base


class DatabaseManager:
    """Менеджер базы данных."""

    def __init__(self, database_url: str):
        """
        Инициализация менеджера БД.

        Args:
            database_url: URL подключения к базе данных
        """
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def init_db(self) -> None:
        """Создание всех таблиц в базе данных."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        """Закрытие подключения к базе данных."""
        await self.engine.dispose()

    def get_session(self) -> AsyncSession:
        """
        Получение сессии для работы с БД.

        Returns:
            AsyncSession: Асинхронная сессия SQLAlchemy
        """
        return self.async_session()
