# Numerology Bot - Project Documentation

## Project Overview

Автоматизированный Telegram-бот для генерации персонализированных нумерологических отчётов с использованием AI (Manus API, GPT-4, Gemini) с интеграцией платёжных систем и CRM.

## Technology Stack

- **Language**: Python 3.11+
- **Bot Framework**: aiogram 3.x
- **Web Server**: FastAPI (для webhook)
- **Database**: PostgreSQL 15+
- **Cache**: Redis 7+
- **ORM**: SQLAlchemy 2.0 (async)
- **Migrations**: Alembic
- **AI Services**: Manus API, OpenAI GPT-4, Google Gemini
- **Payments**: ЮKassa API, Telegram Stars
- **Infrastructure**: Docker + Docker Compose
- **PDF Generation**: WeasyPrint + Jinja2

## Project Structure

```
numerology/
├── src/
│   ├── main.py                    # Application entry point (Bot + FastAPI)
│   ├── bot.py                     # Bot initialization
│   ├── api.py                     # FastAPI application
│   ├── config.py                  # Configuration
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py              # SQLAlchemy models
│   │   └── database.py            # Database connection
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── commands.py            # Command handlers
│   │   ├── order_flow.py          # Order creation flow
│   │   └── payments.py            # Payment handlers
│   ├── services/
│   │   ├── __init__.py
│   │   ├── manus.py               # Manus API client
│   │   ├── ai_fallback.py         # GPT-4/Gemini fallback
│   │   ├── payments.py            # Payment processing
│   │   └── pdf_generator.py      # PDF generation
│   ├── webhooks/
│   │   ├── __init__.py
│   │   ├── manus.py               # Manus webhook handler
│   │   └── yookassa.py            # ЮKassa webhook handler
│   └── utils/
│       ├── __init__.py
│       ├── enums.py               # Enumerations
│       └── states.py              # FSM states
├── alembic/                       # Database migrations
├── templates/                     # Jinja2 templates for PDF
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── .gitignore
└── CLAUDE.MD
```

## Core Components

### 1. Main Application (`src/main.py`)
- Entry point for the application
- Initializes Config and NumerologBot
- Handles asyncio event loop and graceful shutdown

### 2. Bot (`src/bot.py`)
- **NumerologBot class**: Main bot controller
- Manages aiogram Bot and Dispatcher instances
- Sets up handlers and components
- Initializes database connection
- Starts polling for messages

### 3. Configuration (`src/config.py`)
- Loads environment variables from `.env` file
- Required variables:
  - `BOT_TOKEN`: Telegram bot token
  - `DATABASE_URL`: PostgreSQL connection string

### 4. Database (`src/database/database.py`)
- **DatabaseManager class**: Handles all database operations
- Manages connection pool
- Implements CRUD operations for:
  - Orders
  - Order participants
  - Reviews
  - AI logs

### 5. Handlers (`src/handlers/commands.py`)
- **CommandHandlers class**: Telegram command handlers
- Implemented commands:
  - `/start` - Welcome message
  - `/help` - Help information
- Planned handlers:
  - `new_order_handler` - Create new numerology order
  - `get_history_handler` - View order history
  - `support_handler` - Contact support

## Data Models

### Order
- Represents a numerology service order
- Fields: id, order_uuid, user_id, tariff, style, status, amount, currency, payment info, PDF URL, timestamps
- Supports multiple tariff types and styles
- Tracks payment method and completion status

### OrderParticipant
- Person included in the numerology reading
- Fields: id, order_id, full_name, birth_date, birth_time, birth_place, participant_type
- Supports multiple participants per order

### Review
- Customer feedback for completed orders
- Fields: id, order_id, user_id, rating, comment, created_at

### AiLog
- Tracks AI provider usage for generating reports
- Fields: id, order_id, provider, task_id, status, error_message, tokens_used, created_at

## Tariffs (Тарифы)

| Тариф | Описание | Объём | Участников | Цена |
|-------|----------|-------|------------|------|
| quick | Быстрый взгляд | 5-7 стр | 1 | 500₽ |
| deep | Глубокий анализ | 15-20 стр | 1 | 1500₽ |
| pair | Парный Оракул | 15-25 стр | 2 | 2000₽ |
| family | Семейный Оракул | 30-50 стр | 3-5 | 3000₽ |

## Enumerations

- **TariffType**: quick, deep, pair, family
- **StyleType**: analytical (аналитический), shamanic (шаманский)
- **OrderStatus**: pending, paid, processing, completed, failed, refunded
- **Currency**: RUB
- **PaymentMethod**: yookassa, telegram_stars
- **ParticipantType**: main, partner, family_member
- **Rating**: 1-5
- **AiProvider**: manus, gpt4, gemini
- **AiLogStatus**: pending, success, failed

## Development Guidelines

### Code Style
- Russian language used in comments and user-facing messages
- Type hints required for function parameters and return values
- Docstrings for all classes and methods
- Async/await pattern for all I/O operations

### Database Operations
- All database operations are asynchronous
- Use connection pooling for efficiency
- Implement proper error handling for database failures

### Bot Message Flow
1. User sends command
2. Handler processes command
3. Database operations if needed
4. Response sent to user
5. Errors logged and handled gracefully

### Environment Setup
Required environment variables in `.env`:
```
BOT_TOKEN=
MANUS_API_KEY=
OPENAI_API_KEY=
GEMINI_API_KEY=
YOOKASSA_SHOP_ID=
YOOKASSA_SECRET_KEY=
DATABASE_URL=postgresql://user:password@db:5432/numerology
REDIS_URL=redis://redis:6379/0
WEBHOOK_DOMAIN=https://your-domain.com
```

## Running the Application

### With Docker (Production)
```bash
# Set up environment variables
cp .env.example .env
# Edit .env with your values

# Build and run
docker-compose up --build
```

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Run the bot
python src/main.py
```

## User Flow (Пользовательский сценарий)

1. **Начало**: /start → выбор тарифа
2. **Сбор данных**: ФИО, дата рождения, время, место (для каждого участника)
3. **Выбор стиля**: Аналитический / Шаманский
4. **Оплата**: ЮKassa или Telegram Stars (таймаут 15 минут)
5. **Генерация**: Отправка в Manus API (10-15 минут)
6. **Fallback**: Manus → GPT-4 → Gemini → возврат средств
7. **Получение**: PDF отчёт в Telegram
8. **Отзыв**: Через 1 час - оценка 1-5 звёзд

## Future Enhancements

Based on the codebase structure, planned features include:
- Complete implementation of order creation flow
- Payment processing integration
- PDF report generation with AI
- Order history and tracking
- Review system for completed orders
- Admin panel for order management
- Support ticket system

## Notes for AI Assistant

- The project is in early development stage
- Core handlers (`new_order_handler`, `get_history_handler`, `support_handler`) are defined but not registered to router
- Database schema needs to be defined/migrated
- Payment provider integration pending
- AI report generation system pending implementation
- No tests currently implemented
- Russian language is used for user-facing content
