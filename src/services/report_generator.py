"""Сервис генерации отчётов через N8N."""
import logging
from typing import List, Dict, Any

from services.prompts import build_numerology_prompt
from services.n8n_client import N8nClient

logger = logging.getLogger(__name__)


async def generate_report(
    n8n_client: N8nClient,
    order_id: int,
    tariff: str,
    style: str,
    participants: List[Dict[str, Any]]
) -> str:
    """
    Генерация нумерологического отчёта через N8N.

    Args:
        n8n_client: Клиент N8N
        order_id: ID заказа
        tariff: Тип тарифа ('quick', 'deep', 'pair', 'family')
        style: Стиль отчёта ('analytical', 'shamanic')
        participants: Список участников с данными

    Returns:
        str: Сгенерированный текст отчёта

    Raises:
        Exception: При ошибке генерации
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
        text = await n8n_client.generate_report(
            prompt=prompt,
            order_id=order_id,
            tariff=tariff,
            style=style
        )

        logger.info(f"Отчёт успешно сгенерирован для заказа {order_id}")
        return text

    except Exception as e:
        logger.error(f"Ошибка генерации отчёта для заказа {order_id}: {e}")
        raise
