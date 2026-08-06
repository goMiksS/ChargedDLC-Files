from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
import json

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


async def safe_reply(message: Message, text: str, reply_markup=None, parse_mode="HTML"):
    """Универсальная отправка/редактирование сообщений в любом контексте."""
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        return
    except Exception:
        pass
    try:
        await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        pass


def menu_kb(user_id: int, has_sub: bool, trial_used: bool):
    b = InlineKeyboardBuilder()
    if not has_sub and not trial_used:
        b.button(text="🎁 Пробный период (3 дня)", callback_data="trial")
        b.adjust(1)
        return b.as_markup()
    b.button(text="📊 Статистика", callback_data="stats")
    b.button(text="⚙️ Настройки", callback_data="settings")
    b.button(text="📝 Команды", callback_data="help")
    b.button(text="👤 Профиль", callback_data="profile")
    b.button(text="💎 VIP / Магазин", callback_data="shop")
    b.button(text="🎮 Игры", callback_data="games")
    if user_id == ADMIN_ID:
        b.button(text="🛠 Админ", callback_data="admin_panel")
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
    b.button(text=f"{notify} Удаления", callback_data="tog_del")
    b.button(text=f"{edit_n} Правки", callback_data="tog_edit")
    b.button(text="◀️ Назад", callback_data="back_main")
    b.adjust(1)
    return b.as_markup()


def shop_kb():
    b = InlineKeyboardBuilder()
    for key, plan in VIP_PLANS.items():
        b.button(text=f"{plan['title']} — {plan['price']} ⭐", callback_data=f"buy_{key}")
    b.button(text="🎁 Пробный период", callback_data="trial")
    b.button(text="◀️ Назад", callback_data="back_main")
    b.adjust(1)
    return b.as_markup()


def admin_kb():
    b = InlineKeyboardBuilder()
    b.button(text="👥 Список пользователей", callback_data="admin_users")
    b.button(text="📊 Статистика бота", callback_data="admin_stats")
    b.button(text="📜 Логи / последние", callback_data="admin_logs")
    b.button(text="🧹 Очистка", callback_data="admin_clean")
    b.button(text="◀️ Назад", callback_data="back_main")
    b.adjust(1)
    return b.as_markup()


HELP_TEXT = f"""📝 <b>Команды {BOT_NAME}</b>

<code>.help</code> <code>.stats</code> <code>.settings</code> <code>.profile</code>
<code>.shop</code> <code>.vip</code> <code>.id</code> <code>.ping</code> <code>.about</code>

<b>Сообщения</b>
<code>.search</code> <code>.export</code> <code>.last</code> <code>.clear</code> <code>.media</code>

<b>Текст</b>
<code>.sw</code> <code>.reverse</code> <code>.upper</code> <code>.lower</code> <code>.count</code>
<code>.leet</code> <code>.kawaii</code> <code>.love</code> <code>.type</code> <code>.say</code>

<b>Рандом / игры</b>
<code>.random</code> <code>.choose</code> <code>.coin</code> <code>.dice</code> <code>.ball</code>
<code>.ttt</code> <code>.rps</code> <code>.guess</code> <code>.slot</code>

<b>Социальные</b>
<code>.ship</code> <code>.rate</code> <code>.hug</code> <code>.kiss</code> <code>.slap</code>

<b>Админ</b>
<code>.admin</code> <code>.give ID дней</code> <code>.users</code>
"""


@router.message(CommandStart())
async def cmd_start(message: Message):
    if not is_private(message):
        return
    user = message.from_user
    await register_user(user.id, user.username or "", user.full_name or "")
    sub = await get_subscription(user.id)

    if not sub["active"] and not sub["trial_used"]:
        text = (
            f"👋 Привет, {user.first_name}!\n\n"
            f"Я — <b>{BOT_NAME}</b> <code>v{VERSION}</code>\n\n"
            f"Ловлю удалённые сообщения, правки и protected медиа.\n\n"
            f"🎁 Нажми кнопку ниже, чтобы активировать <b>пробный период {TRIAL_DAYS} дня</b>."
        )
        await safe_reply(message, text, reply_markup=menu_kb(user.id, False, False))
        return

    status = f"\n💎 VIP до <b>{sub['until'][:10]}</b>\n" if sub["active"] else ""

    text = (
        f"👋 Привет, {user.first_name}!\n\n"
        f"Я — <b>{BOT_NAME}</b> <code>v{VERSION}</code>{status}\n"
        f"Подключение: Настройки → Автоматизация чатов → добавь бота\n\n"
        f"<code>.help</code> · <code>.shop</code>"
    )
    await safe_reply(message, text, reply_markup=menu_kb(user.id, sub["active"], sub["trial_used"]))


@router.message(F.text.lower().in_({".help", ".помощь"}))
@router.business_message(F.text.lower().in_({".help", ".помощь"}))
async def cmd_help(message: Message):
    sub = await get_subscription(message.from_user.id)
    kb = menu_kb(message.from_user.id, sub["active"], sub["trial_used"])
    await safe_reply(message, HELP_TEXT, reply_markup=kb)


@router.message(F.text.lower().in_({".shop", ".vip", ".магазин"}))
@router.business_message(F.text.lower().in_({".shop", ".vip", ".магазин"}))
async def cmd_shop(message: Message):
    sub = await get_subscription(message.from_user.id)
    status = f"✅ VIP до <b>{sub['until'][:10]}</b>\n\n" if sub["active"] else "❌ Подписка не активна\n\n"
    await safe_reply(message, f"💎 <b>Магазин VIP</b>\n\n{status}Выбери тариф:", reply_markup=shop_kb())


@router.message(F.text.lower().in_({".stats", ".стата"}))
@router.business_message(F.text.lower().in_({".stats", ".стата"}))
async def cmd_stats(message: Message):
    stats = await get_user_stats(message.from_user.id)
    sub = await get_subscription(message.from_user.id)
    if not stats:
        await safe_reply(message, "Пока нет данных.")
        return
    vip = f"\n💎 VIP до {sub['until'][:10]}" if sub["active"] else ""
    await safe_reply(message, f"📊 Сохранено: <b>{stats['total_saved']}</b>\n🗑 Удалений: <b>{stats['total_deleted']}</b>\n✏️ Правок: <b>{stats['total_edited']}</b>{vip}")


@router.message(F.text.lower().in_({".settings", ".настройки"}))
@router.business_message(F.text.lower().in_({".settings", ".настройки"}))
async def cmd_settings(message: Message):
    s = await get_user_settings(message.from_user.id)
    await safe_reply(message, "⚙️ Настройки", reply_markup=settings_kb(s))


@router.message(F.text.lower().in_({".profile", ".я", ".me"}))
@router.business_message(F.text.lower().in_({".profile", ".я", ".me"}))
async def cmd_profile(message: Message):
    user = await get_user(message.from_user.id)
    sub = await get_subscription(message.from_user.id)
    if not user:
        await safe_reply(message, "Сначала /start в ЛС с ботом")
        return
    vip = f"до {sub['until'][:10]}" if sub["active"] else "нет"
    await safe_reply(message, f"👤 {user['full_name']}\nID: <code>{user['user_id']}</code>\nVIP: {vip}\nСообщений: {user['messages_saved']}")


@router.message(F.text.lower() == ".id")
@router.business_message(F.text.lower() == ".id")
async def cmd_id(message: Message):
    await safe_reply(message, f"<code>{message.from_user.id}</code>")


@router.message(F.text.lower() == ".ping")
@router.business_message(F.text.lower() == ".ping")
async def cmd_ping(message: Message):
    await safe_reply(message, "🏓 Pong")


@router.message(F.text.lower() == ".about")
@router.business_message(F.text.lower() == ".about")
async def cmd_about(message: Message):
    await safe_reply(message, f"<b>{BOT_NAME}</b> v{VERSION}\nСохранение удалённых сообщений через Автоматизацию.")


@router.message(F.text.lower().startswith(".search"))
@router.business_message(F.text.lower().startswith(".search"))
async def cmd_search(message: Message):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await safe_reply(message, "Использование: <code>.search текст</code>")
        return
    results = await search_messages(message.from_user.id, parts[1].strip(), 10)
    if not results:
        await safe_reply(message, "Пусто")
        return
    lines = [f"🔍 Найдено {len(results)}:\n"] + [f"• {(r['text'] or r['content_type'] or '')[:70]}" for r in results]
    await safe_reply(message, "\n".join(lines))


@router.message(F.text.lower() == ".export")
@router.business_message(F.text.lower() == ".export")
async def cmd_export(message: Message):
    data = await export_user_messages(message.from_user.id, 200)
    if not data:
        await safe_reply(message, "Нечего экспортировать")
        return
    path = f"media/export_{message.from_user.id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    from aiogram.types import FSInputFile
    await message.answer_document(FSInputFile(path), caption="📦 Экспорт")


@router.message(F.text.lower() == ".last")
@router.business_message(F.text.lower() == ".last")
async def cmd_last(message: Message):
    data = await export_user_messages(message.from_user.id, 5)
    if not data:
        await safe_reply(message, "Пусто")
        return
    lines = ["🕒 Последние сообщения:\n"] + [f"• {r['from_name']}: {(r['text'] or '')[:50]}" for r in data]
    await safe_reply(message, "\n".join(lines))


@router.message(F.text.lower() == ".media")
@router.business_message(F.text.lower() == ".media")
async def cmd_media(message: Message):
    stats = await get_user_stats(message.from_user.id)
    await safe_reply(message, f"🖼 Сохранено медиа: <b>{stats['media_saved'] if stats else 0}</b>")


# ===== CALLBACK HANDLERS =====

@router.callback_query(F.data == "trial")
async def cb_trial(c: CallbackQuery):
    ok = await start_trial(c.from_user.id, TRIAL_DAYS)
    if ok:
        sub = await get_subscription(c.from_user.id)
        await c.message.edit_text(
            f"🎁 Пробный период <b>{TRIAL_DAYS} дня</b> активирован!\n"
            f"До: <code>{sub['until'][:16]}</code>\n\n"
            f"Подключи бота: Настройки → Автоматизация чатов",
            reply_markup=menu_kb(c.from_user.id, True, True),
            parse_mode="HTML"
        )
    else:
        await c.answer("Пробный уже использован или VIP активен", show_alert=True)
    await c.answer()


@router.callback_query(F.data == "shop")
async def cb_shop(c: CallbackQuery):
    sub = await get_subscription(c.from_user.id)
    status = f"✅ VIP до <b>{sub['until'][:10]}</b>\n\n" if sub["active"] else "❌ Нет подписки\n\n"
    await c.message.edit_text(f"💎 <b>Магазин</b>\n\n{status}", reply_markup=shop_kb(), parse_mode="HTML")
    await c.answer()


@router.callback_query(F.data.startswith("buy_"))
async def cb_buy(c: CallbackQuery, bot: Bot):
    key = c.data.replace("buy_", "")
    plan = VIP_PLANS.get(key)
    if not plan:
        await c.answer("Нет тарифа", show_alert=True)
        return
    try:
        await bot.send_invoice(
            chat_id=c.from_user.id,
            title=plan["title"],
            description=f"VIP {plan['days']} дней — {BOT_NAME}",
            payload=f"vip:{key}:{c.from_user.id}",
            currency="XTR",
            prices=[LabeledPrice(label=plan["title"], amount=plan["price"])],
        )
        await c.answer()
    except Exception as e:
        await c.answer(str(e)[:100], show_alert=True)


@router.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(q.id, ok=True)


@router.message(F.successful_payment)
async def success_pay(message: Message):
    parts = (message.successful_payment.invoice_payload or "").split(":")
    if len(parts) >= 2 and parts[0] == "vip":
        plan = VIP_PLANS.get(parts[1])
        if plan:
            until = await grant_days(message.from_user.id, plan["days"], True)
            await message.answer(f"✅ VIP на {plan['days']} дн. до <code>{until[:16]}</code>", parse_mode="HTML")


# ===== ADMIN =====
@router.message(F.text.lower() == ".admin")
@router.business_message(F.text.lower() == ".admin")
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    count = await get_all_users_count()
    await safe_reply(message, f"🛠 <b>Админ</b>\nПользователей: <b>{count}</b>\n<code>.give ID дней</code>", reply_markup=admin_kb())


@router.message(F.text.lower().startswith(".give"))
@router.business_message(F.text.lower().startswith(".give"))
async def cmd_give(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = (message.text or "").split()
    if len(parts) < 3:
        await safe_reply(message, "Использование: <code>.give USER_ID дней</code>")
        return
    try:
        uid, days = int(parts[1]), int(parts[2])
    except ValueError:
        await safe_reply(message, "Укажите числа!")
        return
    until = await grant_days(uid, days, True)
    await safe_reply(message, f"✅ Выдано {days} дн. → <code>{uid}</code>\nДо: {until[:16]}")


@router.message(F.text.lower() == ".users")
@router.business_message(F.text.lower() == ".users")
async def cmd_users(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await safe_reply(message, f"👥 Пользователей: {await get_all_users_count()}")


@router.callback_query(F.data == "admin_panel")
async def cb_admin(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        await c.answer("Нет доступа", show_alert=True)
        return
    count = await get_all_users_count()
    await c.message.edit_text(f"🛠 <b>Админ</b>\nЮзеров: <b>{count}</b>", reply_markup=admin_kb(), parse_mode="HTML")
    await c.answer()


@router.callback_query(F.data == "admin_users")
async def cb_admin_users(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return
    import aiosqlite
    from config import DB_PATH
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT user_id, username, full_name, is_vip FROM users ORDER BY joined_at DESC LIMIT 30") as cur:
            rows = await cur.fetchall()
    lines = ["👥 <b>Пользователи</b> (до 30):\n"]
    for r in rows:
        vip = "💎" if r["is_vip"] else ""
        lines.append(f"{vip}<code>{r['user_id']}</code> {r['full_name'] or ''} @{r['username'] or '—'}")
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Назад", callback_data="admin_panel")
    await c.message.edit_text("\n".join(lines)[:3500], reply_markup=b.as_markup(), parse_mode="HTML")
    await c.answer()


@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return
    count = await get_all_users_count()
    await c.message.edit_text(f"📊 Юзеров: <b>{count}</b>\nВерсия: {VERSION}", parse_mode="HTML")
    await c.answer()


@router.callback_query(F.data == "admin_clean")
async def cb_admin_clean(c: CallbackQuery):
    if c.from_user.id != ADMIN_ID:
        return
    await clean_old_messages()
    await c.answer("Очищено", show_alert=True)


@router.callback_query(F.data == "stats")
async def cb_stats(c: CallbackQuery):
    await cmd_stats(c.message)
    await c.answer()

@router.callback_query(F.data == "help")
async def cb_help(c: CallbackQuery):
    sub = await get_subscription(c.from_user.id)
    kb = menu_kb(c.from_user.id, sub["active"], sub["trial_used"])
    await c.message.edit_text(HELP_TEXT, reply_markup=kb, parse_mode="HTML")
    await c.answer()

@router.callback_query(F.data == "profile")
async def cb_profile(c: CallbackQuery):
    await cmd_profile(c.message)
    await c.answer()

@router.callback_query(F.data == "settings")
async def cb_settings(c: CallbackQuery):
    s = await get_user_settings(c.from_user.id)
    await c.message.edit_text("⚙️ Настройки:", reply_markup=settings_kb(s))
    await c.answer()

@router.callback_query(F.data == "back_main")
async def cb_back(c: CallbackQuery):
    sub = await get_subscription(c.from_user.id)
    await c.message.edit_text("Главное меню:", reply_markup=menu_kb(c.from_user.id, sub["active"], sub["trial_used"]))
    await c.answer()

@router.callback_query(F.data.startswith("tog_"))
async def cb_tog(c: CallbackQuery):
    s = await get_user_settings(c.from_user.id)
    m = {"tog_own": "save_own", "tog_media": "save_media", "tog_del": "notify_delete", "tog_edit": "notify_edit"}
    k = m.get(c.data)
    if k:
        s[k] = not s.get(k, True)
        await update_user_settings(c.from_user.id, s)
    await c.message.edit_reply_markup(reply_markup=settings_kb(s))
    await c.answer("OK")
