"""Обработчики команд бота."""
import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from utils.states import OrderFlow

logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext, session: AsyncSession):
    """
    Обработчик команды /start.

    Args:
        message: Сообщение от пользователя
        state: FSM контекст
        session: Сессия БД
    """
    await state.clear()

    # Получаем или создаём пользователя
    result = await session.execute(
        select(User).where(User.telegram_id == message.from_user.id)
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
        session.add(user)
        await session.commit()
        logger.info(f"Создан новый пользователь: {user.telegram_id}")

    await message.answer(
        "🔮 <b>Добро пожаловать в бота по нумерологии!</b>\n\n"
        "Я помогу вам создать персонализированный нумерологический отчёт.\n\n"
        "Доступные команды:\n"
        "/new - Создать новый заказ\n"
        "/history - История заказов\n"
        "/help - Справка\n"
        "/support - Поддержка",
        parse_mode="HTML"
    )


@router.message(Command("help"))
async def help_handler(message: Message):
    """Обработчик команды /help."""
    await message.answer(
        "📖 <b>Справка по использованию бота</b>\n\n"
        "<b>Тарифы:</b>\n"
        "🌟 Быстрый взгляд (500₽) - краткий анализ, 5-7 стр\n"
        "🔍 Глубокий анализ (1500₽) - полный анализ, 15-20 стр\n"
        "💑 Парный Оракул (2000₽) - совместимость пары, 15-25 стр\n"
        "👨‍👩‍👧‍👦 Семейный Оракул (3000₽) - семейный анализ, 30-50 стр\n\n"
        "<b>Команды:</b>\n"
        "/new - Создать новый заказ\n"
        "/history - Посмотреть историю заказов\n"
        "/download - Скачать отчёт повторно\n"
        "/support - Связаться с поддержкой\n"
        "/cancel - Отменить текущий заказ",
        parse_mode="HTML"
    )


@router.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext):
    """Обработчик команды /cancel."""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нет активного заказа для отмены.")
        return

    await state.clear()
    await message.answer("❌ Текущий заказ отменён.")


@router.message(Command("support"))
async def support_handler(message: Message):
    """Обработчик команды /support."""
    await message.answer(
        "💬 <b>Поддержка</b>\n\n"
        "По всем вопросам обращайтесь:\n"
        "📧 Email: support@example.com\n"
        "Telegram: @support",
        parse_mode="HTML"
    )


@router.message(Command("history"))
async def history_handler(message: Message, session: AsyncSession):
    """Обработчик команды /history."""
    from database.models import Order

    result = await session.execute(
        select(Order)
        .join(User)
        .where(User.telegram_id == message.from_user.id)
        .order_by(Order.created_at.desc())
        .limit(10)
    )
    orders = result.scalars().all()

    if not orders:
        await message.answer("У вас пока нет заказов.")
        return

    text = "📋 <b>Ваши последние заказы:</b>\n\n"
    for order in orders:
        status_emoji = {
            "pending": "⏳",
            "paid": "💳",
            "processing": "⚙️",
            "completed": "✅",
            "failed": "❌",
            "refunded": "↩️"
        }.get(order.status.value, "❓")

        text += (
            f"{status_emoji} <b>Заказ #{order.order_uuid[:8]}</b>\n"
            f"Тариф: {order.tariff.value}\n"
            f"Статус: {order.status.value}\n"
            f"Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        )

        if order.status.value == "completed" and order.pdf_url:
            text += f"Скачать: /download {order.order_uuid[:8]}\n"

        text += "\n"

    await message.answer(text, parse_mode="HTML")


@router.message(Command("download"))
async def download_handler(message: Message, session: AsyncSession):
    """
    Обработчик команды /download для повторного скачивания отчёта.

    Использование: /download <order_id> или /download_<order_id>
    """
    from database.models import Order
    from aiogram.types import FSInputFile
    from pathlib import Path

    # Получаем order_id из команды
    command_parts = message.text.split()

    # Поддержка форматов: /download ORDER_ID или /download_ORDER_ID
    if len(command_parts) > 1:
        order_id = command_parts[1]
    elif message.text.startswith("/download_"):
        order_id = message.text.replace("/download_", "").strip()
    else:
        await message.answer(
            "❌ <b>Неверный формат команды</b>\n\n"
            "Используйте: /download &lt;order_id&gt;\n"
            "Например: /download a1b2c3d4\n\n"
            "Посмотрите список заказов: /history",
            parse_mode="HTML"
        )
        return

    # Поиск заказа
    result = await session.execute(
        select(Order)
        .join(User)
        .where(
            User.telegram_id == message.from_user.id,
            Order.order_uuid.like(f"{order_id}%")
        )
    )
    order = result.scalar_one_or_none()

    if not order:
        await message.answer(
            "❌ <b>Заказ не найден</b>\n\n"
            "Проверьте номер заказа или посмотрите историю: /history",
            parse_mode="HTML"
        )
        return

    if order.status.value != "completed":
        await message.answer(
            f"⏳ <b>Заказ ещё не готов</b>\n\n"
            f"Текущий статус: {order.status.value}\n"
            f"Заказ: <code>{order.order_uuid}</code>",
            parse_mode="HTML"
        )
        return

    if not order.pdf_url or not Path(order.pdf_url).exists():
        await message.answer(
            "❌ <b>Файл отчёта не найден</b>\n\n"
            "Обратитесь в поддержку: /support",
            parse_mode="HTML"
        )
        logger.error(f"PDF файл не найден для заказа {order.order_uuid}: {order.pdf_url}")
        return

    try:
        # Отправляем PDF
        await message.answer_document(
            document=FSInputFile(order.pdf_url),
            caption=(
                f"📄 <b>Ваш нумерологический отчёт</b>\n\n"
                f"Заказ: <code>{order.order_uuid}</code>\n"
                f"Тариф: {order.tariff.value}\n"
                f"Дата: {order.completed_at.strftime('%d.%m.%Y %H:%M')}"
            ),
            parse_mode="HTML"
        )
        logger.info(f"Отчёт повторно отправлен для заказа {order.order_uuid} пользователю {message.from_user.id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке PDF для заказа {order.order_uuid}: {e}")
        await message.answer(
            "❌ <b>Ошибка при отправке файла</b>\n\n"
            "Попробуйте позже или обратитесь в поддержку: /support",
            parse_mode="HTML"
        )
