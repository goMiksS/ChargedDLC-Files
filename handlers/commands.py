import json
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import ADMIN_ID, VERSION, BOT_NAME, TRIAL_DAYS, VIP_PLANS
from db.database import (
    register_user, get_user, get_user_stats, get_user_settings,
    update_user_settings, get_all_users_count, search_messages,
    export_user_messages, clean_old_messages,
    get_subscription, grant_days, start_trial
)

router = Router()


def is_private(message: Message) -> bool:
    """Проверка: диалог напрямую с ботом (не business)."""
    return message.chat.type == "private" and not getattr(message, "business_connection_id", None)


async def send_or_replace(message: Message, text: str, reply_markup=None):
    """
    Удаляет входящее командное сообщение (например, .admin в бизнесе) 
    и отправляет чистое новое сообщение от бота.
    """
    try:
        await message.delete()
    except Exception:
        pass
    return await message.answer(text, reply_markup=reply_markup, parse_mode="HTML")


# ===== КЛАВИАТУРЫ С ПРИВЯЗКОЙ К USER_ID =====

def start_kb(user_id: int):
    b = InlineKeyboardBuilder()
    b.button(text="🎁 Активировать пробный период (3 дня)", callback_data=f"trial:{user_id}")
    return b.as_markup()


def menu_kb(owner_id: int, has_sub: bool, trial_used: bool):
    b = InlineKeyboardBuilder()
    if not has_sub and not trial_used:
        b.button(text="🎁 Активировать пробный период (3 дня)", callback_data=f"trial:{owner_id}")
        b.adjust(1)
        return b.as_markup()

    b.button(text="📊 Статистика", callback_data=f"stats:{owner_id}")
    b.button(text="⚙️ Настройки", callback_data=f"settings:{owner_id}")
    b.button(text="📜 Команды", callback_data=f"help:{owner_id}")
    b.button(text="👤 Профиль", callback_data=f"profile:{owner_id}")
    b.button(text="💎 VIP / Магазин", callback_data=f"shop:{owner_id}")
    if owner_id == ADMIN_ID:
        b.button(text="🛠 Админ", callback_data=f"admin_panel:{owner_id}")
    b.adjust(2)
    return b.as_markup()


def settings_kb(owner_id: int, settings: dict):
    b = InlineKeyboardBuilder()
    own = "✅" if settings.get("save_own", True) else "❌"
    media = "✅" if settings.get("save_media", True) else "❌"
    notify = "✅" if settings.get("notify_delete", True) else "❌"
    edit_n = "✅" if settings.get("notify_edit", True) else "❌"
    
    b.button(text=f"{own} Свои сообщения", callback_data=f"tog_own:{owner_id}")
    b.button(text=f"{media} Сохранять Медиа", callback_data=f"tog_media:{owner_id}")
    b.button(text=f"{notify} Уведомлять об удалениях", callback_data=f"tog_del:{owner_id}")
    b.button(text=f"{edit_n} Уведомлять о правках", callback_data=f"tog_edit:{owner_id}")
    b.button(text="◀️ Назад в меню", callback_data=f"back_main:{owner_id}")
    b.adjust(1)
    return b.as_markup()


def shop_kb(owner_id: int):
    b = InlineKeyboardBuilder()
    for key, plan in VIP_PLANS.items():
        b.button(text=f"💎 {plan['title']} — {plan['price']} ⭐", callback_data=f"buy_{key}:{owner_id}")
    b.button(text="◀️ Назад в меню", callback_data=f"back_main:{owner_id}")
    b.adjust(1)
    return b.as_markup()


def admin_kb(owner_id: int):
    b = InlineKeyboardBuilder()
    b.button(text="👥 Список пользователей", callback_data=f"admin_users:{owner_id}")
    b.button(text="📊 Статистика бота", callback_data=f"admin_stats:{owner_id}")
    b.button(text="🧹 Очистить старые логи", callback_data=f"admin_clean:{owner_id}")
    b.button(text="◀️ Назад в меню", callback_data=f"back_main:{owner_id}")
    b.adjust(1)
    return b.as_markup()


# ===== ПРОВЕРКА ЧУЖИХ КНОПОК =====

async def check_ownership(c: CallbackQuery) -> bool:
    """Проверяет, совпадает ли ID нажавшего с владельцем меню в callback_data."""
    if ":" in c.data:
        owner_id = int(c.data.split(":")[-1])
        if c.from_user.id != owner_id:
            await c.answer("⛔ Это не твое меню! Вызови свое командой .help", show_alert=True)
            return False
    return True


HELP_TEXT = f"""✨ <b>—={BOT_NAME} v{VERSION}=-</b> ✨
───────────────────────────
🛠 <b>ОСНОВНЫЕ КОМАНДЫ</b>
├ <code>.help</code> — Вызов этого меню
├ <code>.stats</code> — Ваша статистика
├ <code>.profile</code> — Данные профиля
├ <code>.settings</code> — Настройки сохранения
└ <code>.shop</code> / <code>.vip</code> — Купить VIP-доступ

📂 <b>УПРАВЛЕНИЕ СООБЩЕНИЯМИ</b>
├ <code>.search [текст]</code> — Поиск по сохраненным
├ <code>.last</code> — Показать последние логи
├ <code>.media</code> — Статистика по сохранённым медиа
└ <code>.export</code> — Скачать логи файлом .json

🔤 <b>ТЕКСТОВЫЕ УТИЛИТЫ</b>
├ <code>.sw [текст]</code> — Исправить раскладку
├ <code>.reverse [текст]</code> — Перевернуть текст
├ <code>.upper [текст]</code> — СДЕЛАТЬ ВЕРХНИЙ РЕГИСТР
└ <code>.lower [текст]</code> — сделать нижний регистр
───────────────────────────
💡 <i>Все команды можно писать прямо в чатах с друзьями!</i>"""


# ===== КОМАНДЫ =====

@router.message(CommandStart())
async def cmd_start(message: Message):
    if not is_private(message):
        return
    user = message.from_user
    await register_user(user.id, user.username or "", user.full_name or "")
    sub = await get_subscription(user.id)

    if not sub["active"] and not sub["trial_used"]:
        text = (
            f"⚡ <b>Приветствуем в {BOT_NAME}!</b> <code>v{VERSION}</code>\n"
            f"───────────────────────────\n"
            f"Модификация <b>{BOT_NAME}</b> позволяет отслеживать и сохранять "
            f"все <b>удалённые сообщения и медиа-файлы</b>!\n\n"
            f"👇 Жми кнопку ниже, чтобы попробовать <b>3 дня бесплатно</b>:"
        )
        await send_or_replace(message, text, reply_markup=start_kb(user.id))
        return

    text = (
        f"⚡ <b>Панель управления {BOT_NAME}</b> <code>v{VERSION}</code>\n"
        f"───────────────────────────\n"
        f"👤 Пользователь: <b>{user.full_name}</b>\n"
        f"📌 Быстрые команды: <code>.help</code> · <code>.stats</code> · <code>.shop</code>"
    )
    await send_or_replace(message, text, reply_markup=menu_kb(user.id, sub["active"], sub["trial_used"]))


@router.message(F.text.lower().in_({".help", ".помощь"}))
@router.business_message(F.text.lower().in_({".help", ".помощь"}))
async def cmd_help(message: Message):
    sub = await get_subscription(message.from_user.id)
    kb = menu_kb(message.from_user.id, sub["active"], sub["trial_used"])
    await send_or_replace(message, HELP_TEXT, reply_markup=kb)


@router.message(F.text.lower() == ".admin")
@router.business_message(F.text.lower() == ".admin")
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    count = await get_all_users_count()
    text = (
        f"🛠 <b>Панель Администратора</b>\n\n"
        f"Пользователей: <b>{count}</b>\n"
        f"Выдача VIP: <code>.give ID дней</code>"
    )
    await send_or_replace(message, text, reply_markup=admin_kb(message.from_user.id))


@router.message(F.text.lower().in_({".shop", ".vip", ".магазин"}))
@router.business_message(F.text.lower().in_({".shop", ".vip", ".магазин"}))
async def cmd_shop(message: Message):
    uid = message.from_user.id
    sub = await get_subscription(uid)
    status = f"✅ VIP активен до: <b>{sub['until'][:10]}</b>\n\n" if sub["active"] else "❌ VIP-подписка не активна\n\n"
    await send_or_replace(message, f"💎 <b>Магазин VIP-подписок</b>\n\n{status}Выберите подписку:", reply_markup=shop_kb(uid))


@router.message(F.text.lower().in_({".stats", ".стата"}))
@router.business_message(F.text.lower().in_({".stats", ".стата"}))
async def cmd_stats(message: Message):
    uid = message.from_user.id
    stats = await get_user_stats(uid)
    sub = await get_subscription(uid)
    if not stats:
        await send_or_replace(message, "Пока нет данных для статистики.")
        return
    vip = f"\n💎 VIP активен до {sub['until'][:10]}" if sub["active"] else ""
    text = (
        f"📊 <b>Ваша статистика:</b>\n\n"
        f"📥 Сохранено сообщений: <b>{stats['total_saved']}</b>\n"
        f"🗑 Перехвачено удалений: <b>{stats['total_deleted']}</b>\n"
        f"✏️ Перехвачено правок: <b>{stats['total_edited']}</b>{vip}"
    )
    await send_or_replace(message, text, reply_markup=menu_kb(uid, sub["active"], sub["trial_used"]))


@router.message(F.text.lower().in_({".settings", ".настройки"}))
@router.business_message(F.text.lower().in_({".settings", ".настройки"}))
async def cmd_settings(message: Message):
    uid = message.from_user.id
    s = await get_user_settings(uid)
    await send_or_replace(message, "⚙️ <b>Настройки перехвата:</b>", reply_markup=settings_kb(uid, s))


# ===== CALLBACK HANDLERS С ПРОВЕРКОЙ =====

@router.callback_query(F.data.startswith("trial:"))
async def cb_trial(c: CallbackQuery):
    if not await check_ownership(c): return
    uid = c.from_user.id
    ok = await start_trial(uid, TRIAL_DAYS)
    if ok:
        sub = await get_subscription(uid)
        instruction_text = (
            f"🎉 <b>Пробный период на {TRIAL_DAYS} дня успешно активирован!</b>\n"
            f"🗓 Истекает: <code>{sub['until'][:16]}</code>\n\n"
            f"📱 <b>Инструкция по установке модификации:</b>\n"
            f"1️⃣ Откройте <b>Настройки Telegram</b>.\n"
            f"2️⃣ Перейдите в <b>Telegram Business (Автоматизация чатов)</b>.\n"
            f"3️⃣ Выберите <b>Чаты / Чат-боты</b>.\n"
            f"4️⃣ Нажмите <b>Добавить бота</b> и укажите юзернейм нашего бота.\n\n"
            f"🚀 <i>Готово! Теперь бот автоматически сохраняет удаленные сообщения.</i>"
        )
        await c.message.edit_text(instruction_text, reply_markup=menu_kb(uid, True, True), parse_mode="HTML")
    else:
        await c.answer("Пробный период уже был использован!", show_alert=True)
    await c.answer()


@router.callback_query(F.data.startswith("admin_panel:"))
async def cb_admin(c: CallbackQuery):
    if not await check_ownership(c): return
    if c.from_user.id != ADMIN_ID:
        await c.answer("Доступ запрещен", show_alert=True)
        return
    count = await get_all_users_count()
    await c.message.edit_text(f"🛠 <b>Админ панель</b>\nПользователей: <b>{count}</b>", reply_markup=admin_kb(c.from_user.id), parse_mode="HTML")
    await c.answer()


@router.callback_query(F.data.startswith("admin_users:"))
async def cb_admin_users(c: CallbackQuery):
    if not await check_ownership(c): return
    if c.from_user.id != ADMIN_ID: return
    import aiosqlite
    from config import DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT user_id, username, full_name, is_vip FROM users ORDER BY joined_at DESC LIMIT 30") as cur:
            rows = await cur.fetchall()
    lines = ["👥 <b>Пользователи</b> (до 30):\n"]
    for r in rows:
        vip = "💎 " if r["is_vip"] else ""
        lines.append(f"{vip}<code>{r['user_id']}</code> {r['full_name'] or ''} @{r['username'] or '—'}")
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Назад", callback_data=f"admin_panel:{c.from_user.id}")
    await c.message.edit_text("\n".join(lines)[:3500], reply_markup=b.as_markup(), parse_mode="HTML")
    await c.answer()


@router.callback_query(F.data.startswith("back_main:"))
async def cb_back(c: CallbackQuery):
    if not await check_ownership(c): return
    uid = c.from_user.id
    sub = await get_subscription(uid)
    await c.message.edit_text("⚡ <b>Главное меню:</b>", reply_markup=menu_kb(uid, sub["active"], sub["trial_used"]), parse_mode="HTML")
    await c.answer()


@router.callback_query(F.data.startswith("tog_"))
async def cb_tog(c: CallbackQuery):
    if not await check_ownership(c): return
    uid = c.from_user.id
    s = await get_user_settings(uid)
    key_raw = c.data.split(":")[0]
    m = {"tog_own": "save_own", "tog_media": "save_media", "tog_del": "notify_delete", "tog_edit": "notify_edit"}
    k = m.get(key_raw)
    if k:
        s[k] = not s.get(k, True)
        await update_user_settings(uid, s)
    await c.message.edit_reply_markup(reply_markup=settings_kb(uid, s))
    await c.answer("Настройки обновлены")
