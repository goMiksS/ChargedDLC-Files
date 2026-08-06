import aiosqlite
import datetime

DB_PATH = "bot_database.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                trial_used INTEGER DEFAULT 0,
                subscription_until TEXT,
                joined_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                timestamp TEXT
            )
        """)
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, trial_used, subscription_until, joined_at FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def add_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        now = datetime.datetime.now().isoformat()
        await db.execute("INSERT OR IGNORE INTO users (user_id, trial_used, subscription_until, joined_at) VALUES (?, 0, NULL, ?)", (user_id, now))
        await db.commit()

async def activate_trial(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        until = (datetime.datetime.now() + datetime.timedelta(days=3)).isoformat()
        await db.execute("UPDATE users SET trial_used = 1, subscription_until = ? WHERE user_id = ?", (until, user_id))
        await db.commit()

async def log_action(user_id: int, action: str):
    async with aiosqlite.connect(DB_PATH) as db:
        now = datetime.datetime.now().isoformat()
        await db.execute("INSERT INTO activity_logs (user_id, action, timestamp) VALUES (?, ?, ?)", (user_id, action, now))
        await db.commit()

async def get_user_logs(user_id: int, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT action, timestamp FROM activity_logs WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit)) as cursor:
            return await cursor.fetchall()

async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, subscription_until FROM users") as cursor:
            return await cursor.fetchall()
