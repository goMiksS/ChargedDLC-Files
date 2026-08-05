from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
import json
from datetime import datetime

from config import ADMIN_ID, VERSION, BOT_NAME, CMD_PREFIX, TRIAL_DAYS, VIP_PLANS
from db.database import (
    register_user, get_user, get_user_stats, get_user_settings,
    update_user_settings, get_all_users_count, search_messages,
    export_user_messages, clean_old_messages,
    get_subscription, grant_days, start_trial, has_access
)

router = Router()


async def safe_edit(message: Message, text: str, reply_markup=None, parse_mode="HTML"):
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except Exception:
        pass
    try:
        await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        pass


def main_menu_kb():
    b = InlineKeyboardBuilder()
    b.button(text="📊 Статистика", callback_data="stats")
    b.button(text="⚙️ Настройки", callback_data="settings")
    b.button(text="📝 Команды", callback_data="help")
    b.button(text="👤 Профиль", callback_data="profile")
    b.button(text="💎 VIP / Магазин", callback_data="shop")
    b.button(text="ℹ️ О боте", callback_data="about")
    b.adjust(2)
    return b.as_markup()


def settings_kb(settings: dict):
    b = InlineKeyboardBuilder()
    own = "✅" if settings.get("save_own", True) else "❌"
    media = "✅" if settings.get("save_media", True) else "❌"
    notify = "✅" if settings.get("notify_delete", True) else "❌"
    edit_n = "✅" if settings.get("notify_edit", True) else "❌"
    b.button(text=f"{own} Свои сообщения", callback_data="tog_own")
    b.button(text=f"{media} Медиа", callback_data="tog_media")
    b.button(text=f"{notify} Уведомления об удалении", callback_data="tog_del")
    b.button(text=f"{edit_n} Уведомления о правках", callback_data="tog_edit")
    b.button(text="◀️ Назад", callback_data="back_main")
    b.adjust(1)
    return b.as_markup()


def shop_kb():
    b = InlineKeyboardBuilder()
    for key, plan in VIP_PLANS.items():
        b.button(
            text=f"{plan['title']} — {plan['price']} ⭐",
            callback_data=f"buy_{key}"
        )
    b.button(text="🎁 Пробный период", callback_data="trial")
    b.button(text="◀️ Назад", callback_data="back_main")
    b.adjust(1)
    return b.as_markup()


HELP_TEXT = f"""📝 <b>Команды {BOT_NAME}</b>

<b>Основные</b>
<code>.help</code> — этот список
<code>.stats</code> — статистика
<code>.settings</code> — настройки
<code>.profile</code> / <code>.я</code> — профиль
<code>.shop</code> / <code>.vip</code> — магазин VIP
<code>.id</code> <code>.ping</code> <code>.version</code> <code>.about</code>

<b>Сообщения</b>
<code>.search текст</code> — поиск
<code>.export</code> — экспорт
<code>.last</code> — последние 5
<code>.clear</code> — очистка
<code>.media</code> — кол-во медиа

<b>Текст</b>
<code>.sw</code> — раскладка
<code>.reverse</code> <code>.upper</code> <code>.lower</code> <code>.count</code>
<code>.leet</code> <code>.kawaii</code> <code>.love</code>
<code>.type</code> <code>.say</code> <code>.repeat</code>

<b>Рандом</b>
<code>.random</code> <code>.choose a|b</code> <code>.coin</code> <code>.dice</code>
<code>.ball</code> <code>.password</code> <code>.uuid</code> <code>.calc</code>

<b>Социальные</b>
<code>.ship</code> <code>.rate</code> <code>.howgay</code> <code>.pp</code>
<code>.hug</code> <code>.kiss</code> <code>.pat</code> <code>.slap</code> <code>.kill</code>

<b>Мемы</b>
<code>.table</code> <code>.shrug</code> <code>.lenny</code> <code>.joke</code> <code>.quote</code> <code>.fact</code>

<b>Инфо</b>
<code>.dox</code> <code>.whoami</code> <code>.server</code>

<b>Админ</b>
<code>.admin</code> <code>.users</code> <code>.clean</code>
<code>.give ID дней</code> — выдать подписку
<code>.broadcast текст</code>
"""


# ========== START ==========
async def _start(message: Message):
    user = message.from_user
    await register_user(user.id, user.username or "", user.full_name or "")
    sub = await get_subscription(user.id)
    status = ""
    if sub["active"]:
        until = sub["until"][:10] if sub["until"] else "?"
        status = f"\n💎 VIP до <b>{until}</b>\n"
    elif not sub["trial_used"]:
        status = f"\n🎁 Доступен пробный период {TRIAL_DAYS} дня — <code>.shop</code>\n"

    text = (
        f"👋 Привет, {user.first_name}!\n\n"
        f"Я — <b>{BOT_NAME}</b> <code>v{VERSION}</code>\n"
        f"{status}\n"
        f"Ловлю удалённые сообщения, правки и protected медиа.\n\n"
        f"<b>Подключение:</b>\n"
        f"Настройки Telegram → Автоматизация чатов → добавь бота\n\n"
        f"Команды: <code>.help</code> · Магазин: <code>.shop</code>"
    )
    await safe_edit(message, text, reply_markup=main_menu_kb())

@router.message(CommandStart())
@router.business_message(CommandStart())
async def cmd_start(message: Message):
    await _start(message)


# ========== HELP ==========
@router.message(Command("help"))
@router.message(F.text.lower().in_({".help", ".помощь"}))
@router.business_message(F.text.lower().in_({".help", ".помощь"}))
async def cmd_help(message: Message):
    await safe_edit(message, HELP_TEXT)


# ========== SHOP / VIP ==========
async def _shop(message: Message):
    sub = await get_subscription(message.from_user.id)
    if sub["active"]:
        until = sub["until"][:16] if sub["until"] else "?"
        status = f"✅ Подписка активна до <b>{until}</b>\n\n"
    else:
        status = "❌ Подписка не активна\n\n"
    text = (
        f"💎 <b>Магазин VIP</b>\n\n"
        f"{status}"
        f"VIP даёт полный доступ к сохранению сообщений и всем функциям.\n\n"
        f"Выбери тариф:"
    )
    await safe_edit(message, text, reply_markup=shop_kb())

@router.message(F.text.lower().in_({".shop", ".vip", ".магазин"}))
@router.business_message(F.text.lower().in_({".shop", ".vip", ".магазин"}))
async def cmd_shop(message: Message):
    await _shop(message)


@router.callback_query(F.data == "shop")
async def cb_shop(c: CallbackQuery):
    await _shop(c.message)
    await c.answer()


@router.callback_query(F.data == "trial")
async def cb_trial(c: CallbackQuery):
    ok = await start_trial(c.from_user.id, TRIAL_DAYS)
    if ok:
        await c.message.edit_text(
            f"🎁 Пробный период на <b>{TRIAL_DAYS} дня</b> активирован!\n"
            f"Полный доступ открыт.",
            parse_mode="HTML"
        )
    else:
        await c.answer("Пробный период уже использован или подписка активна", show_alert=True)
    await c.answer()


@router.callback_query(F.data.startswith("buy_"))
async def cb_buy(c: CallbackQuery, bot: Bot):
    key = c.data.replace("buy_", "")
    plan = VIP_PLANS.get(key)
    if not plan:
        await c.answer("Тариф не найден", show_alert=True)
        return
    # Счёт через Telegram Stars
    try:
        await bot.send_invoice(
            chat_id=c.from_user.id,
            title=plan["title"],
            description=f"VIP доступ на {plan['days']} дней в {BOT_NAME}",
            payload=f"vip:{key}:{c.from_user.id}",
            currency="XTR",  # Telegram Stars
            prices=[LabeledPrice(label=plan["title"], amount=plan["price"])],
        )
        await c.answer()
    except Exception as e:
        await c.answer(f"Ошибка оплаты: {e}", show_alert=True)


@router.pre_checkout_query()
async def on_pre_checkout(query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(query.id, ok=True)


@router.message(F.successful_payment)
async def on_success_payment(message: Message):
    payload = message.successful_payment.invoice_payload or ""
    # vip:vip_30:123456
    parts = payload.split(":")
    if len(parts) >= 2 and parts[0] == "vip":
        key = parts[1]
        plan = VIP_PLANS.get(key)
        if plan:
            until = await grant_days(message.from_user.id, plan["days"], make_vip=True)
            await message.answer(
                f"✅ Оплата прошла!\n"
                f"VIP на <b>{plan['days']} дней</b> активирован.\n"
                f"До: <code>{until[:16]}</code>",
                parse_mode="HTML"
            )


# ========== STATS ==========
async def _stats(message: Message):
    stats = await get_user_stats(message.from_user.id)
    sub = await get_subscription(message.from_user.id)
    if not stats:
        await safe_edit(message, "Пока нет данных.")
        return
    vip_line = ""
    if sub["active"]:
        vip_line = f"\n💎 VIP до {sub['until'][:10]}"
    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"💾 Сохранено: <b>{stats['total_saved']}</b>\n"
        f"🗑 Удалений: <b>{stats['total_deleted']}</b>\n"
        f"✏️ Правок: <b>{stats['total_edited']}</b>\n"
        f"🖼 Медиа: <b>{stats['media_saved']}</b>"
        f"{vip_line}"
    )
    await safe_edit(message, text)

@router.message(F.text.lower().in_({".stats", ".стата", ".stat"}))
@router.business_message(F.text.lower().in_({".stats", ".стата", ".stat"}))
async def cmd_stats(message: Message):
    await _stats(message)


@router.message(F.text.lower().in_({".settings", ".настройки", ".set"}))
@router.business_message(F.text.lower().in_({".settings", ".настройки", ".set"}))
async def cmd_settings(message: Message):
    settings = await get_user_settings(message.from_user.id)
    await safe_edit(message, "⚙️ <b>Настройки</b>", reply_markup=settings_kb(settings))


@router.message(F.text.lower().in_({".profile", ".я", ".me"}))
@router.business_message(F.text.lower().in_({".profile", ".я", ".me"}))
async def cmd_profile(message: Message):
    user = await get_user(message.from_user.id)
    sub = await get_subscription(message.from_user.id)
    if not user:
        await safe_edit(message, "Сначала /start")
        return
    vip = f"до {sub['until'][:10]}" if sub["active"] else "нет"
    text = (
        f"👤 <b>Профиль</b>\n\n"
        f"Имя: {user['full_name']}\n"
        f"ID: <code>{user['user_id']}</code>\n"
        f"VIP: {vip}\n"
        f"Пробный: {'использован' if sub['trial_used'] else 'доступен'}\n\n"
        f"Сообщений: {user['messages_saved']}\n"
        f"Удалений: {user['deletes_caught']}\n"
        f"Правок: {user['edits_caught']}"
    )
    await safe_edit(message, text)


@router.message(F.text.lower() == ".id")
@router.business_message(F.text.lower() == ".id")
async def cmd_id(message: Message):
    await safe_edit(message, f"ID: <code>{message.from_user.id}</code>\nЧат: <code>{message.chat.id}</code>")


@router.message(F.text.lower() == ".ping")
@router.business_message(F.text.lower() == ".ping")
async def cmd_ping(message: Message):
    await safe_edit(message, "🏓 Pong")


@router.message(F.text.lower() == ".version")
@router.business_message(F.text.lower() == ".version")
async def cmd_version(message: Message):
    await safe_edit(message, f"<b>{BOT_NAME}</b>\n<code>{VERSION}</code>")


@router.message(F.text.lower() == ".about")
@router.business_message(F.text.lower() == ".about")
async def cmd_about(message: Message):
    await safe_edit(
        message,
        f"<b>{BOT_NAME}</b> v{VERSION}\n\n"
        f"Бот для сохранения удалённых и отредактированных сообщений.\n"
        f"Работает через Автоматизацию чатов Telegram."
    )


@router.message(F.text.lower().startswith(".search"))
@router.business_message(F.text.lower().startswith(".search"))
async def cmd_search(message: Message):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await safe_edit(message, "Использование: <code>.search текст</code>")
        return
    results = await search_messages(message.from_user.id, parts[1].strip(), limit=10)
    if not results:
        await safe_edit(message, "Ничего не найдено.")
        return
    lines = [f"🔍 Найдено {len(results)}:\n"]
    for r in results:
        preview = (r["text"] or r["caption"] or r["content_type"])[:80]
        lines.append(f"• [{r['created_at'][:16]}] {preview}")
    await safe_edit(message, "\n".join(lines))


@router.message(F.text.lower() == ".export")
@router.business_message(F.text.lower() == ".export")
async def cmd_export(message: Message):
    data = await export_user_messages(message.from_user.id, limit=200)
    if not data:
        await safe_edit(message, "Нечего экспортировать.")
        return
    path = f"media/export_{message.from_user.id}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    from aiogram.types import FSInputFile
    try:
        await message.delete()
    except Exception:
        pass
    await message.answer_document(FSInputFile(path), caption="📦 Экспорт")


@router.message(F.text.lower() == ".clear")
@router.business_message(F.text.lower() == ".clear")
async def cmd_clear(message: Message):
    await safe_edit(message, "⚠️ Для очистки: <code>.clear confirm</code>")


@router.message(F.text.lower() == ".clear confirm")
@router.business_message(F.text.lower() == ".clear confirm")
async def cmd_clear_confirm(message: Message):
    await clean_old_messages()
    await safe_edit(message, "✅ Старые записи очищены.")


@router.message(F.text.lower() == ".last")
@router.business_message(F.text.lower() == ".last")
async def cmd_last(message: Message):
    data = await export_user_messages(message.from_user.id, limit=5)
    if not data:
        await safe_edit(message, "Пока пусто.")
        return
    lines = ["🕒 Последние:\n"]
    for r in data:
        preview = (r["text"] or r["caption"] or r["content_type"])[:60]
        lines.append(f"• {r['created_at'][:16]} | {r['from_name']}: {preview}")
    await safe_edit(message, "\n".join(lines))


@router.message(F.text.lower() == ".media")
@router.business_message(F.text.lower() == ".media")
async def cmd_media(message: Message):
    stats = await get_user_stats(message.from_user.id)
    await safe_edit(message, f"🖼 Медиа: <b>{stats['media_saved'] if stats else 0}</b>")


# ===== ADMIN =====
@router.message(F.text.lower() == ".admin")
@router.business_message(F.text.lower() == ".admin")
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    count = await get_all_users_count()
    await safe_edit(
        message,
        f"🛠 <b>Админ-панель</b>\n\n"
        f"Пользователей: <b>{count}</b>\n"
        f"Версия: {VERSION}\n\n"
        f"<code>.give ID дней</code> — выдать VIP\n"
        f"<code>.users</code> <code>.clean</code>\n"
        f"<code>.broadcast текст</code>"
    )


@router.message(F.text.lower().startswith(".give"))
@router.business_message(F.text.lower().startswith(".give"))
async def cmd_give(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = (message.text or "").split()
    if len(parts) < 3:
        await safe_edit(message, "Использование: <code>.give USER_ID дней</code>\nПример: <code>.give 123456 30</code>")
        return
    try:
        uid = int(parts[1])
        days = int(parts[2])
    except ValueError:
        await safe_edit(message, "ID и дни должны быть числами")
        return
    until = await grant_days(uid, days, make_vip=True)
    await safe_edit(message, f"✅ Выдано <b>{days}</b> дней пользователю <code>{uid}</code>\nДо: {until[:16]}")


@router.message(F.text.lower() == ".users")
@router.business_message(F.text.lower() == ".users")
async def cmd_users(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    count = await get_all_users_count()
    await safe_edit(message, f"👥 Пользователей: <b>{count}</b>")


@router.message(F.text.lower() == ".clean")
@router.business_message(F.text.lower() == ".clean")
async def cmd_admin_clean(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await clean_old_messages()
    await safe_edit(message, "✅ Очистка выполнена.")


@router.message(F.text.lower().startswith(".broadcast"))
@router.business_message(F.text.lower().startswith(".broadcast"))
async def cmd_broadcast(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await safe_edit(message, "Использование: <code>.broadcast текст</code>")
        return
    await safe_edit(message, f"Рассылка: {parts[1]}")


# ===== CALLBACKS =====
@router.callback_query(F.data == "stats")
async def cb_stats(c: CallbackQuery):
    await _stats(c.message)
    await c.answer()

@router.callback_query(F.data == "help")
async def cb_help(c: CallbackQuery):
    await safe_edit(c.message, HELP_TEXT)
    await c.answer()

@router.callback_query(F.data == "profile")
async def cb_profile(c: CallbackQuery):
    await cmd_profile(c.message)
    await c.answer()

@router.callback_query(F.data == "settings")
async def cb_settings(c: CallbackQuery):
    settings = await get_user_settings(c.from_user.id)
    try:
        await c.message.edit_text("⚙️ <b>Настройки</b>", reply_markup=settings_kb(settings), parse_mode="HTML")
    except Exception:
        pass
    await c.answer()

@router.callback_query(F.data == "back_main")
async def cb_back(c: CallbackQuery):
    try:
        await c.message.edit_text("Меню:", reply_markup=main_menu_kb())
    except Exception:
        pass
    await c.answer()

@router.callback_query(F.data.startswith("tog_"))
async def cb_toggle(c: CallbackQuery):
    settings = await get_user_settings(c.from_user.id)
    key_map = {"tog_own": "save_own", "tog_media": "save_media", "tog_del": "notify_delete", "tog_edit": "notify_edit"}
    key = key_map.get(c.data)
    if key:
        settings[key] = not settings.get(key, True)
        await update_user_settings(c.from_user.id, settings)
    try:
        await c.message.edit_reply_markup(reply_markup=settings_kb(settings))
    except Exception:
        pass
    await c.answer("Обновлено")

@router.callback_query(F.data == "about")
async def cb_about(c: CallbackQuery):
    await cmd_about(c.message)
    await c.answer()
