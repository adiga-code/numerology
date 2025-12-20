"""SQLAlchemy модели базы данных."""
from datetime import datetime
from decimal import Decimal
from typing import List
from uuid import uuid4

from sqlalchemy import String, Integer, BigInteger, Text, DECIMAL, DateTime, Date, Time, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from utils.enums import (
    TariffType,
    StyleType,
    OrderStatus,
    Currency,
    PaymentMethod,
    ParticipantType,
    AiProvider,
    AiLogStatus
)


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""
    pass


class User(Base):
    """Модель пользователя."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="user")
    reviews: Mapped[List["Review"]] = relationship("Review", back_populates="user")


class Order(Base):
    """Модель заказа."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_uuid: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid4()))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    # Тариф и стиль
    tariff: Mapped[TariffType] = mapped_column(SQLEnum(TariffType), nullable=False)
    style: Mapped[StyleType] = mapped_column(SQLEnum(StyleType), nullable=False)

    # Статус и оплата
    status: Mapped[OrderStatus] = mapped_column(SQLEnum(OrderStatus), default=OrderStatus.PENDING)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    currency: Mapped[Currency] = mapped_column(SQLEnum(Currency), default=Currency.RUB)
    payment_method: Mapped[PaymentMethod | None] = mapped_column(SQLEnum(PaymentMethod))
    payment_id: Mapped[str | None] = mapped_column(String(255))

    # AI обработка
    manus_task_id: Mapped[str | None] = mapped_column(String(255))
    pdf_url: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="orders")
    participants: Mapped[List["OrderParticipant"]] = relationship("OrderParticipant", back_populates="order", cascade="all, delete-orphan")
    reviews: Mapped[List["Review"]] = relationship("Review", back_populates="order")
    ai_logs: Mapped[List["AiLog"]] = relationship("AiLog", back_populates="order")


class OrderParticipant(Base):
    """Модель участника заказа."""

    __tablename__ = "order_participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)

    # Данные участника
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    birth_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    birth_time: Mapped[datetime | None] = mapped_column(Time)
    birth_place: Mapped[str | None] = mapped_column(String(255))

    # Тип участника
    participant_type: Mapped[ParticipantType] = mapped_column(SQLEnum(ParticipantType), default=ParticipantType.MAIN)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="participants")


class Review(Base):
    """Модель отзыва."""

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    # Отзыв
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    comment: Mapped[str | None] = mapped_column(Text)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="reviews")
    user: Mapped["User"] = relationship("User", back_populates="reviews")


class AiLog(Base):
    """Модель лога AI обработки."""

    __tablename__ = "ai_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)

    # AI провайдер
    provider: Mapped[AiProvider] = mapped_column(SQLEnum(AiProvider), nullable=False)
    task_id: Mapped[str | None] = mapped_column(String(255))

    # Статус и ошибки
    status: Mapped[AiLogStatus] = mapped_column(SQLEnum(AiLogStatus), default=AiLogStatus.PENDING)
    error_message: Mapped[str | None] = mapped_column(Text)
    tokens_used: Mapped[int | None] = mapped_column(Integer)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="ai_logs")
