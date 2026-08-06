import datetime
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from db.database import get_user, add_user, activate_trial, log_action, get_all_users, get_user_logs
from config import ADMIN_IDS

router = Router()

def get_main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="👤 Профиль")
    builder.button(text="ℹ️ Помощь")
    builder.button(text="🎮 Игры")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    
    if not user:
        await add_user(user_id)
        user = await get_user(user_id)

    trial_used, sub_until = user[1], user[2]
    now = datetime.datetime.now()
    is_active = False

    if sub_until:
        sub_date = datetime.datetime.fromisoformat(sub_until)
        if sub_date > now:
            is_active = True

    if not is_active and trial_used == 0:
        builder = InlineKeyboardBuilder()
        builder.button(text="🎁 Активировать пробный период (3 дня)", callback_data="start_trial")
        await message.answer("Добро пожаловать! Нажмите кнопку ниже, чтобы активировать пробный период:", reply_markup=builder.as_markup())
    elif not is_active:
        await message.answer("Ваш пробный период или подписка завершились.")
    else:
        await message.answer("Панель управления доступна ниже:", reply_markup=get_main_keyboard())

@router.callback_query(F.data == "start_trial")
async def process_start_trial(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user = await get_user(user_id)
    if user and user[1] == 0:
        await activate_trial(user_id)
        await log_action(user_id, "Активирован пробный период")
        await callback.message.edit_text("🎉 Пробный период на 3 дня активирован!")
        await callback.message.answer("Главное меню:", reply_markup=get_main_keyboard())
    else:
        await callback.answer("Пробный период уже активировался ранее.", show_alert=True)

# ----- Админ-панель (.admin) -----

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="👥 Пользователи", callback_data="admin_users")
    builder.button(text="📜 Просмотр логов", callback_data="admin_logs")
    builder.adjust(2)

    await message.answer("⚙️ **Панель Администратора**", reply_markup=builder.as_markup(), parse_mode="Markdown")

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    users = await get_all_users()
    await callback.message.edit_text(f"📊 Всего пользователей в системе: **{len(users)}**", parse_mode="Markdown")

@router.callback_query(F.data == "admin_users")
async def admin_users(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    users = await get_all_users()
    text = "👥 **Список пользователей:**\n"
    for u in users[-10:]:
        text += f"• ID: `{u[0]}` | Подписка: {u[1] if u[1] else 'Нет'}\n"
    await callback.message.edit_text(text, parse_mode="Markdown")

@router.callback_query(F.data == "admin_logs")
async def admin_logs(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    logs = await get_user_logs(callback.from_user.id, limit=5)
    text = "📜 **Логи активности:**\n"
    for l in logs:
        text += f"• `{l[1]}`: {l[0]}\n"
    await callback.message.edit_text(text, parse_mode="Markdown")
