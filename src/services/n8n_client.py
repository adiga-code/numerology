"""N8N webhook клиент для генерации отчётов."""
import logging
import httpx
from typing import Dict, Any

logger = logging.getLogger(__name__)


class N8nClient:
    """Клиент для отправки запросов в N8N webhook."""

    def __init__(self, webhook_url: str, callback_url: str, secret_token: str, timeout: int = 30):
        """
        Инициализация N8N клиента.

        Args:
            webhook_url: URL webhook в N8N
            callback_url: URL для callback от N8N с результатом
            secret_token: Секретный токен для проверки callback
            timeout: Таймаут запроса в секундах (по умолчанию 30)
        """
        self.webhook_url = webhook_url
        self.callback_url = callback_url
        self.secret_token = secret_token
        self.timeout = timeout

    async def start_generation(
        self,
        prompt: str,
        order_id: int,
        tariff: str,
        style: str
    ) -> None:
        """
        Отправка запроса на генерацию отчёта в N8N (асинхронно).

        N8N получит запрос, запустит генерацию в фоне и вернёт результат
        через callback на callback_url.

        Args:
            prompt: Готовый промпт для генерации
            order_id: ID заказа
            tariff: Тариф (quick/deep/pair/family)
            style: Стиль (analytical/shamanic)

        Raises:
            Exception: При ошибке отправки запроса
        """
        payload = {
            "prompt": prompt,
            "order_id": order_id,
            "tariff": tariff,
            "style": style,
            "callback_url": self.callback_url,
            "secret_token": self.secret_token
        }

        logger.info(
            f"Отправка запроса в N8N для заказа {order_id} "
            f"(тариф: {tariff}, стиль: {style})"
            f"url: {self.webhook_url}"
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload
                )

                # Проверяем что N8N принял запрос
                response.raise_for_status()

                # Парсим ответ
                result = response.json()

                # Логируем ответ от N8N
                logger.info(f"N8N принял запрос для заказа {order_id}: {result}")

                # Проверяем что workflow запустился
                if "message" in result and "started" in result["message"].lower():
                    logger.info(f"N8N workflow запущен для заказа {order_id}")
                else:
                    logger.warning(
                        f"Неожиданный ответ от N8N для заказа {order_id}: {result}"
                    )

        except httpx.TimeoutException:
            logger.error(f"Таймаут при отправке запроса в N8N для заказа {order_id}")
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
            logger.error(f"Ошибка при отправке запроса в N8N для заказа {order_id}: {e}")
            raise Exception(f"Произошла ошибка при запуске генерации: {str(e)}")
