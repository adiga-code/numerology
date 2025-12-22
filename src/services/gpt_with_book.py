"""GPT клиент с поддержкой PDF книги (Method 2 - Chat API)."""
import logging
from pathlib import Path
from typing import Optional
from openai import AsyncOpenAI
from PyPDF2 import PdfReader

from services.prompts import get_system_prompt, build_detailed_prompt

logger = logging.getLogger(__name__)


class PDFBookLoader:
    """Загрузчик и кэш для PDF книги."""

    def __init__(self, book_path: str):
        """
        Инициализация загрузчика книги.

        Args:
            book_path: Путь к PDF файлу книги
        """
        self.book_path = Path(book_path)
        self._cached_text: Optional[str] = None
        self._is_loaded = False

    def load_book(self) -> str:
        """
        Загрузка и извлечение текста из PDF книги.

        Returns:
            str: Извлечённый текст из книги

        Raises:
            FileNotFoundError: Если книга не найдена
            Exception: Если не удалось извлечь текст
        """
        # Если уже загружено - вернуть из кэша
        if self._is_loaded and self._cached_text:
            logger.debug("Использую кэшированный текст книги")
            return self._cached_text

        if not self.book_path.exists():
            raise FileNotFoundError(
                f"PDF книга не найдена: {self.book_path}\n"
                f"Поместите файл numerology_book.pdf в директорию books/"
            )

        try:
            logger.info(f"Загрузка PDF книги из {self.book_path}")
            reader = PdfReader(str(self.book_path))

            # Извлекаем текст со всех страниц
            text_parts = []
            for i, page in enumerate(reader.pages, 1):
                text = page.extract_text()
                if text:
                    text_parts.append(text)
                    logger.debug(f"Извлечена страница {i}/{len(reader.pages)}")

            full_text = "\n\n".join(text_parts)

            if not full_text.strip():
                raise Exception("Не удалось извлечь текст из PDF (файл пустой или защищён)")

            # Кэшируем результат
            self._cached_text = full_text
            self._is_loaded = True

            logger.info(
                f"PDF книга загружена успешно: "
                f"{len(reader.pages)} страниц, "
                f"{len(full_text)} символов"
            )

            return full_text

        except Exception as e:
            logger.error(f"Ошибка при загрузке PDF книги: {e}")
            raise

    def get_book_summary(self) -> str:
        """
        Получить краткую информацию о загруженной книге.

        Returns:
            str: Информация о книге
        """
        if not self._is_loaded:
            return "Книга не загружена"

        char_count = len(self._cached_text) if self._cached_text else 0
        word_count = len(self._cached_text.split()) if self._cached_text else 0

        return (
            f"Книга загружена: {self.book_path.name}\n"
            f"Символов: {char_count:,}\n"
            f"Слов (примерно): {word_count:,}"
        )


class GPTClientWithBook:
    """
    GPT клиент с использованием PDF книги в контексте (Method 2 - Chat API).

    Преимущества этого метода:
    - Простота реализации
    - Полный контроль над контекстом
    - Ниже стоимость (нет дополнительных расходов на vector store)
    - Быстрее (нет задержки на file_search)

    Ограничения:
    - Размер книги ограничен context window (для gpt-4-turbo ~128k токенов)
    - Весь текст передаётся с каждым запросом
    """

    def __init__(
        self,
        api_key: str,
        book_path: str = "/app/books/numerology_book.pdf",
        model: str = "gpt-4-turbo-preview"
    ):
        """
        Инициализация GPT клиента с книгой.

        Args:
            api_key: API ключ OpenAI
            book_path: Путь к PDF книге
            model: Модель GPT для использования
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.book_loader = PDFBookLoader(book_path)
        self.book_text: Optional[str] = None

    async def initialize(self):
        """
        Инициализация клиента - загрузка книги в память.

        Вызывается один раз при старте приложения.
        """
        try:
            self.book_text = self.book_loader.load_book()
            logger.info("GPT клиент с книгой инициализирован успешно")
            logger.info(self.book_loader.get_book_summary())
        except FileNotFoundError as e:
            logger.warning(f"Книга не найдена: {e}")
            logger.warning("Клиент будет работать БЕЗ книги (fallback режим)")
            self.book_text = None
        except Exception as e:
            logger.error(f"Ошибка при инициализации книги: {e}")
            logger.warning("Клиент будет работать БЕЗ книги (fallback режим)")
            self.book_text = None

    def _build_context_with_book(self, user_prompt: str) -> str:
        """
        Построение контекста с книгой для user сообщения.

        Args:
            user_prompt: Промпт пользователя

        Returns:
            str: Полный контекст с книгой
        """
        if not self.book_text:
            # Fallback: работаем без книги
            return user_prompt

        # Ограничиваем размер книги если нужно (опционально)
        # Для GPT-4-turbo можно передать ~100k символов книги без проблем
        max_book_chars = 100000
        book_content = self.book_text[:max_book_chars]

        if len(self.book_text) > max_book_chars:
            logger.warning(
                f"Книга обрезана: {len(self.book_text)} -> {max_book_chars} символов"
            )

        return f"""СПРАВОЧНАЯ КНИГА ПО НУМЕРОЛОГИИ:

{book_content}

---

ЗАДАНИЕ:

{user_prompt}

ВАЖНО: Используй информацию из справочной книги выше для создания отчёта.
Опирайся на описанные в книге методы, значения чисел и техники расчёта.
Создавай детальный, профессиональный отчёт на основе этих знаний."""

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
        try:
            # Получаем системный промпт
            system_prompt = get_system_prompt(style)

            # Строим детальный промпт
            user_prompt = build_detailed_prompt(tariff, style, participants)

            # Добавляем книгу в контекст
            full_prompt = self._build_context_with_book(user_prompt)

            logger.info(
                f"Генерация отчёта: tariff={tariff}, style={style}, "
                f"participants={len(participants)}, "
                f"book_included={'Yes' if self.book_text else 'No'}"
            )

            # Вызываем GPT-4
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.7,
                max_tokens=16000  # Для длинных отчётов
            )

            text = response.choices[0].message.content
            tokens_used = response.usage.total_tokens

            logger.info(
                f"Отчёт сгенерирован: {len(text)} символов, "
                f"{tokens_used} токенов использовано"
            )

            return text

        except Exception as e:
            logger.error(f"Ошибка при генерации отчёта с книгой: {e}", exc_info=True)
            raise


class OptimizedGPTClient(GPTClientWithBook):
    """
    Оптимизированный GPT клиент с кэшированием промпта книги.

    Для продакшена: использует prompt caching (если поддерживается моделью)
    для снижения стоимости повторных запросов с одной и той же книгой.
    """

    def __init__(self, api_key: str, book_path: str = "/app/books/numerology_book.pdf"):
        """
        Инициализация оптимизированного клиента.

        Args:
            api_key: API ключ OpenAI
            book_path: Путь к PDF книге
        """
        # Используем самую новую модель с поддержкой больших контекстов
        super().__init__(
            api_key=api_key,
            book_path=book_path,
            model="gpt-4-turbo-preview"  # или "gpt-4-1106-preview"
        )

    async def generate_report(
        self,
        tariff: str,
        style: str,
        participants: list
    ) -> str:
        """
        Генерация отчёта с оптимизацией.

        В будущем здесь можно добавить:
        - Кэширование на уровне OpenAI (prompt caching)
        - Разбиение длинных книг на чанки
        - Использование embeddings для релевантных секций
        """
        return await super().generate_report(tariff, style, participants)
