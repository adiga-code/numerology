"""Сервис для запуска AI генерации отчётов."""
import logging
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot

from database.models import Order, OrderParticipant, AiLog
from utils.enums import OrderStatus, AiProvider, AiLogStatus
from services.n8n_client import N8nClient
from services.report_generator import start_report_generation
from config import Config

logger = logging.getLogger(__name__)


async def start_ai_generation(order_id: int, session: AsyncSession, bot: Bot, db_manager=None):
    """
    Запуск генерации AI отчёта после оплаты (асинхронно через N8N).

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
            }
            for p in participants
        ]

        # Инициализируем N8N клиент
        config = Config()

        if not config.N8N_WEBHOOK_URL:
            raise Exception("N8N_WEBHOOK_URL не настроен в .env")

        if not config.N8N_STATUS_URL:
            raise Exception("N8N_STATUS_URL не настроен в .env")

        n8n_client = N8nClient(
            webhook_url=config.N8N_WEBHOOK_URL,
            status_url=config.N8N_STATUS_URL,
            secret_token=config.N8N_SECRET_TOKEN
        )

        # Создаём AI лог
        ai_log = AiLog(
            order_id=order.id,
            provider=AiProvider.GPT4,  # Используем GPT4 как провайдер (N8N использует GPT)
            status=AiLogStatus.PENDING
        )
        session.add(ai_log)
        await session.commit()

        # Запускаем генерацию через N8N (асинхронно)
        logger.info(f"Запуск AI генерации для заказа {order.id}")
        task_id = await start_report_generation(
            n8n_client=n8n_client,
            order_id=order.id,
            tariff=order.tariff.value,
            style=order.style.value,
            participants=participants_data
        )

        # Уведомляем пользователя что отчёт генерируется
        await bot.send_message(
            chat_id=user.telegram_id,
            text=(
                f"⏳ <b>Генерация отчёта началась</b>\n\n"
                f"Заказ: <code>{order.order_uuid}</code>\n"
                f"Тариф: {order.tariff.value}\n"
                f"Стиль: {order.style.value}\n\n"
                f"Отчёт будет готов через несколько минут.\n"
                f"Мы отправим его автоматически! 🔮"
            ),
            parse_mode="HTML"
        )

        # Запускаем polling для проверки статуса таска
        from services.task_polling import poll_task_status
        import asyncio

        logger.info(f"Запуск polling для таска {task_id} (заказ {order.id})")

        # Получаем db_manager (если не передан, создаем новый)
        if db_manager is None:
            from database import DatabaseManager
            db_manager = DatabaseManager(config.DATABASE_URL)

        asyncio.create_task(
            poll_task_status(
                task_id=task_id,
                order_id=order.id,
                n8n_client=n8n_client,
                db_manager=db_manager,
                bot=bot,
                poll_interval=30,  # Проверка каждые 30 секунд
                timeout_minutes=20  # Таймаут через 20 минут
            )
        )

        logger.info(
            f"Генерация запущена для заказа {order.id}, "
            f"task_id: {task_id}, запущен polling"
        )

    except Exception as e:
        logger.error(f"Ошибка при запуске генерации для заказа {order_id}: {e}")

        # Обновляем статус на failed
        order.status = OrderStatus.FAILED

        # Обновляем AI лог
        if 'ai_log' in locals():
            ai_log.status = AiLogStatus.FAILED
            ai_log.error_message = str(e)

        await session.commit()

        # Уведомляем пользователя
        await bot.send_message(
            chat_id=user.telegram_id,
            text=(
                f"❌ <b>Ошибка при запуске генерации отчёта</b>\n\n"
                f"Заказ: <code>{order.order_uuid}</code>\n\n"
                f"Произошла ошибка: {str(e)}\n\n"
                f"Свяжитесь с поддержкой для решения проблемы."
            ),
            parse_mode="HTML"
        )

        # TODO: Автоматический возврат средств через ЮKassa API
