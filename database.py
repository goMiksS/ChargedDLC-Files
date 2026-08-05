import sqlite3
from datetime import datetime
from config import DB_NAME

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    
    # Таблица сообщений
    cur.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            msg_id INTEGER,
            chat_id INTEGER,
            chat_name TEXT,
            sender_id INTEGER,
            sender_name TEXT,
            text TEXT,
            date INTEGER,
            is_edited INTEGER DEFAULT 0,
            is_deleted INTEGER DEFAULT 0,
            media_type TEXT,
            media_file_id TEXT
        )
    ''')
    
    # Таблица статистики
    cur.execute('''
        CREATE TABLE IF NOT EXISTS stats (
            chat_id INTEGER,
            user_id INTEGER,
            deleted_count INTEGER DEFAULT 0,
            edited_count INTEGER DEFAULT 0,
            messages_count INTEGER DEFAULT 0,
            PRIMARY KEY (chat_id, user_id)
        )
    ''')
    
    # Таблица пользователей для чёрного списка
    cur.execute('''
        CREATE TABLE IF NOT EXISTS blacklist (
            user_id INTEGER PRIMARY KEY,
            reason TEXT,
            date INTEGER
        )
    ''')
    
    # Таблица настроек
    cur.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# --- CRUD для сообщений ---
def save_message(msg_id, chat_id, chat_name, sender_id, sender_name, text, date, media_type=None, media_file_id=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT OR REPLACE INTO messages 
        (msg_id, chat_id, chat_name, sender_id, sender_name, text, date, media_type, media_file_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (msg_id, chat_id, chat_name, sender_id, sender_name, text or "", date, media_type, media_file_id))
    conn.commit()
    conn.close()

def get_message(msg_id, chat_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM messages WHERE msg_id=? AND chat_id=?', (msg_id, chat_id))
    row = cur.fetchone()
    conn.close()
    return row

def mark_deleted(msg_id, chat_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('UPDATE messages SET is_deleted=1 WHERE msg_id=? AND chat_id=?', (msg_id, chat_id))
    conn.commit()
    conn.close()

def mark_edited(msg_id, chat_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('UPDATE messages SET is_edited=1 WHERE msg_id=? AND chat_id=?', (msg_id, chat_id))
    conn.commit()
    conn.close()

def update_message_text(msg_id, chat_id, new_text):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('UPDATE messages SET text=?, is_edited=1 WHERE msg_id=? AND chat_id=?', 
                (new_text, msg_id, chat_id))
    conn.commit()
    conn.close()

# --- Статистика ---
def increment_stat(chat_id, user_id, field):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f'''
        INSERT INTO stats (chat_id, user_id, {field}) 
        VALUES (?, ?, 1)
        ON CONFLICT(chat_id, user_id) DO UPDATE SET {field} = {field} + 1
    ''', (chat_id, user_id))
    conn.commit()
    conn.close()

def get_stats(chat_id=None, user_id=None):
    conn = get_connection()
    cur = conn.cursor()
    if chat_id and user_id:
        cur.execute('SELECT * FROM stats WHERE chat_id=? AND user_id=?', (chat_id, user_id))
    elif chat_id:
        cur.execute('SELECT * FROM stats WHERE chat_id=? ORDER BY deleted_count DESC', (chat_id,))
    else:
        cur.execute('SELECT * FROM stats ORDER BY deleted_count DESC')
    rows = cur.fetchall()
    conn.close()
    return rows

# --- Чёрный список ---
def add_blacklist(user_id, reason):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('INSERT OR REPLACE INTO blacklist VALUES (?, ?, ?)', 
                (user_id, reason, int(datetime.now().timestamp())))
    conn.commit()
    conn.close()

def remove_blacklist(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM blacklist WHERE user_id=?', (user_id,))
    conn.commit()
    conn.close()

def is_blacklisted(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT 1 FROM blacklist WHERE user_id=?', (user_id,))
    row = cur.fetchone()
    conn.close()
    return row is not None

def get_blacklist():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM blacklist')
    rows = cur.fetchall()
    conn.close()
    return rows

# --- Настройки ---
def get_setting(key):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT value FROM settings WHERE key=?', (key,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def set_setting(key, value):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('INSERT OR REPLACE INTO settings VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()
