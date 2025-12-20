"""Клиент для работы с Manus API."""
import logging
from typing import Dict, Any

import httpx

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
    participants: list
) -> str:
    """
    Построение промпта для нумерологического анализа.

    Args:
        tariff: Тип тарифа
        style: Стиль отчёта
        participants: Список участников с данными

    Returns:
        str: Промпт для AI
    """
    style_description = {
        "analytical": "аналитическом, научном стиле с структурированным подходом",
        "shamanic": "шаманском, эзотерическом стиле с образным языком"
    }

    tariff_description = {
        "quick": "краткий нумерологический анализ (5-7 страниц)",
        "deep": "глубокий нумерологический анализ с использованием Генокода и метода Пифагора (15-20 страниц)",
        "pair": "анализ совместимости пары (15-25 страниц)",
        "family": "семейный нумерологический анализ (30-50 страниц)"
    }

    prompt = f"""Создай {tariff_description[tariff]} в {style_description[style]}.

Участники:
"""

    for idx, p in enumerate(participants, 1):
        prompt += f"\n{idx}. {p['full_name']}"
        prompt += f"\n   Дата рождения: {p['birth_date']}"
        if p.get('birth_time'):
            prompt += f"\n   Время рождения: {p['birth_time']}"
        if p.get('birth_place'):
            prompt += f"\n   Место рождения: {p['birth_place']}"
        prompt += "\n"

    prompt += """
Структура отчёта должна включать:
1. Введение
2. Нумерологический профиль каждого участника
3. Основные жизненные циклы и периоды
4. Таланты и способности
5. Рекомендации для развития
"""

    if tariff == "pair":
        prompt += "6. Анализ совместимости пары\n7. Рекомендации для гармоничных отношений\n"
    elif tariff == "family":
        prompt += "6. Семейная динамика и взаимодействия\n7. Рекомендации для семейной гармонии\n"

    prompt += "\nОтчёт должен быть профессиональным, детальным и практически применимым."

    return prompt
