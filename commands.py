from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
import json
from datetime import datetime

from config import ADMIN_ID, VERSION, BOT_NAME, CMD_PREFIX
from db.database import (
    register_user, get_user, get_user_stats, get_user_settings,
    update_user_settings, get_all_users_count, search_messages,
    export_user_messages, clean_old_messages
)

router = Router()

def main_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data="stats")
    builder.button(text="⚙️ Настройки", callback_data="settings")
    builder.button(text="📝 Все команды", callback_data="help")
    builder.button(text="👤 Профиль", callback_data="profile")
    builder.button(text="📦 Экспорт", callback_data="export")
    builder.button(text="ℹ️ О боте", callback_data="about")
    builder.adjust(2)
    return builder.as_markup()

def settings_kb(settings: dict):
    builder = InlineKeyboardBuilder()
    own = "✅" if settings.get("save_own", True) else "❌"
    media = "✅" if settings.get("save_media", True) else "❌"
    notify = "✅" if settings.get("notify_delete", True) else "❌"
    edit_n = "✅" if settings.get("notify_edit", True) else "❌"
    builder.button(text=f"{own} Свои сообщения", callback_data="tog_own")
    builder.button(text=f"{media} Медиа", callback_data="tog_media")
    builder.button(text=f"{notify} Уведомления об удалении", callback_data="tog_del")
    builder.button(text=f"{edit_n} Уведомления о правках", callback_data="tog_edit")
    builder.button(text="◀️ Назад", callback_data="back_main")
    builder.adjust(1)
    return builder.as_markup()

@router.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    await register_user(user.id, user.username or "", user.full_name or "")
    
    text = (
        f"👋 <b>Привет, {user.first_name}!</b>\n\n"
        f"Я — <b>{BOT_NAME}</b> <code>v{VERSION}</code>\n"
        f"Сделан с помощью <b>Grok</b> от xAI 🚀\n\n"
        f"<b>Что я умею:</b>\n"
        f"• Ловлю удалённые и отредактированные сообщения\n"
        f"• Сохраняю view-once / protected медиа\n"
        f"• Куча команд: .spam .love .type .ttt .sw .leet и ещё 40+\n"
        f"• Статистика, поиск, экспорт, настройки\n\n"
        f"<b>Подключение:</b>\n"
        f"Настройки Telegram → Автоматизация чатов / Telegram для бизнеса → добавь этого бота\n\n"
        f"Напиши <code>.help</code> чтобы увидеть все команды.\n"
        f"Или жми кнопки 👇"
    )
    await message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")

@router.message(Command("stats"))
@router.message(F.text.lower().in_({f"{CMD_PREFIX}stats", f"{CMD_PREFIX}стата", f"{CMD_PREFIX}stat"}))
async def cmd_stats(message: Message):
    stats = await get_user_stats(message.from_user.id)
    user = await get_user(message.from_user.id)
    if not stats:
        await message.answer("Пока нет данных. Подключи бота через Автоматизацию.")
        return
    text = (
        f"📊 <b>Твоя статистика</b>\n\n"
        f"💾 Сохранено: <b>{stats['total_saved']}</b>\n"
        f"🗑 Удалений поймано: <b>{stats['total_deleted']}</b>\n"
        f"✏️ Правок поймано: <b>{stats['total_edited']}</b>\n"
        f"🖼 Медиа: <b>{stats['media_saved']}</b>\n"
        f"📅 Активность: {stats['last_active'][:16] if stats['last_active'] else '—'}"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(F.text.lower().in_({f"{CMD_PREFIX}settings", f"{CMD_PREFIX}настройки", f"{CMD_PREFIX}set"}))
async def cmd_settings(message: Message):
    settings = await get_user_settings(message.from_user.id)
    await message.answer("⚙️ <b>Настройки</b>", reply_markup=settings_kb(settings), parse_mode="HTML")

@router.message(F.text.lower().in_({f"{CMD_PREFIX}profile", f"{CMD_PREFIX}я", f"{CMD_PREFIX}me"}))
async def cmd_profile(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала /start")
        return
    text = (
        f"👤 <b>Профиль</b>\n\n"
        f"Имя: {user['full_name']}\n"
        f"Юзернейм: @{user['username'] or 'нет'}\n"
        f"ID: <code>{user['user_id']}</code>\n"
        f"Подключён: {'✅' if user['business_connection_id'] else '❌'}\n"
        f"Регистрация: {user['joined_at'][:16]}\n"
        f"Сохранено: {user['messages_saved']} | Удалений: {user['deletes_caught']} | Правок: {user['edits_caught']}"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(F.text.lower() == f"{CMD_PREFIX}id")
async def cmd_id(message: Message):
    await message.answer(f"ID: <code>{message.from_user.id}</code>\nЧат: <code>{message.chat.id}</code>", parse_mode="HTML")

@router.message(F.text.lower() == f"{CMD_PREFIX}ping")
async def cmd_ping(message: Message):
    await message.answer("🏓 Pong!")

@router.message(F.text.lower() == f"{CMD_PREFIX}version")
async def cmd_version(message: Message):
    await message.answer(f"<b>{BOT_NAME}</b>\n<code>{VERSION}</code>\nby Grok", parse_mode="HTML")

@router.message(F.text.lower() == f"{CMD_PREFIX}about")
async def cmd_about(message: Message):
    await message.answer(
        f"<b>{BOT_NAME}</b> v{VERSION}\n\n"
        f"Бот-компаньон через Telegram Business / Автоматизация.\n"
        f"Ловит удаления, правки, исчезающие медиа + куча весёлых команд.\n\n"
        f"Сделано с <b>Grok</b> (xAI).",
        parse_mode="HTML"
    )

@router.message(F.text.lower() == f"{CMD_PREFIX}donate")
async def cmd_donate(message: Message):
    await message.answer("💜 Спасибо, что пользуешься ботом!")

@router.message(F.text.lower().startswith(f"{CMD_PREFIX}search"))
async def cmd_search(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: <code>.search текст</code>", parse_mode="HTML")
        return
    results = await search_messages(message.from_user.id, parts[1].strip(), limit=10)
    if not results:
        await message.answer("Ничего не найдено.")
        return
    lines = [f"🔍 Найдено {len(results)}:\n"]
    for r in results:
        preview = (r["text"] or r["caption"] or r["content_type"])[:80]
        lines.append(f"• [{r['created_at'][:16]}] {preview}")
    await message.answer("\n".join(lines))

@router.message(F.text.lower() == f"{CMD_PREFIX}export")
async def cmd_export(message: Message):
    data = await export_user_messages(message.from_user.id, limit=200)
    if not data:
        await message.answer("Нечего экспортировать.")
        return
    filename = f"export_{message.from_user.id}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    path = f"media/{filename}"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    from aiogram.types import FSInputFile
    await message.answer_document(FSInputFile(path), caption="📦 Экспорт")

@router.message(F.text.lower() == f"{CMD_PREFIX}clear")
async def cmd_clear(message: Message):
    await message.answer("Для очистки напиши <code>.clear confirm</code>", parse_mode="HTML")

@router.message(F.text.lower() == f"{CMD_PREFIX}clear confirm")
async def cmd_clear_confirm(message: Message):
    await clean_old_messages()
    await message.answer("✅ Старые записи очищены.")

@router.message(F.text.lower() == f"{CMD_PREFIX}last")
async def cmd_last(message: Message):
    data = await export_user_messages(message.from_user.id, limit=5)
    if not data:
        await message.answer("Пока пусто.")
        return
    lines = ["🕒 Последние:\n"]
    for r in data:
        preview = (r["text"] or r["caption"] or r["content_type"])[:60]
        lines.append(f"• {r['created_at'][:16]} | {r['from_name']}: {preview}")
    await message.answer("\n".join(lines))

@router.message(F.text.lower() == f"{CMD_PREFIX}media")
async def cmd_media(message: Message):
    stats = await get_user_stats(message.from_user.id)
    await message.answer(f"🖼 Медиа: <b>{stats['media_saved'] if stats else 0}</b>", parse_mode="HTML")

# Админ
@router.message(F.text.lower() == f"{CMD_PREFIX}admin")
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    count = await get_all_users_count()
    await message.answer(f"🛠 Админ\nПользователей: <b>{count}</b>\n.users .clean .broadcast", parse_mode="HTML")

@router.message(F.text.lower() == f"{CMD_PREFIX}users")
async def cmd_users(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    count = await get_all_users_count()
    await message.answer(f"👥 Пользователей: <b>{count}</b>", parse_mode="HTML")

@router.message(F.text.lower() == f"{CMD_PREFIX}clean")
async def cmd_admin_clean(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await clean_old_messages()
    await message.answer("✅ Очистка выполнена.")

@router.message(F.text.lower().startswith(f"{CMD_PREFIX}broadcast"))
async def cmd_broadcast(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(".broadcast текст")
        return
    await message.answer(f"Демо-рассылка: {parts[1]}")

# Callbacks
@router.callback_query(F.data == "stats")
async def cb_stats(callback: CallbackQuery):
    await cmd_stats(callback.message)
    await callback.answer()

@router.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery):
    # Перенаправляем на полный help из fun
    await callback.message.answer("Напиши <code>.help</code> чтобы увидеть полный список команд", parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "profile")
async def cb_profile(callback: CallbackQuery):
    await cmd_profile(callback.message)
    await callback.answer()

@router.callback_query(F.data == "settings")
async def cb_settings(callback: CallbackQuery):
    settings = await get_user_settings(callback.from_user.id)
    await callback.message.edit_text("⚙️ <b>Настройки</b>", reply_markup=settings_kb(settings), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "back_main")
async def cb_back(callback: CallbackQuery):
    await callback.message.edit_text("Главное меню:", reply_markup=main_menu_kb())
    await callback.answer()

@router.callback_query(F.data.startswith("tog_"))
async def cb_toggle(callback: CallbackQuery):
    settings = await get_user_settings(callback.from_user.id)
    key_map = {"tog_own": "save_own", "tog_media": "save_media", "tog_del": "notify_delete", "tog_edit": "notify_edit"}
    key = key_map.get(callback.data)
    if key:
        settings[key] = not settings.get(key, True)
        await update_user_settings(callback.from_user.id, settings)
    await callback.message.edit_reply_markup(reply_markup=settings_kb(settings))
    await callback.answer("Обновлено")

@router.callback_query(F.data == "export")
async def cb_export(callback: CallbackQuery):
    await cmd_export(callback.message)
    await callback.answer()

@router.callback_query(F.data == "about")
async def cb_about(callback: CallbackQuery):
    await cmd_about(callback.message)
    await callback.answer()
