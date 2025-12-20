
from enum import Enum, IntEnum


class TariffType(str, Enum):
    """Типы тарифов"""
    QUICK = "quick"
    DEEP = "deep"
    PAIR = "pair"
    FAMILY = "family"


class StyleType(str, Enum):
    """Стили анализа"""
    ANALYTICAL = "analytical"
    SHAMANIC = "shamanic"


class OrderStatus(str, Enum):
    """Статусы заказа"""
    PENDING = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class Currency(str, Enum):
    """Валюты"""
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"


class PaymentMethod(str, Enum):
    """Методы оплаты"""
    YOOKASSA = "yookassa"
    TELEGRAM_STARS = "telegram_stars"


class ParticipantType(str, Enum):
    """Типы участников заказа"""
    MAIN = "main"
    PARTNER = "partner"
    FAMILY_MEMBER = "family_member"


class AiProvider(str, Enum):
    """Провайдеры AI"""
    MANUS = "manus"
    GPT4 = "gpt4"
    GEMINI = "gemini"


class AiLogStatus(str, Enum):
    """Статусы AI логов"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class Rating(IntEnum):
    """Рейтинги отзывов"""
    ONE_STAR = 1
    TWO_STARS = 2
    THREE_STARS = 3
    FOUR_STARS = 4
    FIVE_STARS = 5

    @classmethod
    def is_valid(cls, value: int) -> bool:
        """Проверка валидности рейтинга"""
        return value in [r.value for r in cls]