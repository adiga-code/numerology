"""AI Fallback сервис (GPT-4 → Manus)."""
import logging
from typing import Dict, Any

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class GPT4Client:
    """Клиент для OpenAI GPT-4."""

    def __init__(self, api_key: str):
        """
        Инициализация клиента GPT-4.

        Args:
            api_key: API ключ OpenAI
        """
        self.client = AsyncOpenAI(api_key=api_key)

    async def generate_report(self, prompt: str) -> str:
        """
        Генерация отчёта через GPT-4.

        Args:
            prompt: Промпт для генерации

        Returns:
            str: Сгенерированный текст
        """
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "Ты профессиональный нумеролог с многолетним опытом."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )

            text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens

            logger.info(f"GPT-4 отчёт сгенерирован, использовано токенов: {tokens_used}")
            return text

        except Exception as e:
            logger.error(f"Ошибка при генерации отчёта GPT-4: {e}")
            raise


async def generate_with_fallback(
    prompt: str,
    manus_client,
    gpt4_client: GPT4Client,
    order_id: int
) -> tuple[str, str]:
    """
    Генерация отчёта с fallback механизмом.

    Для тестирования: GPT-4 → Manus

    Args:
        prompt: Промпт для генерации
        manus_client: Клиент Manus
        gpt4_client: Клиент GPT-4
        order_id: ID заказа

    Returns:
        tuple: (сгенерированный текст, использованный провайдер)
    """
    # Попытка 1: GPT-4 (для тестирования PDF генерации)
    try:
        logger.info(f"Попытка генерации через GPT-4 для заказа {order_id}")
        text = await gpt4_client.generate_report(prompt)
        return text, "gpt4"
    except Exception as e:
        logger.warning(f"GPT-4 недоступен для заказа {order_id}: {e}")

    # Попытка 2: Manus
    try:
        logger.info(f"Попытка генерации через Manus для заказа {order_id}")
        result = await manus_client.create_task(prompt, order_id)
        # Manus работает через webhook, возвращаем task_id
        return result.get("task_id"), "manus"
    except Exception as e:
        logger.error(f"Все AI провайдеры недоступны для заказа {order_id}: {e}")
        raise Exception("Все AI сервисы недоступны")
