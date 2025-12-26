"""Сервис для запуска AI генерации отчётов."""
import logging
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot

from database.models import Order, OrderParticipant, AiLog
from utils.enums import OrderStatus, AiProvider, AiLogStatus
from services.n8n_client import N8nClient
from services.report_generator import generate_report
from services.pdf_generator import generate_pdf
from config import Config

logger = logging.getLogger(__name__)


async def start_ai_generation(order_id: int, session: AsyncSession, bot: Bot):
    """
    Запуск генерации AI отчёта после оплаты.

    Args:
        order_id: ID заказа
        session: Сессия БД
        bot: Экземпляр бота
    """
    try:
        # Получаем заказ с участниками и пользователем (eager loading)
        from sqlalchemy.orm import selectinload

        result = await session.execute(
            select(Order)
            .options(selectinload(Order.user))
            .where(Order.id == order_id)
        )
        order = result.scalar_one()

        # Сохраняем user для использования в exception handler
        user = order.user

        result = await session.execute(
            select(OrderParticipant).where(OrderParticipant.order_id == order_id)
        )
        participants = result.scalars().all()

        # Обновляем статус
        order.status = OrderStatus.PROCESSING
        await session.commit()

        # Подготавливаем данные участников
        participants_data = [
            {
                "full_name": p.full_name,
                "birth_date": p.birth_date,  # Передаем datetime объект
                "birth_time": p.birth_time,  # Передаем datetime объект или None
                "birth_place": p.birth_place
            }
            for p in participants
        ]

        # Инициализируем N8N клиент
        config = Config()

        if not config.N8N_WEBHOOK_URL:
            raise Exception("N8N_WEBHOOK_URL не настроен в .env")

        n8n_client = N8nClient(webhook_url=config.N8N_WEBHOOK_URL)

        # Создаём AI лог
        ai_log = AiLog(
            order_id=order.id,
            provider=AiProvider.GPT4,  # Используем GPT4 как провайдер (N8N использует GPT)
            status=AiLogStatus.PENDING
        )
        session.add(ai_log)
        await session.commit()

        # Генерируем отчёт через N8N
        logger.info(f"Запуск AI генерации для заказа {order.id}")
        result_text = await generate_report(
            n8n_client=n8n_client,
            order_id=order.id,
            tariff=order.tariff.value,
            style=order.style.value,
            participants=participants_data
        )

        # Обновляем AI лог
        ai_log.status = AiLogStatus.SUCCESS
        await session.commit()

        # Генерируем PDF
        logger.info(f"Генерация PDF для заказа {order.id}")
        pdf_path = await generate_pdf(
            order=order,
            participants=participants,
            content=result_text
        )

        # Обновляем заказ
        order.status = OrderStatus.COMPLETED
        order.pdf_url = pdf_path
        order.completed_at = datetime.utcnow()
        await session.commit()

        # Отправляем PDF пользователю
        from aiogram.types import FSInputFile

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

        logger.info(f"Отчёт успешно отправлен для заказа {order.id}")

        # Запланировать запрос отзыва через 1 час
        from handlers.reviews import request_review
        import asyncio
        asyncio.create_task(request_review(bot, order.id, user.telegram_id))

    except Exception as e:
        logger.error(f"Ошибка при генерации AI отчёта для заказа {order_id}: {e}")

        # Обновляем статус на failed
        order.status = OrderStatus.FAILED

        # Обновляем AI лог
        ai_log.status = AiLogStatus.FAILED
        ai_log.error_message = str(e)
        await session.commit()

        # Уведомляем пользователя
        await bot.send_message(
            chat_id=user.telegram_id,
            text=(
                f"❌ <b>Ошибка при генерации отчёта</b>\n\n"
                f"Заказ: <code>{order.order_uuid}</code>\n\n"
                f"Произошла ошибка: {str(e)}\n\n"
                f"Свяжитесь с поддержкой для решения проблемы."
            ),
            parse_mode="HTML"
        )

        # TODO: Автоматический возврат средств через ЮKassa API
