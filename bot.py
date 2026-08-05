import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, MEDIA_DIR
from db.database import init_db, clean_old_messages
from handlers import commands, business, fun

async def on_startup(bot: Bot):
    Path(MEDIA_DIR).mkdir(exist_ok=True)
    await init_db()
    await clean_old_messages()
    me = await bot.get_me()
    print(f"✅ {me.full_name} (@{me.username}) запущен | ModdedInvoker")

async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.include_router(commands.router)
    dp.include_router(fun.router)
    dp.include_router(business.router)

    dp.startup.register(on_startup)

    await dp.start_polling(
        bot,
        allowed_updates=[
            "message",
            "callback_query",
            "business_connection",
            "business_message",
            "edited_business_message",
            "deleted_business_messages",
        ]
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен")
