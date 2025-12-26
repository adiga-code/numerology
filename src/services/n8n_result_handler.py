"""Обработчик результатов генерации от N8N."""
import logging
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot
from aiogram.types import FSInputFile

from database.models import Order, OrderParticipant, AiLog
from utils.enums import OrderStatus, AiLogStatus
from services.pdf_generator import generate_pdf

logger = logging.getLogger(__name__)


async def handle_n8n_result(
    order_id: int,
    text: str,
    session: AsyncSession,
    bot: Bot
) -> None:
    """
    Обработка результата генерации от N8N.

    Args:
        order_id: ID заказа
        text: Сгенерированный текст отчёта
        session: Сессия БД
        bot: Экземпляр бота
    """
    try:
        # Получаем заказ с участниками и пользователем
        from sqlalchemy.orm import selectinload

        result = await session.execute(
            select(Order)
            .options(selectinload(Order.user))
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()

        if not order:
            logger.error(f"Заказ {order_id} не найден при обработке результата от N8N")
            return

        user = order.user

        # Получаем участников
        result = await session.execute(
            select(OrderParticipant).where(OrderParticipant.order_id == order_id)
        )
        participants = result.scalars().all()

        # Логируем статистику ответа
        char_count = len(text)
        word_count = len(text.split())
        estimated_pages = char_count / 2800

        logger.info(
            f"N8N отчёт получен для заказа {order_id}: "
            f"{char_count} символов, {word_count} слов, ~{estimated_pages:.1f} страниц"
        )

        # Обновляем AI лог
        result = await session.execute(
            select(AiLog)
            .where(AiLog.order_id == order_id)
            .order_by(AiLog.id.desc())
            .limit(1)
        )
        ai_log = result.scalar_one_or_none()

        if ai_log:
            ai_log.status = AiLogStatus.SUCCESS
            await session.commit()

        # Генерируем PDF
        logger.info(f"Генерация PDF для заказа {order_id}")
        pdf_path = await generate_pdf(
            order=order,
            participants=participants,
            content=text
        )

        # Обновляем заказ
        order.status = OrderStatus.COMPLETED
        order.pdf_url = pdf_path
        order.completed_at = datetime.utcnow()
        await session.commit()

        # Отправляем PDF пользователю
        await bot.send_document(
            chat_id=user.telegram_id,
            document=FSInputFile(pdf_path),
            caption=(
                f"✅ <b>Ваш нумерологический отчёт готов!</b>\n\n"
                f"Заказ: <code>{order.order_uuid}</code>\n"
                f"Тариф: {order.tariff.value}\n"
                f"Стиль: {order.style.value}\n\n"
                f"Приятного чтения! 🔮"
            ),
            parse_mode="HTML"
        )

        logger.info(f"Отчёт успешно отправлен для заказа {order_id}")

        # Запланировать запрос отзыва через 1 час
        from handlers.reviews import request_review
        import asyncio
        asyncio.create_task(request_review(bot, order_id, user.telegram_id))

    except Exception as e:
        logger.error(f"Ошибка при обработке результата N8N для заказа {order_id}: {e}")
        raise


async def handle_n8n_error(
    order_id: int,
    error_message: str,
    session: AsyncSession,
    bot: Bot
) -> None:
    """
    Обработка ошибки генерации от N8N.

    Args:
        order_id: ID заказа
        error_message: Сообщение об ошибке
        session: Сессия БД
        bot: Экземпляр бота
    """
    try:
        # Получаем заказ
        from sqlalchemy.orm import selectinload

        result = await session.execute(
            select(Order)
            .options(selectinload(Order.user))
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()

        if not order:
            logger.error(f"Заказ {order_id} не найден при обработке ошибки от N8N")
            return

        user = order.user

        logger.error(f"N8N вернул ошибку для заказа {order_id}: {error_message}")

        # Обновляем статус заказа
        order.status = OrderStatus.FAILED
        await session.commit()

        # Обновляем AI лог
        result = await session.execute(
            select(AiLog)
            .where(AiLog.order_id == order_id)
            .order_by(AiLog.id.desc())
            .limit(1)
        )
        ai_log = result.scalar_one_or_none()

        if ai_log:
            ai_log.status = AiLogStatus.FAILED
            ai_log.error_message = error_message
            await session.commit()

        # Уведомляем пользователя
        await bot.send_message(
            chat_id=user.telegram_id,
            text=(
                f"❌ <b>Ошибка при генерации отчёта</b>\n\n"
                f"Заказ: <code>{order.order_uuid}</code>\n\n"
                f"Произошла ошибка: {error_message}\n\n"
                f"Свяжитесь с поддержкой для решения проблемы."
            ),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке ошибки N8N для заказа {order_id}: {e}")
        raise
