"""Перечисления для типов данных."""
from enum import Enum


class TariffType(str, Enum):
    """Типы тарифов."""
    QUICK = "quick"  # Быстрый взгляд (500₽, 1 участник)
    DEEP = "deep"  # Глубокий анализ (1500₽, 1 участник)
    PAIR = "pair"  # Парный Оракул (2000₽, 2 участника)
    FAMILY = "family"  # Семейный Оракул (3000₽, 3-5 участников)


class StyleType(str, Enum):
    """Стили отчётов."""
    ANALYTICAL = "analytical"  # Аналитический
    SHAMANIC = "shamanic"  # Шаманский


class OrderStatus(str, Enum):
    """Статусы заказа."""
    PENDING = "pending"  # Ожидает оплаты
    PAID = "paid"  # Оплачен
    PROCESSING = "processing"  # В обработке
    COMPLETED = "completed"  # Завершён
    FAILED = "failed"  # Ошибка
    REFUNDED = "refunded"  # Возврат средств


class Currency(str, Enum):
    """Валюты."""
    RUB = "RUB"


class PaymentMethod(str, Enum):
    """Методы оплаты."""
    YOOKASSA = "yookassa"
    TELEGRAM_STARS = "telegram_stars"


class ParticipantType(str, Enum):
    """Типы участников."""
    MAIN = "main"  # Основной заказчик
    PARTNER = "partner"  # Партнёр
    FAMILY_MEMBER = "family_member"  # Член семьи


class Rating(int, Enum):
    """Оценки отзывов."""
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5


class AiProvider(str, Enum):
    """AI провайдеры."""
    MANUS = "manus"
    GPT4 = "gpt4"
    GEMINI = "gemini"


class AiLogStatus(str, Enum):
    """Статусы AI обработки."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
