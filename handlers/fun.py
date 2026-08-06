import random
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

# Хранилище балансов и кулдаунов в памяти (можно интегрировать с БД)
USER_BALANCES = {}
COOLDOWNS = {}

def get_bal(uid: int) -> int:
    return USER_BALANCES.get(uid, 1000)

def add_bal(uid: int, amount: int):
    USER_BALANCES[uid] = max(0, get_bal(uid) + amount)

async def savemod_edit_or_reply(message: Message, text: str, reply_markup=None):
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        await message.answer(text, reply_markup=reply_markup, parse_mode="HTML")

# --- 1. Баланс ---
@router.message(F.text.lower().in_({".bal", ".баланс", ".balance"}))
@router.business_message(F.text.lower().in_({".bal", ".баланс", ".balance"}))
async def cmd_balance(message: Message):
    bal = get_bal(message.from_user.id)
    await savemod_edit_or_reply(message, f"💰 <b>Ваш баланс:</b> <code>{bal}</code> монет.")

# --- 2. Работа (.work) ---
@router.message(F.text.lower().in_({".work", ".работа"}))
@router.business_message(F.text.lower().in_({".work", ".работа"}))
async def cmd_work(message: Message):
    uid = message.from_user.id
    earned = random.randint(100, 400)
    add_bal(uid, earned)
    jobs = ["взломал сервер", "написал скрипт", "продал конфиг", "замайнил крипту", "выполнил заказ"]
    job = random.choice(jobs)
    await savemod_edit_or_reply(message, f"🛠 Вы <b>{job}</b> и получили <b>+{earned}</b> монет!\n💰 Баланс: <code>{get_bal(uid)}</code>")

# --- 3. Казино (.casino) ---
@router.message(F.text.lower().startswith((".casino ", ".казино ")))
@router.business_message(F.text.lower().startswith((".casino ", ".казино ")))
async def cmd_casino(message: Message):
    uid = message.from_user.id
    try:
        bet = int(message.text.split()[1])
    except Exception:
        return await savemod_edit_or_reply(message, "❌ <b>Использование:</b> <code>.casino [ставка]</code>")
    
    bal = get_bal(uid)
    if bet <= 0 or bet > bal:
        return await edit_or_reply(message, f"❌ У вас недостаточно монет! Баланс: <code>{bal}</code>")
    
    win = random.choice([True, False, False])
    if win:
        prize = bet * 2
        add_bal(uid, bet)
        await savemod_edit_or_reply(message, f"🎰 <b>ПОБЕДА!</b> Вы выиграли <b>+{bet}</b> монет!\n💰 Баланс: <code>{get_bal(uid)}</code>")
    else:
        add_bal(uid, -bet)
        await savemod_edit_or_reply(message, f"🎰 <b>ПРОИГРЫШ!</b> Вы потеряли <b>-{bet}</b> монет.\n💰 Баланс: <code>{get_bal(uid)}</code>")

# --- 4. Слоты (.slot) ---
@router.message(F.text.lower().startswith((".slot", ".слоты")))
@router.business_message(F.text.lower().startswith((".slot", ".слоты")))
async def cmd_slots(message: Message):
    uid = message.from_user.id
    parts = message.text.split()
    bet = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 50
    bal = get_bal(uid)
    
    if bet > bal:
        return await savemod_edit_or_reply(message, f"❌ Недостаточно монет для ставки <code>{bet}</code>.")

    items = ["🍎", "🍋", "7️⃣", "🔔", "💎"]
    line = [random.choice(items) for _ in range(3)]
    res_str = " | ".join(line)

    if line[0] == line[1] == line[2]:
        win = bet * 5
        add_bal(uid, win)
        msg = f"🎰 [ {res_str} ]\n🔥 <b>ДЖЕКПОРТ!</b> Вы выбили x5 и получили <b>+{win}</b> монет!"
    elif line[0] == line[1] or line[1] == line[2] or line[0] == line[2]:
        win = int(bet * 1.5)
        add_bal(uid, win)
        msg = f"🎰 [ {res_str} ]\n🎉 <b>Совпадение!</b> Вы получили <b>+{win}</b> монет!"
    else:
        add_bal(uid, -bet)
        msg = f"🎰 [ {res_str} ]\n❌ Не повезло. Минус <code>{bet}</code> монет."

    await savemod_edit_or_reply(message, f"{msg}\n💰 Баланс: <code>{get_bal(uid)}</code>")

# --- 5. Кубики / Dice (.dice) ---
@router.message(F.text.lower().startswith((".dice", ".кубик")))
@router.business_message(F.text.lower().startswith((".dice", ".кубик")))
async def cmd_dice(message: Message):
    user_num = random.randint(1, 6)
    bot_num = random.randint(1, 6)
    
    if user_num > bot_num:
        res = "🏆 Вы победили!"
    elif user_num < bot_num:
        res = "🤖 Победил бот!"
    else:
        res = "🤝 Ничья!"

    await savemod_edit_or_reply(message, f"🎲 <b>Ваш бросок:</b> <code>{user_num}</code>\n🎲 <b>Бросок бота:</b> <code>{bot_num}</code>\n\n{res}")

# --- 6. Монетка (.coin) ---
@router.message(F.text.lower().in_({".coin", ".монетка", ".flip"}))
@router.business_message(F.text.lower().in_({".coin", ".монетка", ".flip"}))
async def cmd_coin(message: Message):
    res = random.choice(["🦅 Орёл", "🪙 Решка"])
    await savemod_edit_or_reply(message, f"🪙 Монетка подброшена...\nРезультат: <b>{res}</b>")

# --- 7. Шар предсказаний (.ball) ---
@router.message(F.text.lower().startswith((".ball ", ".шар ")))
@router.business_message(F.text.lower().startswith((".ball ", ".шар ")))
async def cmd_ball(message: Message):
    answers = ["Бесспорно", "Предрешено", "Никаких сомнений", "Определенно да", "Спроси позже", "Даже не думай", "Мой ответ — нет", "Перспективы плохие"]
    await savemod_edit_or_reply(message, f"🔮 <b>Магический шар:</b> {random.choice(answers)}")

# --- 8. Выбор (.choose) ---
@router.message(F.text.lower().startswith((".choose ", ".выбери ")))
@router.business_message(F.text.lower().startswith((".choose ", ".выбери ")))
async def cmd_choose(message: Message):
    raw = message.text.split(maxsplit=1)
    if len(raw) < 2 or " или " not in raw[1].lower():
        return await savemod_edit_or_reply(message, "❌ <b>Использование:</b> <code>.choose чай или кофе</code>")
    opts = [x.strip() for x in raw[1].lower().split("или")]
    await savemod_edit_or_reply(message, f"🤔 Я выбираю: <b>{random.choice(opts)}</b>")

# --- 9. Русская Рулетка (.roulette) ---
@router.message(F.text.lower().in_({".roulette", ".рулетка"}))
@router.business_message(F.text.lower().in_({".roulette", ".рулетка"}))
async def cmd_roulette(message: Message):
    bullet = random.randint(1, 6)
    if bullet == 1:
        await savemod_edit_or_reply(message, "💥 <b>БАХ!</b> Вы схватили пулю. Игра окончена.")
    else:
        await savemod_edit_or_reply(message, "Клик! ⚖️ Барабан прокрутился, вам повезло — патрон пролетел мимо.")

# --- 10. Перевод денег другу (.pay) ---
@router.message(F.text.lower().startswith((".pay ", ".перевод ")))
@router.business_message(F.text.lower().startswith((".pay ", ".перевод ")))
async def cmd_pay(message: Message):
    uid = message.from_user.id
    parts = message.text.split()
    if len(parts) < 3 or not parts[1].isdigit() or not parts[2].isdigit():
        return await savemod_edit_or_reply(message, "❌ <b>Использование:</b> <code>.pay [ID_получателя] [сумма]</code>")
    
    target_id = int(parts[1])
    amount = int(parts[2])
    
    if get_bal(uid) < amount:
        return await savemod_edit_or_reply(message, "❌ У вас недостаточно монет!")
    
    add_bal(uid, -amount)
    add_bal(target_id, amount)
    await savemod_edit_or_reply(message, f"💸 Вы успешно перевели <b>{amount}</b> монет пользователю <code>{target_id}</code>!")
