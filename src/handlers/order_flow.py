"""Обработчики флоу создания заказа."""
import logging
from datetime import datetime
from decimal import Decimal

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Order, OrderParticipant
from utils.enums import TariffType, StyleType, OrderStatus, Currency, ParticipantType
from utils.states import OrderFlow

logger = logging.getLogger(__name__)

router = Router()

# Цены тарифов
TARIFF_PRICES = {
    TariffType.QUICK: Decimal("500.00"),
    TariffType.DEEP: Decimal("1500.00"),
    TariffType.PAIR: Decimal("2000.00"),
    TariffType.FAMILY: Decimal("3000.00"),
}


def get_tariff_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры для выбора тарифа."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌟 Быстрый взгляд (500₽)", callback_data="tariff:quick")],
        [InlineKeyboardButton(text="🔍 Глубокий анализ (1500₽)", callback_data="tariff:deep")],
        [InlineKeyboardButton(text="💑 Парный Оракул (2000₽)", callback_data="tariff:pair")],
        [InlineKeyboardButton(text="👨‍👩‍👧‍👦 Семейный Оракул (3000₽)", callback_data="tariff:family")],
    ])


def get_style_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры для выбора стиля."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 Аналитический", callback_data="style:analytical")],
        [InlineKeyboardButton(text="🔮 Шаманский", callback_data="style:shamanic")],
    ])


def get_skip_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры с кнопкой 'Пропустить'."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip")],
    ])


@router.message(Command("new"))
async def start_order(message: Message, state: FSMContext):
    """
    Начало создания нового заказа.

    Args:
        message: Сообщение от пользователя
        state: FSM контекст
    """
    await state.clear()
    await state.set_state(OrderFlow.choosing_tariff)

    await message.answer(
        "🔮 <b>Создание нового заказа</b>\n\n"
        "Выберите тариф:",
        reply_markup=get_tariff_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(OrderFlow.choosing_tariff, F.data.startswith("tariff:"))
async def process_tariff(callback: CallbackQuery, state: FSMContext):
    """
    Обработка выбора тарифа.

    Args:
        callback: Callback от inline кнопки
        state: FSM контекст
    """
    tariff = callback.data.split(":")[1]
    await state.update_data(tariff=tariff, participants_data=[], current_participant=0)

    tariff_names = {
        "quick": "Быстрый взгляд",
        "deep": "Глубокий анализ",
        "pair": "Парный Оракул",
        "family": "Семейный Оракул"
    }

    # Определяем количество участников
    participants_count = {
        "quick": 1,
        "deep": 1,
        "pair": 2,
        "family": None  # Спросим у пользователя
    }

    await state.update_data(participants_count=participants_count[tariff])

    if tariff == "family":
        await state.set_state(OrderFlow.asking_family_count)
        await callback.message.edit_text(
            f"✅ Выбран тариф: <b>{tariff_names[tariff]}</b>\n\n"
            "Сколько участников будет в анализе? (от 3 до 5)\n"
            "Введите число:",
            parse_mode="HTML"
        )
    else:
        await state.set_state(OrderFlow.entering_full_name)
        participant_num = 1
        await callback.message.edit_text(
            f"✅ Выбран тариф: <b>{tariff_names[tariff]}</b>\n\n"
            f"📝 <b>Участник {participant_num}</b>\n\n"
            "Введите ФИО:",
            parse_mode="HTML"
        )

    await callback.answer()


@router.message(OrderFlow.asking_family_count, F.text.isdigit())
async def process_family_count(message: Message, state: FSMContext):
    """
    Обработка количества участников для семейного тарифа.

    Args:
        message: Сообщение от пользователя
        state: FSM контекст
    """
    count = int(message.text)

    if count < 3 or count > 5:
        await message.answer("❌ Количество участников должно быть от 3 до 5. Попробуйте снова:")
        return

    await state.update_data(participants_count=count)
    await state.set_state(OrderFlow.entering_full_name)

    await message.answer(
        f"✅ Количество участников: {count}\n\n"
        "📝 <b>Участник 1</b>\n\n"
        "Введите ФИО:",
        parse_mode="HTML"
    )


@router.message(OrderFlow.entering_full_name, F.text)
async def process_full_name(message: Message, state: FSMContext):
    """
    Обработка ввода ФИО.

    Args:
        message: Сообщение от пользователя
        state: FSM контекст
    """
    data = await state.get_data()
    participants_data = data.get("participants_data", [])

    # Создаём новую запись участника
    participant_data = {"full_name": message.text}

    if len(participants_data) <= data.get("current_participant", 0):
        participants_data.append(participant_data)
    else:
        participants_data[data["current_participant"]]["full_name"] = message.text

    await state.update_data(participants_data=participants_data)
    await state.set_state(OrderFlow.entering_birth_date)

    await message.answer(
        f"✅ ФИО: {message.text}\n\n"
        "Введите дату рождения в формате ДД.ММ.ГГГГ\n"
        "Например: 25.12.1990"
    )


@router.message(OrderFlow.entering_birth_date, F.text)
async def process_birth_date(message: Message, state: FSMContext):
    """
    Обработка ввода даты рождения.

    Args:
        message: Сообщение от пользователя
        state: FSM контекст
    """
    try:
        birth_date = datetime.strptime(message.text, "%d.%m.%Y").date()
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ, например: 25.12.1990")
        return

    data = await state.get_data()
    participants_data = data["participants_data"]
    participants_data[data["current_participant"]]["birth_date"] = message.text

    await state.update_data(participants_data=participants_data)
    await state.set_state(OrderFlow.entering_birth_time)

    await message.answer(
        f"✅ Дата рождения: {message.text}\n\n"
        "Введите время рождения в формате ЧЧ:ММ\n"
        "Например: 14:30",
        reply_markup=get_skip_keyboard()
    )


@router.message(OrderFlow.entering_birth_time, F.text)
async def process_birth_time(message: Message, state: FSMContext):
    """
    Обработка ввода времени рождения.

    Args:
        message: Сообщение от пользователя
        state: FSM контекст
    """
    try:
        birth_time = datetime.strptime(message.text, "%H:%M").time()
    except ValueError:
        await message.answer("❌ Неверный формат времени. Используйте ЧЧ:ММ, например: 14:30")
        return

    data = await state.get_data()
    participants_data = data["participants_data"]

        participant = OrderParticipant(

            order_id=order.id,

            full_name=participant_data["full_name"],

            birth_time=birth_time,
            birth_place=participant_data.get("birth_place"),
            participant_type=participant_type
        )
        session.add(participant)

    await session.commit()

    await state.clear()

    # Переход к оплате
    from handlers.payments import get_payment_keyboard

    await callback.message.edit_text(
        f"✅ <b>Заказ создан!</b>\n\n"
        f"Номер заказа: <code>{order.order_uuid}</code>\n"
        f"Тариф: {data['tariff']}\n"
        f"Стиль: {style_names[style]}\n"
        f"Участников: {len(data['participants_data'])}\n"
        f"Сумма: {order.amount}₽\n\n"
        f"💳 <b>Выберите способ оплаты:</b>",
        reply_markup=get_payment_keyboard(order.order_uuid, order.amount),
        parse_mode="HTML"
    )

    await callback.answer()

    logger.info(f"Создан заказ {order.order_uuid} для пользователя {user.telegram_id}")
