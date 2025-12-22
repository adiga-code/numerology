"""AI Fallback сервис (GPT-4 → Manus)."""
import logging
import asyncio
from typing import Dict, Any, Optional

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class GPT4Client:
    """Клиент для OpenAI GPT-4 с поддержкой Assistants API."""

    def __init__(self, api_key: str, assistant_id: Optional[str] = None):
        """
        Инициализация клиента GPT-4.

        Args:
            api_key: API ключ OpenAI
            assistant_id: ID Assistant с базой знаний (опционально)
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.assistant_id = assistant_id

        # Определяем API endpoint для assistants (совместимость с openai 1.x и 2.x)
        # В обеих версиях assistants находится в beta
        self.assistants_api = self.client.beta.assistants
        self.threads_api = self.client.beta.threads

    async def generate_report(self, prompt: str) -> str:
        """
        Генерация отчёта через GPT-4.

        Использует Assistants API с file_search если настроен assistant_id,
        иначе fallback на обычный Chat Completions.

        Args:
            prompt: Промпт для генерации

        Returns:
            str: Сгенерированный текст
        """
        try:
            if self.assistant_id:
                # Используем Assistants API с базой знаний
                return await self._generate_with_assistant(prompt)
            else:
                # Fallback на обычный Chat Completions
                return await self._generate_with_chat(prompt)

        except Exception as e:
            logger.error(f"Ошибка при генерации отчёта GPT-4: {e}")
            raise

    async def _generate_with_assistant(self, prompt: str) -> str:
        """
        Генерация через Assistants API с базой знаний.

        Args:
            prompt: Промпт для генерации

        Returns:
            str: Сгенерированный текст
        """
        # Создаём новый thread для каждого заказа
        thread = await self.threads_api.create()
        logger.info(f"Создан thread: {thread.id}")

        # Добавляем сообщение пользователя
        await self.threads_api.messages.create(
            thread_id=thread.id,
            role="user",
            content=prompt
        )

        # Запускаем run с дополнительными инструкциями и увеличенным лимитом токенов
        run = await self.threads_api.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistant_id,
            # Явные дополнительные инструкции для каждого запроса
            additional_instructions="""КРИТИЧЕСКИ ВАЖНО:
- СТРОГО СОБЛЮДАЙ объём, указанный в запросе пользователя
- Если требуется 15-20 страниц, генерируй ПОЛНЫЙ текст на 15-20 страниц
- НЕ СОКРАЩАЙ информацию, расписывай всё МАКСИМАЛЬНО ПОДРОБНО
- Используй ВСЮ доступную информацию из базы знаний
- ОБЯЗАТЕЛЬНО следуй структуре из запроса
- НЕ ОСТАНАВЛИВАЙСЯ до достижения требуемого объёма""",
            # Увеличиваем лимит токенов для длинных отчётов (16000 ~ 20-25 страниц)
            max_completion_tokens=16000
        )

        logger.info(f"Запущен run: {run.id}")

        # Ждём завершения
        while True:
            run_status = await self.threads_api.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )

            if run_status.status == "completed":
                logger.info(f"Run завершён успешно")
                break
            elif run_status.status in ["failed", "cancelled", "expired"]:
                logger.error(f"Run завершён с ошибкой: {run_status.status}")
                raise Exception(f"Assistant run failed: {run_status.status}")

            await asyncio.sleep(2)

        # Получаем ответ
        messages = await self.threads_api.messages.list(
            thread_id=thread.id,
            order="desc",
            limit=1
        )

        if not messages.data:
            raise Exception("Нет ответа от Assistant")

        # Извлекаем текст из ответа
        message = messages.data[0]
        text_content = []

        for content_block in message.content:
            if content_block.type == "text":
                text_content.append(content_block.text.value)

        result_text = "\n".join(text_content)

        # Логируем статистику ответа
        char_count = len(result_text)
        word_count = len(result_text.split())
        estimated_pages = char_count / 2800  # ~2800 символов на страницу А4

        logger.info(
            f"GPT-4 Assistant отчёт сгенерирован (thread: {thread.id}): "
            f"{char_count} символов, {word_count} слов, ~{estimated_pages:.1f} страниц"
        )

        # Проверяем usage если доступно
        if hasattr(run_status, 'usage') and run_status.usage:
            logger.info(f"Использовано токенов: {run_status.usage.completion_tokens}/{run_status.usage.total_tokens}")

        return result_text

    async def _generate_with_chat(self, prompt: str) -> str:
        """
        Генерация через Chat Completions API (fallback без базы знаний).

        Args:
            prompt: Промпт для генерации

        Returns:
            str: Сгенерированный текст
        """
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

        logger.info(f"GPT-4 Chat отчёт сгенерирован, использовано токенов: {tokens_used}")
        return text


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
