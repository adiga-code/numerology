"""N8N webhook клиент для генерации отчётов."""
import logging
import httpx
from typing import Dict, Any

logger = logging.getLogger(__name__)


class N8nClient:
    """Клиент для отправки запросов в N8N webhook."""

    def __init__(self, webhook_url: str, status_url: str, secret_token: str, timeout: int = 30):
        """
        Инициализация N8N клиента.

        Args:
            webhook_url: URL webhook в N8N для создания таска
            status_url: URL для проверки статуса таска в N8N
            secret_token: Секретный токен для проверки
            timeout: Таймаут запроса в секундах (по умолчанию 30)
        """
        self.webhook_url = webhook_url
        self.status_url = status_url
        self.secret_token = secret_token
        self.timeout = timeout

    async def start_generation(
        self,
        prompt: str,
        order_id: int,
        tariff: str,
        style: str
    ) -> str:
        """
        Отправка запроса на генерацию отчёта в N8N (асинхронно).

        N8N получит запрос, создаст таск и вернёт task_id.
        Для получения результата нужно периодически проверять статус через check_status.

        Args:
            prompt: Готовый промпт для генерации
            order_id: ID заказа
            tariff: Тариф (quick/deep/pair/family)
            style: Стиль (analytical/shamanic)

        Returns:
            task_id: ID созданного таска для последующей проверки статуса

        Raises:
            Exception: При ошибке отправки запроса
        """
        payload = {
            "prompt": prompt,
            "order_id": order_id,
            "tariff": tariff,
            "style": style,
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

                # Проверяем что получили task_id
                if "task_id" not in result:
                    logger.error(f"N8N не вернул task_id для заказа {order_id}: {result}")
                    raise Exception("N8N не вернул task_id в ответе")

                task_id = result["task_id"]
                logger.info(f"N8N создал таск {task_id} для заказа {order_id}")

                return task_id

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

    async def check_status(self, task_id: str) -> Dict[str, Any]:
        """
        Проверка статуса таска в N8N.

        Args:
            task_id: ID таска для проверки

        Returns:
            Dict с полями:
            - status: "pending" | "completed" | "failed"
            - data: текст результата (если status == "completed")
            - error: сообщение об ошибке (если status == "failed")

        Raises:
            Exception: При ошибке запроса
        """
        # Формируем URL для проверки статуса с query параметром
        url = f"{self.status_url}?task_id={task_id}"

        logger.info(f"Проверка статуса таска {task_id} по URL: {url}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    headers={"X-N8N-Token": self.secret_token}
                )

                response.raise_for_status()
                result = response.json()

                logger.info(f"Статус таска {task_id}: {result.get('status', 'unknown')}")

                # Проверяем наличие поля status
                if "status" not in result:
                    logger.error(f"N8N не вернул поле status для таска {task_id}: {result}")
                    raise Exception("N8N не вернул поле status в ответе")

                return result

        except httpx.TimeoutException:
            logger.error(f"Таймаут при проверке статуса таска {task_id}")
            raise Exception("Превышено время ожидания ответа от сервиса")

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP ошибка при проверке статуса таска {task_id}: "
                f"{e.response.status_code}"
            )
            raise Exception(f"Ошибка сервиса (HTTP {e.response.status_code})")

        except Exception as e:
            logger.error(f"Ошибка при проверке статуса таска {task_id}: {e}")
            raise Exception(f"Произошла ошибка при проверке статуса: {str(e)}")
