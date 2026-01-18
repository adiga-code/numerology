"""Polling механизм для проверки статуса N8N тасков."""
import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Bot

from services.n8n_client import N8nClient
from services.n8n_result_handler import handle_n8n_result, handle_n8n_error
from database import DatabaseManager

logger = logging.getLogger(__name__)


async def poll_task_status(
    task_id: str,
    order_id: int,
    n8n_client: N8nClient,
    db_manager: DatabaseManager,
    bot: Bot,
    poll_interval: int = 30,
    timeout_minutes: int = 20
) -> None:
    """
    Периодически проверяет статус таска в N8N до получения результата.

    Args:
        task_id: ID таска в N8N
        order_id: ID заказа в базе данных
        n8n_client: Клиент для запросов к N8N
        db_manager: Менеджер базы данных для создания сессий
        bot: Telegram бот для отправки сообщений
        poll_interval: Интервал проверки в секундах (по умолчанию 30)
        timeout_minutes: Максимальное время ожидания в минутах (по умолчанию 20)
    """
    start_time = datetime.utcnow()
    timeout = timedelta(minutes=timeout_minutes)
    attempt = 0

    logger.info(
        f"Запуск polling для таска {task_id} (order {order_id}), "
        f"интервал {poll_interval}s, таймаут {timeout_minutes}m"
    )

    try:
        while True:
            attempt += 1
            elapsed = datetime.utcnow() - start_time

            # Проверяем таймаут
            if elapsed > timeout:
                logger.error(
                    f"Таймаут polling для таска {task_id} (order {order_id}) "
                    f"после {elapsed.total_seconds():.0f}s и {attempt} попыток"
                )
                async with db_manager.get_session() as session:
                    await handle_n8n_error(
                        order_id,
                        f"Превышено время ожидания результата ({timeout_minutes} минут). "
                        f"Генерация отчёта не завершилась вовремя.",
                        session,
                        bot
                    )
                return

            # Проверяем статус таска
            try:
                logger.info(
                    f"Polling попытка {attempt} для таска {task_id} (order {order_id}), "
                    f"прошло {elapsed.total_seconds():.0f}s"
                )

                result = await n8n_client.check_status(task_id)
                status = result.get("status")

                if status == "completed":
                    logger.info(
                        f"Таск {task_id} (order {order_id}) завершён успешно "
                        f"после {attempt} попыток и {elapsed.total_seconds():.0f}s"
                    )

                    # Проверяем наличие данных
                    if "data" not in result:
                        logger.error(
                            f"Таск {task_id} (order {order_id}) завершён, "
                            f"но нет поля 'data' в ответе: {result}"
                        )
                        async with db_manager.get_session() as session:
                            await handle_n8n_error(
                                order_id,
                                "Получен пустой результат от сервиса генерации",
                                session,
                                bot
                            )
                        return

                    # Обрабатываем успешный результат
                    async with db_manager.get_session() as session:
                        await handle_n8n_result(
                            order_id,
                            result["data"],
                            session,
                            bot
                        )
                    return

                elif status == "failed":
                    error_message = result.get("error", "Неизвестная ошибка")
                    logger.error(
                        f"Таск {task_id} (order {order_id}) завершён с ошибкой "
                        f"после {attempt} попыток: {error_message}"
                    )

                    # Обрабатываем ошибку
                    async with db_manager.get_session() as session:
                        await handle_n8n_error(
                            order_id,
                            error_message,
                            session,
                            bot
                        )
                    return

                elif status == "pending":
                    logger.info(
                        f"Таск {task_id} (order {order_id}) ещё в процессе, "
                        f"ожидание {poll_interval}s..."
                    )

                else:
                    logger.warning(
                        f"Неожиданный статус '{status}' для таска {task_id} "
                        f"(order {order_id}): {result}"
                    )

            except Exception as e:
                logger.error(
                    f"Ошибка при проверке статуса таска {task_id} (order {order_id}) "
                    f"на попытке {attempt}: {e}"
                )

                # Проверяем не истёк ли таймаут перед следующей попыткой
                elapsed = datetime.utcnow() - start_time
                if elapsed > timeout:
                    logger.error(
                        f"Таймаут после ошибки проверки для таска {task_id} (order {order_id})"
                    )
                    async with db_manager.get_session() as session:
                        await handle_n8n_error(
                            order_id,
                            f"Ошибка при проверке статуса генерации: {str(e)}",
                            session,
                            bot
                        )
                    return

            # Ждём перед следующей проверкой
            await asyncio.sleep(poll_interval)

    except asyncio.CancelledError:
        logger.info(f"Polling отменён для таска {task_id} (order {order_id})")
        raise

    except Exception as e:
        logger.error(
            f"Критическая ошибка в polling для таска {task_id} (order {order_id}): {e}"
        )
        async with db_manager.get_session() as session:
            await handle_n8n_error(
                order_id,
                f"Критическая ошибка при проверке статуса: {str(e)}",
                session,
                bot
            )
