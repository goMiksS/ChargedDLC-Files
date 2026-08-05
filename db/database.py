import aiosqlite
import json
from datetime import datetime, timedelta
from pathlib import Path
from config import DB_PATH, MAX_MESSAGES_PER_USER, AUTO_CLEAN_DAYS

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                business_connection_id TEXT,
                joined_at TEXT,
                settings TEXT DEFAULT '{}',
                is_active INTEGER DEFAULT 1,
                messages_saved INTEGER DEFAULT 0,
                deletes_caught INTEGER DEFAULT 0,
                edits_caught INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                chat_id INTEGER,
                message_id INTEGER,
                from_user_id INTEGER,
                from_username TEXT,
                from_name TEXT,
                content_type TEXT,
                text TEXT,
                caption TEXT,
                file_id TEXT,
                file_path TEXT,
                raw_json TEXT,
                created_at TEXT,
                is_deleted INTEGER DEFAULT 0,
                is_edited INTEGER DEFAULT 0,
                UNIQUE(user_id, chat_id, message_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS edits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_row_id INTEGER,
                old_text TEXT,
                new_text TEXT,
                edited_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                user_id INTEGER PRIMARY KEY,
                total_saved INTEGER DEFAULT 0,
                total_deleted INTEGER DEFAULT 0,
                total_edited INTEGER DEFAULT 0,
                media_saved INTEGER DEFAULT 0,
                last_active TEXT
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_msg_user ON messages(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_msg_chat ON messages(chat_id, message_id)")
        # VIP / trial columns
        try:
            await db.execute("ALTER TABLE users ADD COLUMN subscription_until TEXT")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN is_vip INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN trial_used INTEGER DEFAULT 0")
        except Exception:
            pass
        await db.commit()

async def register_user(user_id: int, username: str, full_name: str, business_connection_id: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO users (user_id, username, full_name, business_connection_id, joined_at, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (user_id, username, full_name, business_connection_id, datetime.now().isoformat()))
        await db.execute("""
            INSERT OR IGNORE INTO stats (user_id, last_active) VALUES (?, ?)
        """, (user_id, datetime.now().isoformat()))
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
            return await cur.fetchone()

async def update_user_settings(user_id: int, settings: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET settings = ? WHERE user_id = ?", (json.dumps(settings), user_id))
        await db.commit()

async def get_user_settings(user_id: int) -> dict:
    user = await get_user(user_id)
    if not user:
        return {}
    try:
        return json.loads(user["settings"] or "{}")
    except:
        return {}

async def save_message(user_id: int, chat_id: int, message_id: int, from_user_id: int,
                       from_username: str, from_name: str, content_type: str,
                       text: str = None, caption: str = None, file_id: str = None,
                       file_path: str = None, raw_json: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        # Лимит
        async with db.execute("SELECT COUNT(*) FROM messages WHERE user_id = ?", (user_id,)) as cur:
            count = (await cur.fetchone())[0]
        if count >= MAX_MESSAGES_PER_USER:
            # Удаляем самые старые
            await db.execute("""
                DELETE FROM messages WHERE id IN (
                    SELECT id FROM messages WHERE user_id = ? ORDER BY created_at ASC LIMIT 100
                )
            """, (user_id,))

        await db.execute("""
            INSERT OR REPLACE INTO messages
            (user_id, chat_id, message_id, from_user_id, from_username, from_name,
             content_type, text, caption, file_id, file_path, raw_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, chat_id, message_id, from_user_id, from_username, from_name,
              content_type, text, caption, file_id, file_path, raw_json, datetime.now().isoformat()))
        await db.execute("UPDATE stats SET total_saved = total_saved + 1, last_active = ? WHERE user_id = ?",
                         (datetime.now().isoformat(), user_id))
        await db.execute("UPDATE users SET messages_saved = messages_saved + 1 WHERE user_id = ?", (user_id,))
        await db.commit()

async def get_saved_message(user_id: int, chat_id: int, message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM messages WHERE user_id = ? AND chat_id = ? AND message_id = ?
        """, (user_id, chat_id, message_id)) as cur:
            return await cur.fetchone()

async def mark_deleted(user_id: int, chat_id: int, message_ids: list):
    async with aiosqlite.connect(DB_PATH) as db:
        for mid in message_ids:
            await db.execute("""
                UPDATE messages SET is_deleted = 1 WHERE user_id = ? AND chat_id = ? AND message_id = ?
            """, (user_id, chat_id, mid))
        await db.execute("UPDATE stats SET total_deleted = total_deleted + ? WHERE user_id = ?",
                         (len(message_ids), user_id))
        await db.execute("UPDATE users SET deletes_caught = deletes_caught + ? WHERE user_id = ?",
                         (len(message_ids), user_id))
        await db.commit()

async def save_edit(user_id: int, chat_id: int, message_id: int, old_text: str, new_text: str):
    async with aiosqlite.connect(DB_PATH) as db:
        row = await get_saved_message(user_id, chat_id, message_id)
        if row:
            await db.execute("""
                INSERT INTO edits (message_row_id, old_text, new_text, edited_at)
                VALUES (?, ?, ?, ?)
            """, (row["id"], old_text, new_text, datetime.now().isoformat()))
            await db.execute("UPDATE messages SET is_edited = 1, text = ? WHERE id = ?", (new_text, row["id"]))
            await db.execute("UPDATE stats SET total_edited = total_edited + 1 WHERE user_id = ?", (user_id,))
            await db.execute("UPDATE users SET edits_caught = edits_caught + 1 WHERE user_id = ?", (user_id,))
            await db.commit()

async def get_user_stats(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM stats WHERE user_id = ?", (user_id,)) as cur:
            return await cur.fetchone()

async def get_all_users_count():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE is_active = 1") as cur:
            return (await cur.fetchone())[0]

async def clean_old_messages():
    cutoff = (datetime.now() - timedelta(days=AUTO_CLEAN_DAYS)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM messages WHERE created_at < ?", (cutoff,))
        await db.commit()

async def search_messages(user_id: int, query: str, limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM messages
            WHERE user_id = ? AND (text LIKE ? OR caption LIKE ?)
            ORDER BY created_at DESC LIMIT ?
        """, (user_id, f"%{query}%", f"%{query}%", limit)) as cur:
            return await cur.fetchall()

async def export_user_messages(user_id: int, limit: int = 1000):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM messages WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
        """, (user_id, limit)) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_subscription(user_id: int) -> dict:
    """Возвращает статус подписки."""
    from datetime import datetime
    user = await get_user(user_id)
    if not user:
        return {"active": False, "until": None, "is_vip": False, "trial_used": False}
    until = user["subscription_until"] if "subscription_until" in user.keys() else None
    is_vip = bool(user["is_vip"]) if "is_vip" in user.keys() else False
    trial_used = bool(user["trial_used"]) if "trial_used" in user.keys() else False
    active = False
    if until:
        try:
            active = datetime.fromisoformat(until) > datetime.now()
        except Exception:
            active = False
    return {"active": active, "until": until, "is_vip": is_vip and active, "trial_used": trial_used}


async def grant_days(user_id: int, days: int, make_vip: bool = True):
    """Выдать дни подписки (админ)."""
    from datetime import datetime, timedelta
    import aiosqlite
    from config import DB_PATH
    sub = await get_subscription(user_id)
    now = datetime.now()
    if sub["until"]:
        try:
            base = datetime.fromisoformat(sub["until"])
            if base < now:
                base = now
        except Exception:
            base = now
    else:
        base = now
    new_until = (base + timedelta(days=days)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET subscription_until = ?, is_vip = ? WHERE user_id = ?",
            (new_until, 1 if make_vip else 0, user_id)
        )
        await db.commit()
    return new_until


async def start_trial(user_id: int, days: int = 3) -> bool:
    """Запустить пробный период. Возвращает True если выдан."""
    from datetime import datetime, timedelta
    import aiosqlite
    from config import DB_PATH
    sub = await get_subscription(user_id)
    if sub["trial_used"] or sub["active"]:
        return False
    until = (datetime.now() + timedelta(days=days)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET subscription_until = ?, is_vip = 1, trial_used = 1 WHERE user_id = ?",
            (until, user_id)
        )
        await db.commit()
    return True


async def has_access(user_id: int) -> bool:
    """Есть ли доступ (trial/VIP или админ)."""
    from config import ADMIN_ID
    if user_id == ADMIN_ID:
        return True
    sub = await get_subscription(user_id)
    return sub["active"]
