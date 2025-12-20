from sqlalchemy import BigInteger, Text, String, Integer, Float, Boolean, DateTime, ForeignKey, Date, Time, DECIMAL, UUID
from sqlalchemy.orm import relationship, mapped_column, Mapped, DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine, async_sessionmaker
from datetime import datetime, date, time
from uuid import uuid4


class DatabaseManager:
    def __init__(self, database_url: str):
        self.engine = create_async_engine(database_url, echo=True)
        self.async_session = async_sessionmaker(self.engine, expire_on_commit=False)

    async def initialise(self):
        """
        Инициализация базы данных.
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    orders: Mapped[list["OrderORM"]] = relationship(back_populates="user")
    reviews: Mapped[list["ReviewORM"]] = relationship(back_populates="user")


class OrderORM(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_uuid: Mapped[str] = mapped_column(UUID(as_uuid=False), unique=True, default=lambda: str(uuid4()))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    tariff: Mapped[str] = mapped_column(String(50), nullable=False)  # quick, deep, pair, family
    style: Mapped[str] = mapped_column(String(50), nullable=False)  # analytical, shamanic
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, paid, processing, completed, failed, refunded
    amount: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)  # yookassa, telegram_stars
    payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manus_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    user: Mapped["UserORM"] = relationship(back_populates="orders")
    participants: Mapped[list["OrderParticipantORM"]] = relationship(back_populates="order")
    reviews: Mapped[list["ReviewORM"]] = relationship(back_populates="order")
    ai_logs: Mapped[list["AiLogORM"]] = relationship(back_populates="order")


class OrderParticipantORM(Base):
    __tablename__ = "order_participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    birth_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    birth_place: Mapped[str | None] = mapped_column(String(255), nullable=True)
    participant_type: Mapped[str] = mapped_column(String(50), nullable=False)  # main, partner, family_member

    # Relationships
    order: Mapped["OrderORM"] = relationship(back_populates="participants")


class ReviewORM(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    order: Mapped["OrderORM"] = relationship(back_populates="reviews")
    user: Mapped["UserORM"] = relationship(back_populates="reviews")


class AiLogORM(Base):
    __tablename__ = "ai_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # manus, gpt4, gemini
    task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, success, failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    order: Mapped["OrderORM"] = relationship(back_populates="ai_logs")