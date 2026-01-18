"""Сервис генерации отчётов через N8N."""
import logging
from typing import List, Dict, Any

from services.prompts import build_numerology_prompt
from services.n8n_client import N8nClient

logger = logging.getLogger(__name__)


async def start_report_generation(
    n8n_client: N8nClient,
    order_id: int,
    tariff: str,
    style: str,
    participants: List[Dict[str, Any]]
) -> str:
    """
    Запуск генерации нумерологического отчёта через N8N (асинхронно).

    N8N получит запрос, создаст таск и вернёт task_id для последующего polling.

    Args:
        n8n_client: Клиент N8N
        order_id: ID заказа
        tariff: Тип тарифа ('quick', 'deep', 'pair', 'family')
        style: Стиль отчёта ('analytical', 'shamanic')
        participants: Список участников с данными

    Returns:
        task_id: ID созданного таска в N8N

    Raises:
        Exception: При ошибке отправки запроса
    """
    # Строим промпт
    prompt = build_numerology_prompt(tariff, style, participants)

    # Логируем промпт
    logger.info(
        f"Сгенерирован промпт для {tariff}/{style}, "
        f"длина: {len(prompt)} символов (~{len(prompt.split())} слов)"
    )

    # Отправляем в N8N для генерации
    try:
        task_id = await n8n_client.start_generation(
            prompt=prompt,
            order_id=order_id,
            tariff=tariff,
            style=style
        )

        logger.info(
            f"Генерация запущена для заказа {order_id}, "
            f"получен task_id: {task_id}"
        )

        return task_id

    except Exception as e:
        logger.error(f"Ошибка запуска генерации для заказа {order_id}: {e}")
        raise
