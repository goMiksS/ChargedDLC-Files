import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "8836466924:AAG9JHWBmNN9voqfWY-6aRK3PdKl4eJ46VU")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "5115505064").split(",") if x.isdigit()]
TRIAL_DAYS = 3
