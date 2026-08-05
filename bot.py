import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from config import BOT_TOKEN
from database import init_db
from handlers import register_handlers

logging.basicConfig(level=logging.INFO)

async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="stats", description="Статистика удалений"),
        BotCommand(command="top", description="Топ нарушителей"),
        BotCommand(command="activity", description="Активность сегодня"),
        BotCommand(command="search", description="Поиск по сообщениям"),
        BotCommand(command="last", description="Последние сообщения"),
        BotCommand(command="find", description="Найти по дате"),
        BotCommand(command="user", description="Информация о пользователе"),
        BotCommand(command="whois", description="Расширенная информация"),
        BotCommand(command="avatar", description="Аватар пользователя"),
        BotCommand(command="blacklist", description="Управление ЧС"),
        BotCommand(command="settings", description="Настройки"),
        BotCommand(command="mode", description="Режим отслеживания"),
        BotCommand(command="notify", description="Уведомления"),
        BotCommand(command="export", description="Экспорт данных"),
        BotCommand(command="status", description="Статус бота"),
        BotCommand(command="clean", description="Очистка временных данных"),
        BotCommand(command="report", description="Отчёт по чату"),
    ]
    await bot.set_my_commands(commands)

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    init_db()
    register_handlers(dp, bot)
    await set_commands(bot)
    
    logging.info("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
