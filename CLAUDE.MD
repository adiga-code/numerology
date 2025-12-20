# Numerology Bot - Project Documentation

## Project Overview

This is a Telegram bot for providing numerology services. The bot handles user orders for numerological readings, processes payment, and generates personalized PDF reports based on birth data.

## Technology Stack

- **Language**: Python 3.12+
- **Bot Framework**: aiogram (Telegram Bot API wrapper)
- **Database**: PostgreSQL (via asyncpg)
- **Async Framework**: asyncio
- **Environment Management**: python-dotenv

## Project Structure

```
numerology/
├── src/
│   ├── main.py              # Application entry point
│   ├── bot.py               # Bot initialization and setup
│   ├── config.py            # Configuration management
│   ├── database/
│   │   ├── __init__.py
│   │   └── database.py      # Database operations and models
│   ├── handlers/
│   │   ├── __init__.py
│   │   └── commands.py      # Command handlers for bot
│   └── utils/
│       ├── __init__.py
│       ├── entities.py      # Data models and entities
│       └── enums.py         # Enumerations for types
├── .gitignore
└── CLAUDE.MD                # This file
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

## Enumerations

The project uses enums for type safety (defined in `src/utils/enums.py`):
- **TariffType**: Different service pricing tiers
- **StyleType**: Report presentation styles
- **OrderStatus**: Order lifecycle states
- **Currency**: Supported payment currencies
- **PaymentMethod**: Available payment options
- **ParticipantType**: Role in the reading (self, partner, child, etc.)
- **Rating**: Review rating scale
- **AiProvider**: AI service providers used
- **AiLogStatus**: AI processing status

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
BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=postgresql://user:password@host:port/database
```

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your values

# Run the bot
python src/main.py
```

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
