"""Сервис для запуска AI генерации отчётов."""
import logging
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot

from database.models import Order, OrderParticipant, AiLog
from utils.enums import OrderStatus, AiProvider, AiLogStatus
from services.manus import ManusClient
from services.ai_fallback import generate_with_fallback
from services.gpt_with_book import OptimizedGPTClient
from services.pdf_generator import generate_pdf
from config import Config

logger = logging.getLogger(__name__)

# Глобальный экземпляр GPT клиента с книгой (инициализируется при старте)
_gpt_book_client: OptimizedGPTClient | None = None


async def initialize_gpt_with_book(api_key: str):
    """
    Инициализация GPT клиента с книгой при старте приложения.

    Args:
        api_key: API ключ OpenAI
    """
    global _gpt_book_client

    try:
        logger.info("Инициализация GPT клиента с книгой...")
        _gpt_book_client = OptimizedGPTClient(api_key=api_key)
        await _gpt_book_client.initialize()
        logger.info("GPT клиент с книгой готов к работе")
    except Exception as e:
        logger.error(f"Не удалось инициализировать GPT клиент с книгой: {e}")
        _gpt_book_client = None


def get_gpt_book_client() -> OptimizedGPTClient | None:
    """
    Получить глобальный экземпляр GPT клиента с книгой.

    Returns:
        OptimizedGPTClient | None: Клиент или None если не инициализирован
    """
    return _gpt_book_client


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
                "birth_date": p.birth_date.strftime("%d.%m.%Y"),
                "birth_time": p.birth_time.strftime("%H:%M") if p.birth_time else None,
                "birth_place": p.birth_place
            }
            for p in participants
        ]

        # Получаем конфигурацию
        config = Config()

        # Проверяем наличие GPT клиента с книгой
        gpt_book_client = get_gpt_book_client()

        # Инициализируем дополнительные клиенты для fallback
        manus_client = None
        if config.MANUS_API_KEY:
            manus_client = ManusClient(config.MANUS_API_KEY, config.WEBHOOK_DOMAIN)

        if not gpt_book_client and not manus_client:
            raise Exception(
                "Не настроен ни один AI провайдер. "
                "Добавьте OPENAI_API_KEY или MANUS_API_KEY в .env"
            )

        # Создаём AI лог
        ai_log = AiLog(
            order_id=order.id,
            provider=AiProvider.GPT4 if gpt_book_client else AiProvider.MANUS,
            status=AiLogStatus.PENDING
        )
        session.add(ai_log)
        await session.commit()

        # Генерируем отчёт
        logger.info(f"Запуск AI генерации для заказа {order.id}")

        result_text = None
        provider = None

        # Приоритет 1: GPT с книгой
        if gpt_book_client:
            try:
                logger.info(f"Генерация через GPT-4 с книгой для заказа {order.id}")
                result_text = await gpt_book_client.generate_report(
                    tariff=order.tariff.value,
                    style=order.style.value,
                    participants=participants_data
                )
                provider = "gpt4"
                logger.info(f"Отчёт успешно сгенерирован через GPT-4 с книгой")
            except Exception as e:
                logger.error(f"Ошибка GPT-4 с книгой: {e}")

        # Приоритет 2: Fallback на Manus
        if not result_text and manus_client:
            try:
                logger.info(f"Fallback на Manus для заказа {order.id}")
                from services.manus import build_numerology_prompt
                prompt = build_numerology_prompt(
                    tariff=order.tariff.value,
                    style=order.style.value,
                    participants=participants_data
                )
                manus_result = await manus_client.create_task(prompt, order.id)
                result_text = manus_result.get("task_id")
                provider = "manus"
                logger.info(f"Задача отправлена в Manus: {result_text}")
            except Exception as e:
                logger.error(f"Ошибка Manus: {e}")

        if not result_text:
            raise Exception("Все AI провайдеры недоступны")

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
                f"Мы автоматически вернём средства.\n"
                f"Приносим извинения за неудобства."
            ),
            parse_mode="HTML"
        )

        # TODO: Автоматический возврат средств через ЮKassa API
