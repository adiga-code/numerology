"""GPT клиент с поддержкой PDF книги (Method 1 - Assistants API с file_search)."""
import logging
from pathlib import Path
from typing import Optional
from openai import AsyncOpenAI

from services.prompts import get_system_prompt, build_detailed_prompt

logger = logging.getLogger(__name__)


class GPTAssistantWithBook:
    """
    GPT клиент с использованием Assistants API и file_search (Method 1).

    Преимущества:
    - Поддержка БОЛЬШИХ книг (600+ страниц)
    - Автоматический поиск релевантных секций через vector store
    - Не нужно управлять размером контекста вручную

    Недостатки:
    - Дороже (платный vector store)
    - Медленнее инициализация (загрузка в vector store)
    """

    def __init__(
        self,
        api_key: str,
        book_path: str = "/app/books/numerology_book.pdf",
        model: str = "gpt-4-turbo-preview"
    ):
        """
        Инициализация GPT клиента с книгой через Assistants API.

        Args:
            api_key: API ключ OpenAI
            book_path: Путь к PDF книге
            model: Модель GPT для использования
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.book_path = Path(book_path)

        # ID ресурсов OpenAI (заполняются при инициализации)
        self.assistant_id: Optional[str] = None
        self.vector_store_id: Optional[str] = None
        self.file_id: Optional[str] = None

    async def initialize(self):
        """
        Инициализация клиента - загрузка книги в vector store и создание ассистента.

        Вызывается один раз при старте приложения.
        """
        try:
            if not self.book_path.exists():
                raise FileNotFoundError(
                    f"PDF книга не найдена: {self.book_path}\n"
                    f"Поместите файл numerology_book.pdf в директорию books/"
                )

            logger.info(f"Загрузка PDF книги {self.book_path.name} в OpenAI...")

            # Шаг 1: Загружаем файл в OpenAI
            with open(self.book_path, "rb") as f:
                file = await self.client.files.create(
                    file=f,
                    purpose="assistants"
                )
            self.file_id = file.id
            logger.info(f"Файл загружен: {self.file_id}")

            # Шаг 2: Создаём vector store
            vector_store = await self.client.beta.vector_stores.create(
                name="Numerology Reference Book",
                file_ids=[self.file_id]
            )
            self.vector_store_id = vector_store.id
            logger.info(f"Vector store создан: {self.vector_store_id}")

            # Ждём пока файл проиндексируется
            logger.info("Ожидание индексации книги...")
            import asyncio
            max_wait = 60  # максимум 60 секунд
            waited = 0
            while waited < max_wait:
                vs_status = await self.client.beta.vector_stores.retrieve(
                    vector_store_id=self.vector_store_id
                )
                if vs_status.status == "completed":
                    logger.info("Индексация завершена!")
                    break
                elif vs_status.status == "failed":
                    raise Exception("Ошибка индексации книги в vector store")

                await asyncio.sleep(2)
                waited += 2
                logger.debug(f"Индексация... ({waited}s / {max_wait}s)")

            if waited >= max_wait:
                logger.warning("Индексация заняла слишком много времени, продолжаем...")

            # Шаг 3: Создаём ассистента с file_search
            assistant = await self.client.beta.assistants.create(
                name="Numerology Expert",
                instructions=(
                    "Ты профессиональный нумеролог с многолетним опытом. "
                    "Используй прикреплённую справочную книгу по нумерологии для создания "
                    "детальных, профессиональных отчётов. "
                    "Опирайся на методы и значения из книги."
                ),
                model=self.model,
                tools=[{"type": "file_search"}],
                tool_resources={
                    "file_search": {
                        "vector_store_ids": [self.vector_store_id]
                    }
                }
            )
            self.assistant_id = assistant.id
            logger.info(f"Ассистент создан: {self.assistant_id}")
            logger.info("GPT клиент с книгой инициализирован успешно (Assistants API)")

        except FileNotFoundError as e:
            logger.warning(f"Книга не найдена: {e}")
            logger.warning("Клиент будет работать БЕЗ книги (fallback режим)")
            self.assistant_id = None
        except Exception as e:
            logger.error(f"Ошибка при инициализации книги: {e}", exc_info=True)
            logger.warning("Клиент будет работать БЕЗ книги (fallback режим)")
            self.assistant_id = None

    async def generate_report(
        self,
        tariff: str,
        style: str,
        participants: list
    ) -> str:
        """
        Генерация нумерологического отчёта с использованием книги.

        Args:
            tariff: Тип тарифа (quick/deep/pair/family)
            style: Стиль отчёта (analytical/shamanic)
            participants: Список участников с данными

        Returns:
            str: Сгенерированный отчёт

        Raises:
            Exception: Если произошла ошибка при генерации
        """
        if not self.assistant_id:
            raise Exception(
                "Ассистент не инициализирован. Проверьте логи инициализации."
            )

        try:
            # Строим детальный промпт
            user_prompt = build_detailed_prompt(tariff, style, participants)

            # Добавляем инструкцию использовать книгу
            full_prompt = f"""{user_prompt}

ВАЖНО: Используй информацию из прикреплённой справочной книги по нумерологии.
Опирайся на описанные в книге методы, значения чисел и техники расчёта.
Создавай детальный, профессиональный отчёт на основе этих знаний."""

            logger.info(
                f"Генерация отчёта через Assistants API: "
                f"tariff={tariff}, style={style}, participants={len(participants)}"
            )

            # Создаём thread
            thread = await self.client.beta.threads.create()
            logger.debug(f"Thread создан: {thread.id}")

            # Отправляем сообщение
            await self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=full_prompt
            )

            # Запускаем ассистента
            run = await self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.assistant_id
            )
            logger.debug(f"Run создан: {run.id}")

            # Ждём завершения
            import asyncio
            max_wait = 300  # 5 минут максимум
            waited = 0
            while waited < max_wait:
                run_status = await self.client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )

                if run_status.status == "completed":
                    logger.info("Генерация завершена!")
                    break
                elif run_status.status in ["failed", "cancelled", "expired"]:
                    error_msg = getattr(run_status, 'last_error', 'Unknown error')
                    raise Exception(f"Run failed: {run_status.status}, error: {error_msg}")

                await asyncio.sleep(3)
                waited += 3

                if waited % 15 == 0:  # Каждые 15 секунд логируем
                    logger.debug(f"Генерация в процессе... ({waited}s, status: {run_status.status})")

            if waited >= max_wait:
                raise Exception("Timeout: генерация заняла слишком много времени")

            # Получаем ответ
            messages = await self.client.beta.threads.messages.list(
                thread_id=thread.id,
                order="desc",
                limit=1
            )

            if not messages.data:
                raise Exception("Не получен ответ от ассистента")

            # Извлекаем текст из первого сообщения
            message = messages.data[0]
            text_parts = []
            for content_block in message.content:
                if content_block.type == "text":
                    text_parts.append(content_block.text.value)

            result_text = "\n\n".join(text_parts)

            if not result_text.strip():
                raise Exception("Получен пустой ответ от ассистента")

            logger.info(
                f"Отчёт сгенерирован: {len(result_text)} символов, "
                f"thread={thread.id}"
            )

            # Удаляем thread для экономии (опционально)
            try:
                await self.client.beta.threads.delete(thread_id=thread.id)
                logger.debug(f"Thread удалён: {thread.id}")
            except Exception as e:
                logger.warning(f"Не удалось удалить thread: {e}")

            return result_text

        except Exception as e:
            logger.error(f"Ошибка при генерации отчёта с книгой: {e}", exc_info=True)
            raise

    async def cleanup(self):
        """
        Очистка ресурсов при остановке приложения.

        Удаляет assistant, vector store и файл из OpenAI.
        """
        try:
            if self.assistant_id:
                await self.client.beta.assistants.delete(self.assistant_id)
                logger.info(f"Ассистент удалён: {self.assistant_id}")

            if self.vector_store_id:
                await self.client.beta.vector_stores.delete(self.vector_store_id)
                logger.info(f"Vector store удалён: {self.vector_store_id}")

            if self.file_id:
                await self.client.files.delete(self.file_id)
                logger.info(f"Файл удалён: {self.file_id}")

        except Exception as e:
            logger.error(f"Ошибка при очистке ресурсов: {e}")


# Alias для обратной совместимости
OptimizedGPTClient = GPTAssistantWithBook
