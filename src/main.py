import asyncio

from config import Config
from bot import NumerologBot

async def main():
    config = Config()
    numerolog_bot = NumerologBot(config)
    try:
        await numerolog_bot.start()
    finally:
        pass

try:
    if __name__ == "__main__":
        asyncio.run(main())
except (KeyboardInterrupt, SystemExit):
    print("Bot stopped!")