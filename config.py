import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("8836466924:AAG9JHWBmNN9voqfWY-6aRK3PdKl4eJ46VU")
ADMIN_ID = int(os.getenv("5115505064", 0))
DB_NAME = "messages.db"

# Настройки логирования
LOG_CHAT_ID = ADMIN_ID  # Куда отправлять логи
