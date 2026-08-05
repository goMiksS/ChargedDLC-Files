import asyncio
import logging
from datetime import datetime
from pyrogram import Client, filters, types
from pyrogram.enums import ChatType, MessagesFilter
from config import API_ID, API_HASH, PHONE_NUMBER, ADMIN_ID
from database import *

logging.basicConfig(level=logging.INFO)

app = Client("my_account", api_id=API_ID, api_hash=API_HASH, phone_number=PHONE_NUMBER)

# ============ СОХРАНЕНИЕ СООБЩЕНИЙ ============
@app.on_message(filters.private | filters.group)
async def save_message(client, message: types.Message):
    # Пропускаем свои сообщения (чтобы не зациклить)
    if message.from_user and message.from_user.is_self:
        return
    
    chat_name = message.chat.title or message.chat.first_name or "Unknown"
    sender_name = message.from_user.first_name or "Unknown"
    if message.from_user.last_name:
        sender_name += f" {message.from_user.last_name}"
    
    # Сохраняем в БД
    save_message(
        message.id,
        message.chat.id,
        chat_name,
        message.from_user.id if message.from_user else 0,
        sender_name,
        message.text or message.caption or "",
        int(message.date.timestamp())
    )
    
    # Обновляем статистику
    if message.from_user:
        increment_stat(message.chat.id, message.from_user.id, "messages_count")

# ============ ОТСЛЕЖИВАНИЕ УДАЛЕНИЙ ============
@app.on_deleted_messages()
async def handle_deleted(client, messages):
    for message in messages:
        old = get_message(message.id, message.chat.id)
        if old:
            mark_deleted(message.id, message.chat.id)
            increment_stat(message.chat.id, old[4], "deleted_count")
            
            # Уведомление админу
            await app.send_message(
                ADMIN_ID,
                f"🗑️ <b>Удалено сообщение</b>\n"
                f"👤 {old[5]}\n"
                f"📝 {old[6][:200]}\n"
                f"⏱️ {format_date(old[7])}",
                parse_mode="HTML"
            )

# ============ ОТСЛЕЖИВАНИЕ ИЗМЕНЕНИЙ ============
@app.on_edited_message()
async def handle_edited(client, message: types.Message):
    old = get_message(message.id, message.chat.id)
    if old:
        update_message_text(message.id, message.chat.id, message.text or "")
        increment_stat(message.chat.id, message.from_user.id, "edited_count")
        
        await app.send_message(
            ADMIN_ID,
            f"✏️ <b>Изменено сообщение</b>\n"
            f"👤 {old[5]}\n"
            f"📝 Было: {old[6][:100]}\n"
            f"📝 Стало: {(message.text or '')[:100]}\n"
            f"⏱️ {format_date(old[7])}",
            parse_mode="HTML"
        )

# ============ КОМАНДЫ ============
@app.on_message(filters.command(["start", "help"]) & filters.private)
async def cmd_start(client, message):
    await message.reply(
        "🤖 <b>SaveMod Clone (UserBot)</b>\n\n"
        "Сохраняю все сообщения и отслеживаю удаления!\n\n"
        "📋 Команды:\n"
        "/stats - Статистика\n"
        "/search <текст> - Поиск\n"
        "/last [N] - Последние N сообщений\n"
        "/user @username - Инфо о пользователе\n"
        "/export - Экспорт\n"
        "/status - Статус",
        parse_mode="HTML"
    )

@app.on_message(filters.command("stats") & filters.private)
async def cmd_stats(client, message):
    stats = get_stats()
    if not stats:
        await message.reply("📊 Статистика пока пуста")
        return
    text = "📊 <b>Общая статистика</b>\n\n"
    for stat in stats[:10]:
        text += f"👤 {stat[2]}: 🗑️{stat[3]} ✏️{stat[4]} 💬{stat[5]}\n"
    await message.reply(text, parse_mode="HTML")

@app.on_message(filters.command("search") & filters.private)
async def cmd_search(client, message):
    if len(message.text.split()) < 2:
        await message.reply("❌ Укажите текст: /search привет")
        return
    query = " ".join(message.text.split()[1:])
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT sender_name, text, date FROM messages 
        WHERE text LIKE ? AND is_deleted = 0
        ORDER BY date DESC LIMIT 20
    ''', (f'%{query}%',))
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        await message.reply(f"🔍 Ничего не найдено: {query}")
        return
    
    text = f"🔍 <b>Результаты:</b> \"{query}\"\n\n"
    for row in rows[:10]:
        text += f"👤 {row[0]}: {row[1][:60]}\n⏱️ {format_date(row[2])}\n\n"
    await message.reply(text, parse_mode="HTML")

@app.on_message(filters.command("last") & filters.private)
async def cmd_last(client, message):
    args = message.text.split()
    n = int(args[1]) if len(args) > 1 and args[1].isdigit() else 10
    n = min(n, 50)
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT sender_name, text, date FROM messages 
        WHERE is_deleted = 0
        ORDER BY date DESC LIMIT ?
    ''', (n,))
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        await message.reply("📭 Нет сообщений")
        return
    
    text = f"📋 <b>Последние {n} сообщений</b>\n\n"
    for row in reversed(rows):
        text += f"👤 {row[0]}: {row[1][:60]}\n⏱️ {format_date(row[2])}\n\n"
        if len(text) > 3500:
            break
    await message.reply(text, parse_mode="HTML")

@app.on_message(filters.command("user") & filters.private)
async def cmd_user(client, message):
    if len(message.text.split()) < 2:
        await message.reply("❌ Укажите пользователя: /user @username")
        return
    username = message.text.split()[1].replace("@", "")
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT sender_name, COUNT(*), 
               SUM(CASE WHEN is_deleted=1 THEN 1 ELSE 0 END),
               SUM(CASE WHEN is_edited=1 THEN 1 ELSE 0 END)
        FROM messages 
        WHERE sender_name LIKE ?
        GROUP BY sender_name
    ''', (f'%{username}%',))
    row = cur.fetchone()
    conn.close()
    
    if not row:
        await message.reply(f"❌ Пользователь @{username} не найден")
        return
    
    await message.reply(
        f"👤 <b>Информация о пользователе</b>\n\n"
        f"Имя: {row[0]}\n"
        f"💬 Сообщений: {row[1]}\n"
        f"🗑️ Удалений: {row[2]}\n"
        f"✏️ Изменений: {row[3]}",
        parse_mode="HTML"
    )

@app.on_message(filters.command("export") & filters.private)
async def cmd_export(client, message):
    await message.reply("⏳ Формирую экспорт...")
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT sender_name, text, date, is_deleted, is_edited 
        FROM messages 
        ORDER BY date DESC LIMIT 1000
    ''')
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        await message.reply("📭 Нет данных")
        return
    
    import json, io
    data = [{"sender": r[0], "text": r[1], "date": format_date(r[2]), 
             "deleted": bool(r[3]), "edited": bool(r[4])} for r in rows]
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    file = io.BytesIO(json_str.encode('utf-8'))
    file.name = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    await client.send_document(ADMIN_ID, file, caption="📊 Экспорт данных")
    await message.reply("✅ Экспорт отправлен")

@app.on_message(filters.command("status") & filters.private)
async def cmd_status(client, message):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM messages')
    total = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM messages WHERE is_deleted=1')
    deleted = cur.fetchone()[0]
    conn.close()
    
    await message.reply(
        f"📊 <b>Статус UserBot</b>\n\n"
        f"💬 Сохранено: {total}\n"
        f"🗑️ Удалено: {deleted}\n"
        f"✅ Активен\n"
        f"🔄 Версия: 3.0 (MTProto)",
        parse_mode="HTML"
    )

# ============ ЗАПУСК ============
if __name__ == "__main__":
    init_db()
    logging.info("🔥 UserBot запускается...")
    app.run()
