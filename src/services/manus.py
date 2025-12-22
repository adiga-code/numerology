"""Клиент для работы с Manus API."""
import logging
from typing import Dict, Any, List

import httpx

from services.prompts import build_numerology_prompt as build_prompt

logger = logging.getLogger(__name__)


class ManusClient:
    """Клиент для Manus API."""

    def __init__(self, api_key: str, webhook_url: str):
        """
        Инициализация клиента Manus API.

        Args:
            api_key: API ключ Manus
            webhook_url: URL для webhook уведомлений
        """
        self.api_key = api_key
        self.webhook_url = webhook_url
        self.base_url = "https://api.manus.im"  # Примерный URL, нужно уточнить

    async def create_task(
        self,
        prompt: str,
        order_id: int,
        agent_profile: str = "manus-1.5"
    ) -> Dict[str, Any]:
        """
        Создание задачи в Manus API.

        Args:
            prompt: Промпт для генерации отчёта
            order_id: ID заказа
            agent_profile: Профиль агента

        Returns:
            Dict с task_id и статусом
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/tasks",
                    json={
                        "agentProfile": agent_profile,
                        "prompt": prompt,
                        "metadata": {
                            "order_id": order_id
                        },
                        "webhook_url": f"{self.webhook_url}/webhook/manus"
                    },
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                logger.info(f"Создана задача Manus для заказа {order_id}: {data.get('task_id')}")
                return data

            except httpx.HTTPError as e:
                logger.error(f"Ошибка при создании задачи Manus: {e}")
                raise

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Получение статуса задачи.

        Args:
            task_id: ID задачи

        Returns:
            Dict со статусом и результатом
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/tasks/{task_id}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()

            except httpx.HTTPError as e:
                logger.error(f"Ошибка при получении статуса задачи Manus: {e}")
                raise


def build_numerology_prompt(
    tariff: str,
    style: str,
    participants: List[Dict[str, Any]]
) -> str:
    """
    Построение промпта для нумерологического анализа.

    DEPRECATED: Используйте services.prompts.build_numerology_prompt напрямую.
    Эта функция оставлена для обратной совместимости.

    Args:
        tariff: Тип тарифа ('quick', 'deep', 'pair', 'family')
        style: Стиль отчёта ('analytical', 'shamanic')
        participants: Список участников с данными

    Returns:
        str: Промпт для AI
    """
    prompt = build_prompt(tariff, style, participants)

    # Логирование длины промпта для мониторинга
    logger.info(
        f"Сгенерирован промпт для {tariff}/{style}, "
        f"длина: {len(prompt)} символов (~{len(prompt.split())} слов)"
    )

    return prompt
