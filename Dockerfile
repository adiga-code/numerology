FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей для WeasyPrint
RUN apt-get update && apt-get install -y \
    # Основные библиотеки WeasyPrint
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    # Шрифты для кириллицы
    fonts-dejavu \
    fonts-liberation \
    # Очистка кеша
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Запуск приложения
CMD ["python", "src/main.py"]
