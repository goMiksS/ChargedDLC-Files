import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
PHONE_NUMBER = os.getenv("+79036476677")
ADMIN_ID = int(os.getenv("5115505064", 0))
DB_NAME = "messages.db"
