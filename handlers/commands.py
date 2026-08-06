import json
import random
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
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

async def savemod_edit_or_reply(message: Message, text: str, reply_markup=None):
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        await message.answer(text, reply_markup=reply_markup, parse_mode="HTML")

# ===== КЛАВИАТУРЫ =====

def start_trial_kb(user_id: int):
    b = InlineKeyboardBuilder()
    b.button(text="🎁 Активировать пробный период (3 дня)", callback_data=f"trial:{user_id}")
    return b.as_markup()

def menu_kb(user_id: int):
    b = InlineKeyboardBuilder()
    b.button(text="📊 Статистика", callback_data=f"stats:{user_id}")
    b.button(text="⚙️ Настройки", callback_data=f"settings:{user_id}")
    b.button(text="📜 Команды", callback_data=f"help:{user_id}")
    b.button(text="👤 Профиль", callback_data=f"profile:{user_id}")
    b.button(text="💎 VIP / Магазин", callback_data=f"shop:{user_id}")
    
    if int(user_id) == int(ADMIN_ID):
        b.button(text="🛠 Админ", callback_data=f"admin_panel:{user_id}")
        
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

# ===== ЛОГИКА СИСТЕМНЫХ И ТЕКСТОВЫХ КОМАНД =====

@router.message(CommandStart())
async def cmd_start(message: Message):
    if getattr(message, "business_connection_id", None):
        return
    user = message.from_user
    await register_user(user.id, user.username or "", user.full_name or "")
    sub = await get_subscription(user.id)

    if not sub["active"] and not sub["trial_used"]:
        text = f"⚡ <b>Приветствуем в {BOT_NAME}!</b>\nЖми кнопку ниже, чтобы активировать тест:"
        await message.answer(text, reply_markup=start_trial_kb(user.id), parse_mode="HTML")
        return

    text = f"⚡ <b>Панель {BOT_NAME} v{VERSION}</b>\nПользователь: <b>{user.full_name}</b>"
    await message.answer(text, reply_markup=menu_kb(user.id), parse_mode="HTML")

@router.message(F.text.lower().in_({".help", ".помощь"}))
@router.business_message(F.text.lower().in_({".help", ".помощь"}))
async def cmd_help(message: Message):
    text = (
        f"✨ <b>—={BOT_NAME} v{VERSION}=-</b> ✨\n"
        f"───────────────────────────\n"
        f"🛠 <b>ОСНОВНЫЕ:</b> <code>.stats</code> · <code>.profile</code> · <code>.settings</code> · <code>.shop</code> · <code>.ping</code> · <code>.id</code>\n\n"
        f"📂 <b>ЛОГИ:</b> <code>.search [текст]</code> · <code>.last</code> · <code>.export</code>\n\n"
        f"🔤 <b>ТЕКСТ:</b> <code>.sw</code> · <code>.reverse</code> · <code>.upper</code> · <code>.lower</code> · <code>.bold</code> · <code>.italic</code> · <code>.code</code> · <code>.spoiler</code> · <code>.strike</code> · <code>.len</code>\n\n"
        f"🎮 <b>ИГРЫ:</b> <code>.bal</code> · <code>.work</code> · <code>.casino [ставка]</code> · <code>.slot</code> · <code>.dice</code> · <code>.coin</code> · <code>.ball</code> · <code>.choose</code> · <code>.roulette</code> · <code>.pay [id] [сумма]</code> · <code>.rand [от] [до]</code> · <code>.percent [текст]</code>\n\n"
        f"🛠 <b>АДМИН:</b> <code>.admin</code> · <code>.give [ID] [дней]</code>"
    )
    await savemod_edit_or_reply(message, text)

# --- Управление и Профиль ---
@router.message(F.text.lower().in_({".profile", ".профиль"}))
@router.business_message(F.text.lower().in_({".profile", ".профиль"}))
async def cmd_profile(message: Message):
    uid = message.from_user.id
    sub = await get_subscription(uid)
    vip_status = f"✅ VIP до {sub['until'][:10]}" if sub["active"] else "❌ Нет VIP"
    text = (
        f"👤 <b>Профиль пользователя:</b>\n"
        f"🆔 ID: <code>{uid}</code>\n"
        f"👤 Имя: <b>{message.from_user.full_name}</b>\n"
        f"💎 Статус: <b>{vip_status}</b>"
    )
    await savemod_edit_or_reply(message, text, reply_markup=menu_kb(uid))

@router.message(F.text.lower().in_({".stats", ".стата"}))
@router.business_message(F.text.lower().in_({".stats", ".стата"}))
async def cmd_stats(message: Message):
    uid = message.from_user.id
    stats = await get_user_stats(uid)
    sub = await get_subscription(uid)
    if not stats:
        return await savemod_edit_or_reply(message, "Пока нет сохранённых данных.")
    text = (
        f"📊 <b>Ваша статистика:</b>\n\n"
        f"📥 Сохранено сообщений: <b>{stats['total_saved']}</b>\n"
        f"🗑 Перехвачено удалений: <b>{stats['total_deleted']}</b>\n"
        f"✏️ Перехвачено правок: <b>{stats['total_edited']}</b>"
    )
    await savemod_edit_or_reply(message, text, reply_markup=menu_kb(uid))

@router.message(F.text.lower().in_({".settings", ".настройки"}))
@router.business_message(F.text.lower().in_({".settings", ".настройки"}))
async def cmd_settings(message: Message):
    uid = message.from_user.id
    s = await get_user_settings(uid)
    await savemod_edit_or_reply(message, "⚙️ <b>Настройки перехватчика:</b>", reply_markup=settings_kb(uid, s))

@router.message(F.text.lower().in_({".shop", ".vip", ".магазин"}))
@router.business_message(F.text.lower().in_({".shop", ".vip", ".магазин"}))
async def cmd_shop(message: Message):
    uid = message.from_user.id
    await savemod_edit_or_reply(message, "💎 <b>Магазин подписок:</b>", reply_markup=shop_kb(uid))

# --- Системные проверки ---
@router.message(F.text.lower() == ".ping")
@router.business_message(F.text.lower() == ".ping")
async def cmd_ping(message: Message):
    await savemod_edit_or_reply(message, "🏓 <b>ПОНГ!</b> Бот работает в штатном режиме.")

@router.message(F.text.lower() == ".id")
@router.business_message(F.text.lower() == ".id")
async def cmd_id(message: Message):
    await savemod_edit_or_reply(message, f"🆔 Ваш Telegram ID: <code>{message.from_user.id}</code>")

# --- Поиск по логам (.search) ---
@router.message(F.text.lower().startswith((".search ", ".поиск ")))
@router.business_message(F.text.lower().startswith((".search ", ".поиск ")))
async def cmd_search(message: Message):
    uid = message.from_user.id
    query = message.text.split(maxsplit=1)[1]
    results = await search_messages(uid, query)
    if not results:
        return await savemod_edit_or_reply(message, f"🔍 По запросу «{query}» ничего не найдено.")
    
    text = f"🔍 <b>Результаты поиска «{query}»:</b>\n\n"
    for r in results[:5]:
        text += f"💬 <code>{r['text']}</code>\n\n"
    await savemod_edit_or_reply(message, text)

# --- Экспорт логов (.export) ---
@router.message(F.text.lower() == ".export")
@router.business_message(F.text.lower() == ".export")
async def cmd_export(message: Message):
    uid = message.from_user.id
    data = await export_user_messages(uid)
    if not data:
        return await savemod_edit_or_reply(message, "❌ Нет сохраненных сообщений для экспорта.")
    
    json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
    from aiogram.types import BufferedInputFile
    file = BufferedInputFile(json_bytes, filename=f"logs_{uid}.json")
    await message.answer_document(file, caption="📂 Ваши экспортированные логи сообщений")

# --- Текстовые Утилиты ---
@router.message(F.text.lower().startswith(".sw "))
@router.business_message(F.text.lower().startswith(".sw "))
async def cmd_sw(message: Message):
    raw = message.text[4:]
    eng = "qwertyuiop[]asdfghjkl;'zxcvbnm,./QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>?"
    rus = "йцукенгшщзхъфывапролджэячсмитьбю.ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,"
    tr = str.maketrans(eng + rus, rus + eng)
    await savemod_edit_or_reply(message, raw.translate(tr))

@router.message(F.text.lower().startswith(".reverse "))
@router.business_message(F.text.lower().startswith(".reverse "))
async def cmd_reverse(message: Message):
    raw = message.text.split(maxsplit=1)[1]
    await savemod_edit_or_reply(message, raw[::-1])

@router.message(F.text.lower().startswith(".upper "))
@router.business_message(F.text.lower().startswith(".upper "))
async def cmd_upper(message: Message):
    raw = message.text.split(maxsplit=1)[1]
    await savemod_edit_or_reply(message, raw.upper())

@router.message(F.text.lower().startswith(".lower "))
@router.business_message(F.text.lower().startswith(".lower "))
async def cmd_lower(message: Message):
    raw = message.text.split(maxsplit=1)[1]
    await savemod_edit_or_reply(message, raw.lower())

@router.message(F.text.lower().startswith(".bold "))
@router.business_message(F.text.lower().startswith(".bold "))
async def cmd_bold(message: Message):
    raw = message.text.split(maxsplit=1)[1]
    await savemod_edit_or_reply(message, f"<b>{raw}</b>")

@router.message(F.text.lower().startswith(".italic "))
@router.business_message(F.text.lower().startswith(".italic "))
async def cmd_italic(message: Message):
    raw = message.text.split(maxsplit=1)[1]
    await savemod_edit_or_reply(message, f"<i>{raw}</i>")

@router.message(F.text.lower().startswith(".code "))
@router.business_message(F.text.lower().startswith(".code "))
async def cmd_code(message: Message):
    raw = message.text.split(maxsplit=1)[1]
    await savemod_edit_or_reply(message, f"<code>{raw}</code>")

@router.message(F.text.lower().startswith(".spoiler "))
@router.business_message(F.text.lower().startswith(".spoiler "))
async def cmd_spoiler(message: Message):
    raw = message.text.split(maxsplit=1)[1]
    await savemod_edit_or_reply(message, f"<tg-spoiler>{raw}</tg-spoiler>")

@router.message(F.text.lower().startswith(".strike "))
@router.business_message(F.text.lower().startswith(".strike "))
async def cmd_strike(message: Message):
    raw = message.text.split(maxsplit=1)[1]
    await savemod_edit_or_reply(message, f"<s>{raw}</s>")

@router.message(F.text.lower().startswith(".len "))
@router.business_message(F.text.lower().startswith(".len "))
async def cmd_len(message: Message):
    raw = message.text.split(maxsplit=1)[1]
    await savemod_edit_or_reply(message, f"📏 Длина текста: <b>{len(raw)}</b> симв.")

@router.message(F.text.lower().startswith((".rand ", ".рандом ")))
@router.business_message(F.text.lower().startswith((".rand ", ".рандом ")))
async def cmd_rand(message: Message):
    try:
        parts = message.text.split()
        val = random.randint(int(parts[1]), int(parts[2]))
        await savemod_edit_or_reply(message, f"🎲 Случайное число: <b>{val}</b>")
    except Exception:
        await savemod_edit_or_reply(message, "❌ <b>Использование:</b> <code>.rand 1 100</code>")

@router.message(F.text.lower().startswith(".percent "))
@router.business_message(F.text.lower().startswith(".percent "))
async def cmd_percent(message: Message):
    raw = message.text.split(maxsplit=1)[1]
    val = random.randint(0, 100)
    await savemod_edit_or_reply(message, f"📊 Вероятность «{raw}»: <b>{val}%</b>")

# --- Админка ---
@router.message(F.text.lower() == ".admin")
@router.business_message(F.text.lower() == ".admin")
async def cmd_admin(message: Message):
    if int(message.from_user.id) != int(ADMIN_ID): return
    count = await get_all_users_count()
    await savemod_edit_or_reply(message, f"🛠 <b>Админ Панель</b>\nВсего пользователей: <b>{count}</b>", reply_markup=admin_kb(message.from_user.id))

@router.message(F.text.lower().startswith(".give "))
@router.business_message(F.text.lower().startswith(".give "))
async def cmd_give(message: Message):
    if int(message.from_user.id) != int(ADMIN_ID): return
    try:
        _, target_id, days = message.text.split()
        await grant_days(int(target_id), int(days))
        await savemod_edit_or_reply(message, f"✅ Пользователю <code>{target_id}</code> выдано <b>{days}</b> дней VIP!")
    except Exception:
        await savemod_edit_or_reply(message, "❌ <b>Ошибка! Использование:</b> <code>.give [ID] [дней]</code>")
