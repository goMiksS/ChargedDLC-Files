from aiogram import Bot, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
from datetime import datetime
import json

from config import ADMIN_ID, LOG_CHAT_ID
from database import *
from utils import *

# --- Словарь для временных данных ---
temp_data = {}

def register_handlers(dp, bot: Bot):
    
    # ============ ОСНОВНЫЕ КОМАНДЫ ============
    
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        await message.answer(
            "🤖 <b>SaveMod Clone</b>\n\n"
            "Бот сохраняет все сообщения и отслеживает удаления/изменения.\n\n"
            "📋 <b>Команды:</b>\n"
            "/stats - Статистика удалений\n"
            "/search <текст> - Поиск по сообщениям\n"
            "/last [N] - Последние N сообщений\n"
            "/user @username - Инфо о пользователе\n"
            "/export - Экспорт данных (JSON)\n"
            "/blacklist - Управление ЧС\n"
            "/settings - Настройки бота\n"
            "/help - Помощь",
            parse_mode="HTML"
        )
    
    @dp.message(Command("help"))
    async def cmd_help(message: types.Message):
        help_text = """
📚 <b>Полный список команд</b>

<b>📊 Статистика и мониторинг</b>
/stats [@user] - Статистика удалений/изменений
/top - Топ нарушителей
/activity - Активность сегодня

<b>🔍 Поиск и история</b>
/search <текст> - Поиск по сохранённым сообщениям
/last [N] - Показать последние N сообщений (по умолчанию 10)
/find <дата> - Найти сообщения по дате (ДД.ММ.ГГГГ)

<b>👤 Информация о пользователях</b>
/user @username - Информация о пользователе
/whois @username - Расширенная информация
/avatar @username - Показать аватарку

<b>🛡️ Безопасность</b>
/blacklist add @username - Добавить в ЧС
/blacklist remove @username - Удалить из ЧС
/blacklist list - Список ЧС

<b>⚙️ Настройки</b>
/settings - Открыть панель настроек
/mode [all|chats] - Режим отслеживания
/notify [on|off] - Включить/выключить уведомления

<b>💾 Экспорт</b>
/export - Экспорт всех сообщений (JSON)
/export user @username - Экспорт сообщений пользователя
/export date ДД.ММ.ГГГГ - Экспорт за дату

<b>🧹 Другое</b>
/clean - Очистить временные данные
/status - Статус бота
/report - Сформировать отчёт
"""
        await message.answer(help_text, parse_mode="HTML")
    
    # ============ СТАТИСТИКА ============
    
    @dp.message(Command("stats"))
    async def cmd_stats(message: types.Message, command: CommandObject):
        args = command.args
        if args and args.startswith('@'):
            username = args[1:]
            # Ищем пользователя
            user_id = None
            # Простой поиск по БД
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('SELECT DISTINCT sender_id, sender_name FROM messages WHERE sender_name LIKE ?', (f'%{username}%',))
            rows = cur.fetchall()
            conn.close()
            if rows:
                user_id = rows[0][0]
                stats = get_stats(user_id=user_id)
                if stats:
                    for stat in stats:
                        await message.answer(
                            f"📊 <b>Статистика пользователя</b>\n"
                            f"👤 {rows[0][1]}\n"
                            f"🗑️ Удалений: {stat[3]}\n"
                            f"✏️ Изменений: {stat[4]}\n"
                            f"💬 Сообщений: {stat[5]}",
                            parse_mode="HTML"
                        )
                        return
                await message.answer("❌ Нет данных о пользователе")
            else:
                await message.answer("❌ Пользователь не найден")
        else:
            # Общая статистика
            stats = get_stats(chat_id=message.chat.id)
            if not stats:
                await message.answer("📊 Статистика пока пуста")
                return
            text = "📊 <b>Общая статистика</b>\n\n"
            for i, stat in enumerate(stats[:10], 1):
                text += f"{i}. {stat[2]}\n"
                text += f"   🗑️ Удалений: {stat[3]} | ✏️ Изменений: {stat[4]}\n"
            await message.answer(text, parse_mode="HTML")
    
    @dp.message(Command("top"))
    async def cmd_top(message: types.Message):
        stats = get_stats(chat_id=message.chat.id)
        if not stats:
            await message.answer("📊 Нет данных")
            return
        text = "🏆 <b>Топ нарушителей</b>\n\n"
        for i, stat in enumerate(stats[:5], 1):
            text += f"{i}. {stat[2]} — {stat[3]} удалений\n"
        await message.answer(text, parse_mode="HTML")
    
    @dp.message(Command("activity"))
    async def cmd_activity(message: types.Message):
        today = datetime.now().strftime("%d.%m.%Y")
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT COUNT(*) FROM messages 
            WHERE date >= ? AND chat_id = ?
        ''', (int(datetime.now().timestamp()) - 86400, message.chat.id))
        count = cur.fetchone()[0]
        conn.close()
        await message.answer(f"📈 <b>Активность за сегодня</b>\n"
                            f"Сообщений: {count}\n"
                            f"Дата: {today}", parse_mode="HTML")
    
    # ============ ПОИСК ============
    
    @dp.message(Command("search"))
    async def cmd_search(message: types.Message, command: CommandObject):
        if not command.args:
            await message.answer("❌ Введите текст для поиска\nПример: /search привет")
            return
        
        query = command.args
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT sender_name, text, date FROM messages 
            WHERE chat_id = ? AND text LIKE ? AND is_deleted = 0
            ORDER BY date DESC LIMIT 20
        ''', (message.chat.id, f'%{query}%'))
        rows = cur.fetchall()
        conn.close()
        
        if not rows:
            await message.answer(f"🔍 Ничего не найдено по запросу: <b>{query}</b>", parse_mode="HTML")
            return
        
        text = f"🔍 <b>Результаты поиска:</b> \"{query}\"\n\n"
        for row in rows[:10]:
            text += f"👤 {row[0]}: {truncate_text(row[1], 80)}\n"
            text += f"⏱️ {format_date(row[2])}\n\n"
        
        if len(rows) > 10:
            text += f"… и ещё {len(rows) - 10} сообщений"
        
        await message.answer(text, parse_mode="HTML")
    
    @dp.message(Command("last"))
    async def cmd_last(message: types.Message, command: CommandObject):
        try:
            n = int(command.args) if command.args else 10
            n = min(n, 50)
        except:
            n = 10
        
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT sender_name, text, date FROM messages 
            WHERE chat_id = ? AND is_deleted = 0
            ORDER BY date DESC LIMIT ?
        ''', (message.chat.id, n))
        rows = cur.fetchall()
        conn.close()
        
        if not rows:
            await message.answer("📭 Нет сохранённых сообщений")
            return
        
        text = f"📋 <b>Последние {n} сообщений</b>\n\n"
        for row in reversed(rows):
            text += f"👤 {row[0]}: {truncate_text(row[1], 60)}\n"
            text += f"⏱️ {format_date(row[2])}\n\n"
            if len(text) > 3500:
                break
        
        await message.answer(text, parse_mode="HTML")
    
    @dp.message(Command("find"))
    async def cmd_find(message: types.Message, command: CommandObject):
        if not command.args:
            await message.answer("❌ Введите дату в формате ДД.ММ.ГГГГ\nПример: /find 25.12.2024")
            return
        
        try:
            date_obj = datetime.strptime(command.args, "%d.%m.%Y")
            start_ts = int(date_obj.timestamp())
            end_ts = int(start_ts + 86400)
        except:
            await message.answer("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ")
            return
        
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT sender_name, text, date FROM messages 
            WHERE chat_id = ? AND date BETWEEN ? AND ? AND is_deleted = 0
            ORDER BY date DESC LIMIT 30
        ''', (message.chat.id, start_ts, end_ts))
        rows = cur.fetchall()
        conn.close()
        
        if not rows:
            await message.answer(f"📭 Нет сообщений за {command.args}")
            return
        
        text = f"📅 <b>Сообщения за {command.args}</b>\n\n"
        for row in rows[:15]:
            text += f"👤 {row[0]}: {truncate_text(row[1], 60)}\n"
        
        await message.answer(text, parse_mode="HTML")
    
    # ============ ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЯХ ============
    
    @dp.message(Command("user"))
    async def cmd_user(message: types.Message, command: CommandObject):
        if not command.args:
            await message.answer("❌ Укажите пользователя\nПример: /user @username")
            return
        
        username = command.args.strip()
        if username.startswith('@'):
            username = username[1:]
        
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT sender_id, sender_name, COUNT(*), 
                   SUM(CASE WHEN is_deleted=1 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN is_edited=1 THEN 1 ELSE 0 END)
            FROM messages 
            WHERE sender_name LIKE ? AND chat_id = ?
            GROUP BY sender_id
        ''', (f'%{username}%', message.chat.id))
        row = cur.fetchone()
        conn.close()
        
        if not row:
            await message.answer(f"❌ Пользователь @{username} не найден в сохранённых сообщениях")
            return
        
        await message.answer(
            f"👤 <b>Информация о пользователе</b>\n\n"
            f"Имя: {row[1]}\n"
            f"ID: {row[0] or 'Неизвестно'}\n"
            f"💬 Сообщений: {row[2]}\n"
            f"🗑️ Удалений: {row[3]}\n"
            f"✏️ Изменений: {row[4]}",
            parse_mode="HTML"
        )
    
    @dp.message(Command("whois"))
    async def cmd_whois(message: types.Message, command: CommandObject):
        # Расширенная информация
        if not command.args:
            await message.answer("❌ Укажите пользователя\nПример: /whois @username")
            return
        
        username = command.args.strip()
        if username.startswith('@'):
            username = username[1:]
        
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT sender_id, sender_name, COUNT(*), 
                   SUM(CASE WHEN is_deleted=1 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN is_edited=1 THEN 1 ELSE 0 END),
                   MIN(date), MAX(date)
            FROM messages 
            WHERE sender_name LIKE ? AND chat_id = ?
            GROUP BY sender_id
        ''', (f'%{username}%', message.chat.id))
        row = cur.fetchone()
        conn.close()
        
        if not row:
            await message.answer(f"❌ Пользователь @{username} не найден")
            return
        
        await message.answer(
            f"🔍 <b>Расширенная информация</b>\n\n"
            f"👤 {row[1]}\n"
            f"🆔 {row[0] or 'Неизвестно'}\n"
            f"💬 Сообщений: {row[2]}\n"
            f"🗑️ Удалений: {row[3]}\n"
            f"✏️ Изменений: {row[4]}\n"
            f"📅 Первое сообщение: {format_date(row[5])}\n"
            f"📅 Последнее: {format_date(row[6])}",
            parse_mode="HTML"
        )
    
    @dp.message(Command("avatar"))
    async def cmd_avatar(message: types.Message, command: CommandObject):
        if not command.args:
            await message.answer("❌ Укажите пользователя\nПример: /avatar @username")
            return
        
        username = command.args.strip()
        if username.startswith('@'):
            username = username[1:]
        
        try:
            user = await bot.get_chat(f"@{username}")
            photos = await bot.get_user_profile_photos(user.id)
            if photos.photos:
                await bot.send_photo(message.chat.id, photos.photos[0][-1].file_id,
                                    caption=f"🖼️ Аватар @{username}")
            else:
                await message.answer(f"❌ У @{username} нет аватарки")
        except:
            await message.answer(f"❌ Не удалось найти пользователя @{username}")
    
    # ============ ЧЁРНЫЙ СПИСОК ============
    
    @dp.message(Command("blacklist"))
    async def cmd_blacklist(message: types.Message, command: CommandObject):
        args = command.args.split() if command.args else []
        
        if not args:
            # Показать список
            blacklist = get_blacklist()
            if not blacklist:
                await message.answer("📭 Чёрный список пуст")
                return
            text = "🚫 <b>Чёрный список</b>\n\n"
            for item in blacklist:
                text += f"🆔 {item[0]} — {item[1]}\n"
                text += f"⏱️ Добавлен: {format_date(item[2])}\n\n"
            await message.answer(text, parse_mode="HTML")
            return
        
        action = args[0].lower()
        if action == "add" and len(args) > 1:
            username = args[1].strip()
            if username.startswith('@'):
                username = username[1:]
            try:
                user = await bot.get_chat(f"@{username}")
                reason = " ".join(args[2:]) if len(args) > 2 else "Не указана"
                add_blacklist(user.id, reason)
                await message.answer(f"✅ @{username} добавлен в ЧС\nПричина: {reason}")
            except:
                await message.answer(f"❌ Не удалось найти пользователя @{username}")
        
        elif action == "remove" and len(args) > 1:
            username = args[1].strip()
            if username.startswith('@'):
                username = username[1:]
            try:
                user = await bot.get_chat(f"@{username}")
                remove_blacklist(user.id)
                await message.answer(f"✅ @{username} удалён из ЧС")
            except:
                await message.answer(f"❌ Не удалось найти пользователя @{username}")
        
        else:
            await message.answer("❌ Использование:\n"
                                "/blacklist list\n"
                                "/blacklist add @username [причина]\n"
                                "/blacklist remove @username")
    
    # ============ НАСТРОЙКИ ============
    
    @dp.message(Command("settings"))
    async def cmd_settings(message: types.Message):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔔 Уведомления", callback_data="settings_notify")],
            [InlineKeyboardButton(text="👁️ Режим отслеживания", callback_data="settings_mode")],
            [InlineKeyboardButton(text="💾 Автосохранение медиа", callback_data="settings_media")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="settings_stats")],
            [InlineKeyboardButton(text="🔄 Сбросить настройки", callback_data="settings_reset")],
        ])
        await message.answer("⚙️ <b>Настройки бота</b>\n\n"
                            "Выберите раздел для настройки:",
                            parse_mode="HTML", reply_markup=keyboard)
    
    @dp.callback_query(lambda c: c.data.startswith('settings_'))
    async def settings_callback(callback: types.CallbackQuery):
        action = callback.data.replace('settings_', '')
        
        if action == "notify":
            current = get_setting("notify_enabled") or "on"
            new_val = "off" if current == "on" else "on"
            set_setting("notify_enabled", new_val)
            await callback.answer(f"🔔 Уведомления: {'Включены' if new_val == 'on' else 'Выключены'}")
            await callback.message.edit_text(f"✅ Настройка обновлена: уведомления {new_val}")
        
        elif action == "mode":
            current = get_setting("track_mode") or "all"
            modes = {"all": "Все чаты", "chats": "Только избранные"}
            await callback.message.edit_text(
                f"👁️ Режим отслеживания: {modes.get(current, current)}\n\n"
                "Выберите режим:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📱 Все чаты", callback_data="mode_all")],
                    [InlineKeyboardButton(text="⭐ Избранные", callback_data="mode_chats")],
                ])
            )
        
        elif action == "media":
            current = get_setting("save_media") or "off"
            new_val = "on" if current == "off" else "off"
            set_setting("save_media", new_val)
            await callback.answer(f"💾 Автосохранение: {'Включено' if new_val == 'on' else 'Выключено'}")
            await callback.message.edit_text(f"✅ Настройка обновлена: автосохранение медиа {new_val}")
        
        elif action == "stats":
            stats = get_stats()
            total_deleted = sum(s[3] for s in stats)
            total_edited = sum(s[4] for s in stats)
            total_msgs = sum(s[5] for s in stats)
            await callback.message.edit_text(
                f"📊 <b>Общая статистика бота</b>\n\n"
                f"💬 Сохранено сообщений: {total_msgs}\n"
                f"🗑️ Отслежено удалений: {total_deleted}\n"
                f"✏️ Отслежено изменений: {total_edited}\n"
                f"👥 Пользователей: {len(stats)}\n"
                f"📅 Запущен: {format_date(int(datetime.now().timestamp()))}",
                parse_mode="HTML"
            )
        
        elif action == "reset":
            set_setting("notify_enabled", "on")
            set_setting("track_mode", "all")
            set_setting("save_media", "off")
            await callback.answer("🔄 Настройки сброшены")
            await callback.message.edit_text("✅ Все настройки сброшены до значений по умолчанию")
        
        await callback.answer()
    
    @dp.callback_query(lambda c: c.data.startswith('mode_'))
    async def mode_callback(callback: types.CallbackQuery):
        mode = callback.data.replace('mode_', '')
        set_setting("track_mode", mode)
        modes = {"all": "Все чаты", "chats": "Только избранные"}
        await callback.answer(f"👁️ Режим: {modes.get(mode, mode)}")
        await callback.message.edit_text(f"✅ Режим отслеживания: {modes.get(mode, mode)}")
    
    @dp.message(Command("mode"))
    async def cmd_mode(message: types.Message, command: CommandObject):
        if not command.args:
            current = get_setting("track_mode") or "all"
            await message.answer(f"👁️ Текущий режим: {current}\n"
                                f"Используйте: /mode [all|chats]")
            return
        mode = command.args.lower()
        if mode in ["all", "chats"]:
            set_setting("track_mode", mode)
            await message.answer(f"✅ Режим отслеживания: {mode}")
        else:
            await message.answer("❌ Доступные режимы: all, chats")
    
    @dp.message(Command("notify"))
    async def cmd_notify(message: types.Message, command: CommandObject):
        if not command.args:
            current = get_setting("notify_enabled") or "on"
            await message.answer(f"🔔 Уведомления: {current}\n"
                                f"Используйте: /notify [on|off]")
            return
        state = command.args.lower()
        if state in ["on", "off"]:
            set_setting("notify_enabled", state)
            await message.answer(f"✅ Уведомления: {state}")
        else:
            await message.answer("❌ Используйте: /notify on или /notify off")
    
    # ============ ЭКСПОРТ ============
    
    @dp.message(Command("export"))
    async def cmd_export(message: types.Message, command: CommandObject):
        await message.answer("⏳ Формирую экспорт...")
        
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT chat_name, sender_name, text, date, is_deleted, is_edited 
            FROM messages 
            WHERE chat_id = ?
            ORDER BY date DESC LIMIT 1000
        ''', (message.chat.id,))
        rows = cur.fetchall()
        conn.close()
        
        if not rows:
            await message.answer("📭 Нет данных для экспорта")
            return
        
        # Формируем JSON
        data = []
        for row in rows:
            data.append({
                "chat": row[0],
                "sender": row[1],
                "text": row[2],
                "date": format_date(row[3]),
                "deleted": bool(row[4]),
                "edited": bool(row[5])
            })
        
        # Отправляем файл
        import io
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        file = io.BytesIO(json_str.encode('utf-8'))
        file.name = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        await bot.send_document(message.chat.id, file, caption="📊 Экспорт данных")
        await message.answer("✅ Экспорт завершён")
    
    @dp.message(Command("export_date"))
    async def cmd_export_date(message: types.Message, command: CommandObject):
        # Аналогично export, но с фильтром по дате
        if not command.args:
            await message.answer("❌ Укажите дату: /export_date ДД.ММ.ГГГГ")
            return
        
        # ... (аналогично find с экспортом)
        await message.answer("⏳ Функция в разработке...")
    
    # ============ УПРАВЛЕНИЕ ============
    
    @dp.message(Command("status"))
    async def cmd_status(message: types.Message):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM messages')
        total = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM messages WHERE is_deleted=1')
        deleted = cur.fetchone()[0]
        conn.close()
        
        uptime = "~" + str(int(datetime.now().timestamp() - 0))[:8]  # заглушка
        
        await message.answer(
            f"📊 <b>Статус бота</b>\n\n"
            f"💬 Сохранено: {total} сообщений\n"
            f"🗑️ Удалено: {deleted}\n"
            f"⏱️ Активен: с запуска\n"
            f"🔄 Версия: 2.0",
            parse_mode="HTML"
        )
    
    @dp.message(Command("clean"))
    async def cmd_clean(message: types.Message):
        # Очистка временных данных
        temp_data.clear()
        await message.answer("🧹 Временные данные очищены")
    
    @dp.message(Command("report"))
    async def cmd_report(message: types.Message):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM messages WHERE chat_id = ?', (message.chat.id,))
        total = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM messages WHERE chat_id = ? AND is_deleted=1', (message.chat.id,))
        deleted = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM messages WHERE chat_id = ? AND is_edited=1', (message.chat.id,))
        edited = cur.fetchone()[0]
        cur.execute('SELECT COUNT(DISTINCT sender_id) FROM messages WHERE chat_id = ?', (message.chat.id,))
        users = cur.fetchone()[0]
        conn.close()
        
        await message.answer(
            f"📋 <b>Отчёт по чату</b>\n\n"
            f"💬 Всего сообщений: {total}\n"
            f"🗑️ Удалено: {deleted}\n"
            f"✏️ Изменено: {edited}\n"
            f"👥 Участников: {users}\n"
            f"📅 Дата отчёта: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            parse_mode="HTML"
        )
    
    # ============ ОБРАБОТКА СООБЩЕНИЙ (СОХРАНЕНИЕ) ============
    
    @dp.message(F.chat.type == "private")
    async def save_message_handler(message: types.Message):
        # Проверка ЧС
        if is_blacklisted(message.from_user.id):
            return
        
        # Сохраняем
        media_type = None
        media_file_id = None
        if message.photo:
            media_type = "photo"
            media_file_id = message.photo[-1].file_id
        elif message.video:
            media_type = "video"
            media_file_id = message.video.file_id
        elif message.document:
            media_type = "document"
            media_file_id = message.document.file_id
        elif message.audio:
            media_type = "audio"
            media_file_id = message.audio.file_id
        elif message.voice:
            media_type = "voice"
            media_file_id = message.voice.file_id
        
        save_message(
            message.message_id,
            message.chat.id,
            message.chat.full_name or "Unknown",
            message.from_user.id,
            message.from_user.full_name or message.from_user.username or "Unknown",
            message.text or "",
            int(message.date.timestamp()),
            media_type,
            media_file_id
        )
        
        # Обновляем статистику
        increment_stat(message.chat.id, message.from_user.id, "messages_count")
        
        # Проверка на упоминания
        if message.text:
            mentions = extract_mentions(message.text)
            if mentions:
                await message.answer(f"🔔 Вы упомянули: {', '.join(mentions)}")
    
    # ============ ОБРАБОТКА УДАЛЕНИЙ И ИЗМЕНЕНИЙ (BUSINESS API) ============
    
    @dp.business_messages()
    async def business_delete_handler(update: types.BusinessMessages):
        if get_setting("notify_enabled") == "off":
            return
        
        # Удалённые
        for msg in update.deleted_messages:
            old = get_message(msg.message_id, update.chat.id)
            if old:
                mark_deleted(msg.message_id, update.chat.id)
                increment_stat(update.chat.id, old[4], "deleted_count")
                
                if get_setting("notify_enabled") == "on":
                    await bot.send_message(
                        LOG_CHAT_ID,
                        f"🗑️ <b>Удалено сообщение</b>\n"
                        f"👤 {old[5]}\n"
                        f"📝 {truncate_text(old[6], 200)}\n"
                        f"⏱️ {format_date(old[7])}",
                        parse_mode="HTML"
                    )
            else:
                # Сообщение не найдено в БД (возможно, было до запуска бота)
                if get_setting("notify_enabled") == "on":
                    await bot.send_message(
                        LOG_CHAT_ID,
                        f"🗑️ <b>Удалено сообщение</b> (не найдено в БД)\n"
                        f"ID: {msg.message_id}",
                        parse_mode="HTML"
                    )
        
        # Изменённые
        for msg in update.edited_messages:
            old = get_message(msg.message_id, update.chat.id)
            if old:
                update_message_text(msg.message_id, update.chat.id, msg.text or "")
                increment_stat(update.chat.id, old[4], "edited_count")
                
                if get_setting("notify_enabled") == "on":
                    await bot.send_message(
                        LOG_CHAT_ID,
                        f"✏️ <b>Изменено сообщение</b>\n"
                        f"👤 {old[5]}\n"
                        f"📝 Было: {truncate_text(old[6], 100)}\n"
                        f"📝 Стало: {truncate_text(msg.text or '', 100)}\n"
                        f"⏱️ {format_date(old[7])}",
                        parse_mode="HTML"
                    )
            else:
                # Сохраняем как новое
                save_message(
                    msg.message_id,
                    update.chat.id,
                    update.chat.full_name or "Unknown",
                    msg.from_user.id,
                    msg.from_user.full_name or msg.from_user.username or "Unknown",
                    msg.text or "",
                    int(msg.date.timestamp())
                )
    
    # ============ ЗАЩИТА ОТ СПАМА ============
    
    @dp.message(F.text.startswith('/'))
    async def unknown_command(message: types.Message):
        await message.answer(f"❌ Неизвестная команда\nИспользуйте /help для списка команд")
