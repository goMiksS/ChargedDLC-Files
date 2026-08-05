import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
DB_NAME = "messages.db"

# Настройки логирования
LOG_CHAT_ID = ADMIN_ID  # Куда отправлять логи
