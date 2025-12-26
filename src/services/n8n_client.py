"""N8N webhook клиент для генерации отчётов."""
import logging
import httpx
from typing import Dict, Any

logger = logging.getLogger(__name__)


class N8nClient:
    """Клиент для отправки запросов в N8N webhook."""

    def __init__(self, webhook_url: str, timeout: int = 300):
        """
        Инициализация N8N клиента.

        Args:
            webhook_url: URL webhook в N8N
            timeout: Таймаут запроса в секундах (по умолчанию 300 = 5 минут)
        """
        self.webhook_url = webhook_url
        self.timeout = timeout

    async def generate_report(
        self,
        prompt: str,
        order_id: int,
        tariff: str,
        style: str
    ) -> str:
        """
        Отправка запроса на генерацию отчёта в N8N.

        Args:
            prompt: Готовый промпт для генерации
            order_id: ID заказа
            tariff: Тариф (quick/deep/pair/family)
            style: Стиль (analytical/shamanic)

        Returns:
            str: Сгенерированный текст отчёта

        Raises:
            Exception: При ошибке генерации или таймауте
        """
        payload = {
            "prompt": prompt,
            "order_id": order_id,
            "tariff": tariff,
            "style": style
        }

        logger.info(
            f"Отправка запроса в N8N для заказа {order_id} "
            f"(тариф: {tariff}, стиль: {style})"
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload
                )

                # Проверяем статус ответа
                response.raise_for_status()

                # Парсим JSON ответ
                result = response.json()

                # Логируем полный ответ от N8N для дебага
                logger.info(f"Ответ от N8N для заказа {order_id}: {result}")

                # Валидация ответа
                if not isinstance(result, dict):
                    raise ValueError(f"Некорректный формат ответа от N8N: {type(result)}")

                if result.get("status") != "success":
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"N8N вернул некорректный статус. Полный ответ: {result}")
                    raise Exception(f"N8N вернул ошибку: {error_msg}")

                if "text" not in result:
                    raise ValueError("N8N не вернул поле 'text' в ответе")

                text = result["text"]

                # Логируем статистику
                char_count = len(text)
                word_count = len(text.split())
                estimated_pages = char_count / 2800

                logger.info(
                    f"N8N отчёт получен для заказа {order_id}: "
                    f"{char_count} символов, {word_count} слов, ~{estimated_pages:.1f} страниц"
                )

                return text

        except httpx.TimeoutException:
            logger.error(f"Таймаут при обращении к N8N для заказа {order_id}")
            raise Exception(
                "Превышено время ожидания ответа от сервиса генерации. "
                "Попробуйте позже."
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP ошибка от N8N для заказа {order_id}: "
                f"{e.response.status_code}"
            )
            raise Exception(
                f"Ошибка сервиса генерации (HTTP {e.response.status_code}). "
                f"Попробуйте позже."
            )

        except Exception as e:
            logger.error(f"Ошибка при генерации через N8N для заказа {order_id}: {e}")
            raise Exception(f"Произошла ошибка при генерации отчёта: {str(e)}")
