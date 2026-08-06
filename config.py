import os

# Основные настройки бота
BOT_TOKEN = "8836466924:AAG9JHWBmNN9voqfWY-6aRK3PdKl4eJ46VU"
ADMIN_ID = 5115505064

# Информация о боте
BOT_NAME = "ModdedInvoker"
VERSION = "2.0.0"
CMD_PREFIX = "."

# База данных и файлы
DB_PATH = "bot_database.db"
MEDIA_DIR = "media"

# Ограничения и подписки
TRIAL_DAYS = 3

# Тарифы VIP (Telegram Stars - XTR)
VIP_PLANS = {
    "vip_7": {
        "title": "VIP 7 дней",
        "days": 7,
        "price": 50
    },
    "vip_30": {
        "title": "VIP 30 дней",
        "days": 30,
        "price": 150
    },
    "vip_365": {
        "title": "VIP 1 год",
        "days": 365,
        "price": 1000
    }
}

# Автоматическое создание папки для медиа
if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)
