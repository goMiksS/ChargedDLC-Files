import asyncio
import logging
import sys
import os
from pathlib import Path

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, MEDIA_DIR, LOCAL_SERVER_URL, BOT_NAME
from db.database import init_db, clean_old_messages
from handlers import commands, business, fun, games


async def on_startup(bot: Bot):
    Path(MEDIA_DIR).mkdir(exist_ok=True)
    await init_db()
    await clean_old_messages()
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass
    me = await bot.get_me()
    print(f"✅ {me.full_name} (@{me.username}) | {BOT_NAME} v2.0 Started")


async def health(_request):
    return web.Response(text="OK")


async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    # Подключение сессии для работы с локальным Telegram Bot API (снятие лимита 20 МБ)
    if LOCAL_SERVER_URL:
        session = AiohttpSession(
            api=TelegramAPIServer.from_base(LOCAL_SERVER_URL, is_local=True)
        )
        bot = Bot(
            token=BOT_TOKEN,
            session=session,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
    else:
        bot = Bot(
            token=BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

    dp = Dispatcher(storage=MemoryStorage())

    # Регистрация роутеров
    dp.include_router(commands.router)
    dp.include_router(fun.router)
    dp.include_router(games.router)
    dp.include_router(business.router)

    dp.startup.register(on_startup)

    # Веб-сервер проверки работоспособности (для хостинга)
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Health server listening on :{port}")

    await dp.start_polling(
        bot,
        allowed_updates=[
            "message",
            "callback_query",
            "pre_checkout_query",
            "business_connection",
            "business_message",
            "edited_business_message",
            "deleted_business_messages",
        ],
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Stopped")
