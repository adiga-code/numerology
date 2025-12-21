"""Сервис для запуска AI генерации отчётов."""
import logging
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot

from database.models import Order, OrderParticipant, AiLog
from utils.enums import OrderStatus, AiProvider, AiLogStatus
from services.manus import ManusClient, build_numerology_prompt
from services.ai_fallback import GPT4Client, generate_with_fallback
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
        # Получаем заказ с участниками
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one()

        result = await session.execute(
            select(OrderParticipant).where(OrderParticipant.order_id == order_id)
        )
        participants = result.scalars().all()

        # Обновляем статус
        order.status = OrderStatus.PROCESSING
        await session.commit()

        # Строим промпт
        participants_data = [
            {
                "full_name": p.full_name,
                "birth_date": p.birth_date.strftime("%d.%m.%Y"),
                "birth_time": p.birth_time.strftime("%H:%M") if p.birth_time else None,
                "birth_place": p.birth_place
            }
            for p in participants
        ]

        prompt = build_numerology_prompt(
            tariff=order.tariff.value,
            style=order.style.value,
            participants=participants_data
        )

        # Инициализируем клиенты
        config = Config()
        manus_client = ManusClient(config.MANUS_API_KEY, config.WEBHOOK_DOMAIN) if config.MANUS_API_KEY else None
        gpt4_client = GPT4Client(config.OPENAI_API_KEY) if config.OPENAI_API_KEY else None

        # Создаём AI лог
        ai_log = AiLog(
            order_id=order.id,
            provider=AiProvider.GPT4,  # Начинаем с GPT-4 для тестирования
            status=AiLogStatus.PENDING
        )
        session.add(ai_log)
        await session.commit()

        # Генерируем отчёт
        logger.info(f"Запуск AI генерации для заказа {order.id}")
        result_text, provider = await generate_with_fallback(
            prompt=prompt,
            manus_client=manus_client,
            gpt4_client=gpt4_client,
            order_id=order.id
        )

        # Обновляем AI лог
        ai_log.provider = AiProvider(provider)
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

        user = order.user
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

        # TODO: Запланировать запрос отзыва через 1 час

    except Exception as e:
        logger.error(f"Ошибка при генерации AI отчёта для заказа {order_id}: {e}")

        # Обновляем статус на failed
        order.status = OrderStatus.FAILED

        # Обновляем AI лог
        ai_log.status = AiLogStatus.FAILED
        ai_log.error_message = str(e)
        await session.commit()

        # Уведомляем пользователя
        user = order.user
        await bot.send_message(
            chat_id=user.telegram_id,
            text=(
                f"❌ <b>Ошибка при генерации отчёта</b>\n\n"
                f"Заказ: <code>{order.order_uuid}</code>\n\n"
                f"Мы автоматически вернём средства.\n"
                f"Приносим извинения за неудобства."
            ),
            parse_mode="HTML"
        )

        # TODO: Автоматический возврат средств через ЮKassa API
