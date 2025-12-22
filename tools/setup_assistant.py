#!/usr/bin/env python3
"""
Скрипт для первоначальной настройки OpenAI Assistant с базой знаний PDF.

Запуск: python tools/setup_assistant.py <путь_к_pdf>

Скрипт:
1. Загружает PDF в OpenAI
2. Создает Vector Store
3. Создает Assistant с file_search
4. Выводит ASSISTANT_ID для .env
"""
import asyncio
import sys
from pathlib import Path
import os
from dotenv import load_dotenv

# Проверяем версию OpenAI
try:
    import openai
    from openai import AsyncOpenAI

    # Проверяем что версия >= 1.20.0 (минимум для vector_stores)
    version = tuple(map(int, openai.__version__.split('.')[:2]))
    if version < (1, 20):
        print(f"❌ Ошибка: Требуется openai >= 1.20.0, установлена {openai.__version__}")
        print("Обновите библиотеку: pip install --upgrade openai")
        sys.exit(1)
except ImportError:
    print("❌ Ошибка: Библиотека openai не установлена")
    print("Установите: pip install openai>=1.55.0")
    sys.exit(1)

# Загружаем переменные окружения
load_dotenv()


async def setup_assistant(pdf_path: str):
    """Настройка OpenAI Assistant с базой знаний."""

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Ошибка: OPENAI_API_KEY не найден в .env")
        sys.exit(1)

    client = AsyncOpenAI(api_key=api_key)

    # Определяем, где находится vector_stores API (версия 1.x vs 2.x)
    # В версии 2.x: client.vector_stores
    # В версии 1.x: client.beta.vector_stores
    vector_stores_api = None
    assistants_api = None

    if hasattr(client, 'vector_stores'):
        # OpenAI >= 2.0
        vector_stores_api = client.vector_stores
        assistants_api = client.beta.assistants
        print(f"📌 Используется OpenAI SDK >= 2.0 (версия: {openai.__version__})")
    elif hasattr(client.beta, 'vector_stores'):
        # OpenAI 1.x
        vector_stores_api = client.beta.vector_stores
        assistants_api = client.beta.assistants
        print(f"📌 Используется OpenAI SDK 1.x (версия: {openai.__version__})")
    else:
        print(f"❌ Ошибка: Vector Stores API недоступен в версии {openai.__version__}")
        print("Обновите библиотеку: pip install --upgrade openai")
        sys.exit(1)

    # Проверяем файл
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"❌ Ошибка: Файл {pdf_path} не найден")
        sys.exit(1)

    print(f"📄 Загружаем PDF: {pdf_file.name} ({pdf_file.stat().st_size / 1024 / 1024:.2f} MB)")

    # Шаг 1: Загрузка файла
    with open(pdf_file, "rb") as f:
        uploaded_file = await client.files.create(
            file=f,
            purpose="assistants"
        )

    print(f"✅ Файл загружен: {uploaded_file.id}")

    # Шаг 2: Создание Vector Store
    print("🔧 Создаем Vector Store...")
    vector_store = await vector_stores_api.create(
        name="Numerology Knowledge Base",
        file_ids=[uploaded_file.id]
    )

    print(f"✅ Vector Store создан: {vector_store.id}")

    # Ожидаем индексацию
    print("⏳ Ожидаем завершения индексации...")
    while True:
        vs_status = await vector_stores_api.retrieve(vector_store.id)
        if vs_status.status == "completed":
            print(f"✅ Индексация завершена! Файлов в базе: {vs_status.file_counts.completed}")
            break
        elif vs_status.status == "failed":
            print("❌ Ошибка индексации")
            sys.exit(1)

        await asyncio.sleep(2)

    # Шаг 3: Создание Assistant
    print("🤖 Создаем Assistant...")
    assistant = await assistants_api.create(
        name="Numerology Expert",
        instructions="""Ты профессиональный нумеролог с многолетним опытом.

Используй базу знаний для создания точных и детальных нумерологических отчётов.

При создании отчёта:
- Опирайся на информацию из базы знаний
- Используй методы Пифагора и Генокода
- Структурируй отчёт согласно запросу пользователя
- Пиши профессионально и практически применимо
- Адаптируй стиль под запрос (аналитический или шаманский)
""",
        model="gpt-4-turbo-preview",
        tools=[{"type": "file_search"}],
        tool_resources={
            "file_search": {
                "vector_store_ids": [vector_store.id]
            }
        }
    )

    print(f"✅ Assistant создан: {assistant.id}")
    print("\n" + "="*60)
    print("🎉 Настройка завершена успешно!")
    print("="*60)
    print(f"\n📋 Добавьте в .env файл:\n")
    print(f"OPENAI_ASSISTANT_ID={assistant.id}")
    print(f"\n📊 Информация:")
    print(f"   - File ID: {uploaded_file.id}")
    print(f"   - Vector Store ID: {vector_store.id}")
    print(f"   - Assistant ID: {assistant.id}")
    print("\n💡 После добавления в .env бот будет использовать базу знаний для генерации отчётов")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python tools/setup_assistant.py <путь_к_pdf>")
        print("Пример: python tools/setup_assistant.py knowledge/numerology.pdf")
        sys.exit(1)

    asyncio.run(setup_assistant(sys.argv[1]))
