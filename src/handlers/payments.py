"""Обработчики платежей."""
import logging
from decimal import Decimal

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Order, User
from utils.enums import OrderStatus, PaymentMethod

logger = logging.getLogger(__name__)

router = Router()


def get_payment_keyboard(order_uuid: str, amount: Decimal) -> InlineKeyboardMarkup:
    """
    Создание клавиатуры для выбора способа оплаты.

    Args:
        order_uuid: UUID заказа
        amount: Сумма заказа

    Returns:
        InlineKeyboardMarkup: Клавиатура с вариантами оплаты
    """
    # Конвертируем рубли в звёзды Telegram (1₽ = 1 звезда для примера)
    stars_amount = int(amount)

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"⭐️ Telegram Stars ({stars_amount} ⭐️)",
            callback_data=f"pay_stars:{order_uuid}"
        )],
        [InlineKeyboardButton(
            text=f"💳 ЮKassa ({amount}₽)",
            callback_data=f"pay_yookassa:{order_uuid}"
        )],
    ])


@router.callback_query(F.data.startswith("pay_stars:"))
async def process_telegram_stars_payment(callback: CallbackQuery, session: AsyncSession):
    """
    Обработка оплаты через Telegram Stars.

    Args:
        callback: Callback от inline кнопки
        session: Сессия БД
    """
    order_uuid = callback.data.split(":")[1]

    # Получаем заказ
    result = await session.execute(
        select(Order).where(Order.order_uuid == order_uuid)
    )
    order = result.scalar_one_or_none()

    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    if order.status != OrderStatus.PENDING:
        await callback.answer("❌ Заказ уже оплачен или отменён", show_alert=True)
        return

    # Конвертируем сумму в звёзды (1₽ = 1 звезда)
    stars_amount = int(order.amount)

    try:
        # Отправляем invoice для Telegram Stars
        await callback.message.answer_invoice(
            title=f"Нумерологический отчёт - {order.tariff.value}",
            description=f"Оплата заказа #{order_uuid[:8]}",
            payload=f"order_{order_uuid}",
            provider_token="",  # Пустой токен для Telegram Stars
            currency="XTR",  # XTR - валюта для Telegram Stars
            prices=[
                LabeledPrice(label=f"Тариф {order.tariff.value}", amount=stars_amount)
            ]
        )

        await callback.answer("✅ Счёт на оплату отправлен")
        logger.info(f"Отправлен invoice Telegram Stars для заказа {order_uuid}")

    except Exception as e:
        logger.error(f"Ошибка при создании invoice: {e}")
        await callback.answer("❌ Ошибка при создании счёта", show_alert=True)


@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery, session: AsyncSession):
    """
    Обработка pre-checkout query от Telegram.

    Args:
        pre_checkout_query: Pre-checkout query
        session: Сессия БД
    """
    # Извлекаем order_uuid из payload
    payload = pre_checkout_query.invoice_payload
    if not payload.startswith("order_"):
        await pre_checkout_query.answer(ok=False, error_message="Неверный payload")
        return

    order_uuid = payload.replace("order_", "")

    # Проверяем заказ
    result = await session.execute(
        select(Order).where(Order.order_uuid == order_uuid)
    )
    order = result.scalar_one_or_none()

    if not order or order.status != OrderStatus.PENDING:
        await pre_checkout_query.answer(
            ok=False,
            error_message="Заказ не найден или уже оплачен"
        )
        return

    await pre_checkout_query.answer(ok=True)
    logger.info(f"Pre-checkout подтверждён для заказа {order_uuid}")


@router.message(F.successful_payment)
async def process_successful_payment(message: Message, session: AsyncSession):
    """
    Обработка успешной оплаты через Telegram Stars.

    Args:
        message: Сообщение с successful_payment
        session: Сессия БД
    """
    payment_info = message.successful_payment
    payload = payment_info.invoice_payload
    order_uuid = payload.replace("order_", "")

    # Получаем заказ
    result = await session.execute(
        select(Order).where(Order.order_uuid == order_uuid)
    )
    order = result.scalar_one_or_none()

    if not order:
        await message.answer("❌ Ошибка: заказ не найден")
        return

    # Обновляем статус заказа
    from datetime import datetime
    order.status = OrderStatus.PAID
    order.payment_method = PaymentMethod.TELEGRAM_STARS
    order.payment_id = payment_info.telegram_payment_charge_id
    order.paid_at = datetime.utcnow()

    await session.commit()

    await message.answer(
        f"✅ <b>Оплата успешна!</b>\n\n"
        f"Заказ #{order_uuid[:8]}\n"
        f"Сумма: {payment_info.total_amount} ⭐️\n\n"
        f"⚙️ Ваш отчёт генерируется...\n"
        f"Это займёт 10-15 минут.\n\n"
        f"Мы отправим вам уведомление, когда отчёт будет готов.",
        parse_mode="HTML"
    )

    logger.info(f"Оплата Telegram Stars успешна для заказа {order_uuid}")

    # TODO: Запустить генерацию AI отчёта
    from services.ai_service import start_ai_generation
    await start_ai_generation(order.id, session, message.bot)


@router.callback_query(F.data.startswith("pay_yookassa:"))
async def process_yookassa_payment(callback: CallbackQuery, session: AsyncSession):
    """
    Обработка оплаты через ЮKassa.

    Args:
        callback: Callback от inline кнопки
        session: Сессия БД
    """
    order_uuid = callback.data.split(":")[1]

    # Получаем заказ
    result = await session.execute(
        select(Order).where(Order.order_uuid == order_uuid)
    )
    order = result.scalar_one_or_none()

    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    if order.status != OrderStatus.PENDING:
        await callback.answer("❌ Заказ уже оплачен или отменён", show_alert=True)
        return

    # TODO: Создать платёж в ЮKassa
    await callback.message.answer(
        "💳 <b>Оплата через ЮKassa</b>\n\n"
        "Функция в разработке.\n"
        "Пока используйте Telegram Stars.",
        parse_mode="HTML"
    )

    await callback.answer()
    logger.info(f"Запрос оплаты ЮKassa для заказа {order_uuid}")
