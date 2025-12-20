from dataclasses import dataclass
from datetime import datetime, date, time
from typing import Optional, List
from utils import *


@dataclass
class Order:
    id: int
    order_uuid: str
    user_id: int
    tariff: TariffType
    style: StyleType
    status: OrderStatus
    amount: float
    currency: Currency
    payment_method: Optional[PaymentMethod]
    payment_id: Optional[str]
    manus_task_id: Optional[str]
    pdf_url: Optional[str]
    created_at: datetime
    paid_at: Optional[datetime]
    completed_at: Optional[datetime]


@dataclass
class OrderParticipant:
    id: int
    order_id: int
    full_name: str
    birth_date: date
    birth_time: Optional[time]
    birth_place: Optional[str]
    participant_type: ParticipantType


@dataclass
class Review:
    id: int
    order_id: int
    user_id: int
    rating: Rating
    comment: Optional[str]
    created_at: datetime


@dataclass
class AiLog:
    id: int
    order_id: int
    provider: AiProvider
    task_id: Optional[str]
    status: AiLogStatus
    error_message: Optional[str]
    tokens_used: Optional[int]
    created_at: datetime