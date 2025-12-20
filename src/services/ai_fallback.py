"""AI Fallback сервисы (GPT-4 и Gemini)."""
import logging
from typing import Dict, Any

from openai import AsyncOpenAI
import google.generativeai as genai

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


class GeminiClient:
    """Клиент для Google Gemini."""

    def __init__(self, api_key: str):
        """
        Инициализация клиента Gemini.

        Args:
            api_key: API ключ Google
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')

    async def generate_report(self, prompt: str) -> str:
        """
        Генерация отчёта через Gemini.

        Args:
            prompt: Промпт для генерации

        Returns:
            str: Сгенерированный текст
        """
        try:
            response = await self.model.generate_content_async(prompt)
            text = response.text

            logger.info(f"Gemini отчёт сгенерирован")
            return text

        except Exception as e:
            logger.error(f"Ошибка при генерации отчёта Gemini: {e}")
            raise


async def generate_with_fallback(
    prompt: str,
    manus_client,
    gpt4_client: GPT4Client,
    gemini_client: GeminiClient,
    order_id: int
) -> tuple[str, str]:
    """
    Генерация отчёта с fallback механизмом.

    Пробует в порядке: Manus → GPT-4 → Gemini

    Args:
        prompt: Промпт для генерации
        manus_client: Клиент Manus
        gpt4_client: Клиент GPT-4
        gemini_client: Клиент Gemini
        order_id: ID заказа

    Returns:
        tuple: (сгенерированный текст, использованный провайдер)
    """
    # Попытка 1: Manus
    try:
        logger.info(f"Попытка генерации через Manus для заказа {order_id}")
        result = await manus_client.create_task(prompt, order_id)
        # Manus работает через webhook, возвращаем task_id
        return result.get("task_id"), "manus"
    except Exception as e:
        logger.warning(f"Manus недоступен для заказа {order_id}: {e}")

    # Попытка 2: GPT-4
    try:
        logger.info(f"Попытка генерации через GPT-4 для заказа {order_id}")
        text = await gpt4_client.generate_report(prompt)
        return text, "gpt4"
    except Exception as e:
        logger.warning(f"GPT-4 недоступен для заказа {order_id}: {e}")

    # Попытка 3: Gemini
    try:
        logger.info(f"Попытка генерации через Gemini для заказа {order_id}")
        text = await gemini_client.generate_report(prompt)
        return text, "gemini"
    except Exception as e:
        logger.error(f"Все AI провайдеры недоступны для заказа {order_id}: {e}")
        raise Exception("Все AI сервисы недоступны")
