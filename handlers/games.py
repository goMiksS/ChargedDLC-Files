import random
import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

# Состояние для игр (в памяти)
# state format: {user_id: {"game": "ttt", "board": [...], "turn": "X" или "number": 42}}
active_games = {}


def safe_edit(message: Message):
    pass


# ==========================================
# 1. КРЕСТИКИ-НОЛИКИ (TIC-TAC-TOE)
# ==========================================

def get_ttt_keyboard(board):
    b = InlineKeyboardBuilder()
    for i in range(9):
        val = board[i] if board[i] != " " else " "
        b.button(text=val, callback_data=f"ttt_move_{i}")
    b.adjust(3)
    b.button(text="🏳️ Сдаться", callback_data="ttt_quit")
    b.adjust(3, 3, 3, 1)
    return b.as_markup()


def check_ttt_winner(board):
    lines = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),  # строки
        (0, 3, 6), (1, 4, 7), (2, 5, 8),  # столбцы
        (0, 4, 8), (2, 4, 6)             # диагонали
    ]
    for a, b, c in lines:
        if board[a] == board[b] == board[c] and board[a] != " ":
            return board[a]
    if " " not in board:
        return "draw"
    return None


def bot_ttt_move(board):
    empty = [i for i, cell in enumerate(board) if cell == " "]
    if not empty:
        return board
    
    # 1. Попытка выиграть
    for i in empty:
        temp = board.copy()
        temp[i] = "O"
        if check_ttt_winner(temp) == "O":
            return temp

    # 2. Попытка заблокировать игрока
    for i in empty:
        temp = board.copy()
        temp[i] = "X"
        if check_ttt_winner(temp) == "X":
            board[i] = "O"
            return board

    # 3. Случайный ход
    move = random.choice(empty)
    board[move] = "O"
    return board


@router.callback_query(F.data == "game_ttt")
async def start_ttt_cb(c: CallbackQuery):
    user_id = c.from_user.id
    active_games[user_id] = {
        "game": "ttt",
        "board": [" "] * 9
    }
    await c.message.edit_text(
        "❌⭕ <b>Крестики-Нолики</b>\nТвой ход! (Ты играешь за ❌)",
        reply_markup=get_ttt_keyboard(active_games[user_id]["board"]),
        parse_mode="HTML"
    )
    await c.answer()


@router.callback_query(F.data.startswith("ttt_move_"))
async def process_ttt_move(c: CallbackQuery):
    user_id = c.from_user.id
    if user_id not in active_games or active_games[user_id].get("game") != "ttt":
        await c.answer("Игра не найдена. Начни новую!", show_alert=True)
        return

    move_idx = int(c.data.split("_")[2])
    board = active_games[user_id]["board"]

    if board[move_idx] != " ":
        await c.answer("Эта клетка уже занята!", show_alert=True)
        return

    # Ход игрока
    board[move_idx] = "X"
    winner = check_ttt_winner(board)

    if winner == "X":
        del active_games[user_id]
        await c.message.edit_text(f"🎉 <b>Победа!</b> Ты выиграл!\n\n{render_board(board)}", parse_mode="HTML")
        await c.answer()
        return
    elif winner == "draw":
        del active_games[user_id]
        await c.message.edit_text(f"🤝 <b>Ничья!</b>\n\n{render_board(board)}", parse_mode="HTML")
        await c.answer()
        return

    # Ход бота
    board = bot_ttt_move(board)
    winner = check_ttt_winner(board)

    if winner == "O":
        del active_games[user_id]
        await c.message.edit_text(f"🤖 <b>Бот победил!</b> Попробуй ещё раз.\n\n{render_board(board)}", parse_mode="HTML")
        await c.answer()
        return
    elif winner == "draw":
        del active_games[user_id]
        await c.message.edit_text(f"🤝 <b>Ничья!</b>\n\n{render_board(board)}", parse_mode="HTML")
        await c.answer()
        return

    active_games[user_id]["board"] = board
    await c.message.edit_text(
        "❌⭕ <b>Крестики-Нолики</b>\nТвой ход!",
        reply_markup=get_ttt_keyboard(board),
        parse_mode="HTML"
    )
    await c.answer()


@router.callback_query(F.data == "ttt_quit")
async def quit_ttt(c: CallbackQuery):
    user_id = c.from_user.id
    if user_id in active_games:
        del active_games[user_id]
    await c.message.edit_text("Игра отменена.")
    await c.answer()


def render_board(board):
    b = [c if c != " " else "▪️" for c in board]
    return f"{b[0]} {b[1]} {b[2]}\n{b[3]} {b[4]} {b[5]}\n{b[6]} {b[7]} {b[8]}"


# ==========================================
# 2. КАМЕНЬ, НОЖНИЦЫ, БУМАГА (RPS)
# ==========================================

@router.callback_query(F.data == "game_rps")
async def start_rps_cb(c: CallbackQuery):
    b = InlineKeyboardBuilder()
    b.button(text="🪨 Камень", callback_data="rps_rock")
    b.button(text="✂️ Ножницы", callback_data="rps_scissors")
    b.button(text="📄 Бумага", callback_data="rps_paper")
    b.adjust(3)
    await c.message.edit_text("✂️ <b>Камень-Ножницы-Бумага</b>\nСделай выбор:", reply_markup=b.as_markup(), parse_mode="HTML")
    await c.answer()


@router.callback_query(F.data.startswith("rps_"))
async def process_rps(c: CallbackQuery):
    user_choice = c.data.replace("rps_", "")
    choices = {"rock": "🪨 Камень", "scissors": "✂️ Ножницы", "paper": "📄 Бумага"}
    bot_choice = random.choice(["rock", "scissors", "paper"])

    rules = {
        "rock": "scissors",
        "scissors": "paper",
        "paper": "rock"
    }

    if user_choice == bot_choice:
        res = "🤝 <b>Ничья!</b>"
    elif rules[user_choice] == bot_choice:
        res = "🎉 <b>Ты победил!</b>"
    else:
        res = "🤖 <b>Бот победил!</b>"

    text = (
        f"<b>Результат игры:</b>\n\n"
        f"Твой выбор: {choices[user_choice]}\n"
        f"Выбор бота: {choices[bot_choice]}\n\n"
        f"{res}"
    )

    b = InlineKeyboardBuilder()
    b.button(text="🔄 Играть снова", callback_data="game_rps")
    b.button(text="◀️ Меню", callback_data="games")
    b.adjust(1)

    await c.message.edit_text(text, reply_markup=b.as_markup(), parse_mode="HTML")
    await c.answer()


# ==========================================
# 3. УГАДАЙ ЧИСЛО (GUESS)
# ==========================================

@router.callback_query(F.data == "game_guess")
async def start_guess_cb(c: CallbackQuery):
    secret = random.randint(1, 100)
    active_games[c.from_user.id] = {
        "game": "guess",
        "secret": secret,
        "attempts": 0
    }
    await c.message.edit_text(
        "🎯 <b>Угадай число от 1 до 100</b>\n\n"
        "Отправь боту число в сообщении (например: <code>50</code>).\n"
        "У тебя неограниченное количество попыток!",
        parse_mode="HTML"
    )
    await c.answer()


@router.message(F.text.isdigit())
async def process_guess_msg(message: Message):
    user_id = message.from_user.id
    if user_id not in active_games or active_games[user_id].get("game") != "guess":
        return  # Обычное число в чате, пропускаем

    game = active_games[user_id]
    num = int(message.text)
    game["attempts"] += 1

    if num < game["secret"]:
        await message.answer(f"📈 Загаданное число <b>БОЛЬШЕ</b> чем {num}! (Попытка {game['attempts']})", parse_mode="HTML")
    elif num > game["secret"]:
        await message.answer(f"📉 Загаданное число <b>МЕНЬШЕ</b> чем {num}! (Попытка {game['attempts']})", parse_mode="HTML")
    else:
        attempts = game["attempts"]
        del active_games[user_id]
        await message.answer(
            f"🎉 <b>ПОЗДРАВЛЯЕМ!</b>\n\nТы угадал число <b>{num}</b> за <b>{attempts}</b> попыток!",
            parse_mode="HTML"
        )


# ==========================================
# 4. СЛОТЫ (SLOT MACHINE)
# ==========================================

@router.callback_query(F.data == "game_slot")
async def start_slot_cb(c: CallbackQuery):
    symbols = ["🍎", "🍋", "7️⃣", "🔔", "💎"]
    res1, res2, res3 = random.choice(symbols), random.choice(symbols), random.choice(symbols)

    if res1 == res2 == res3 == "7️⃣":
        win = "🔥 <b>JACKPOT!!! 777!</b> 🔥"
    elif res1 == res2 == res3:
        win = "🎉 <b>Большой выигрыш! 3 в ряд!</b>"
    elif res1 == res2 or res2 == res3 or res1 == res3:
        win = "✨ <b>Малый выигрыш! 2 совпадения!</b>"
    else:
        win = "❌ Не повезло, попробуй ещё!"

    text = f"🎰 <b>Слот-машина</b>\n\n[ {res1} | {res2} | {res3} ]\n\n{win}"

    b = InlineKeyboardBuilder()
    b.button(text="🎰 Крутить еще", callback_data="game_slot")
    b.button(text="◀️ Назад", callback_data="games")
    b.adjust(1)

    await c.message.edit_text(text, reply_markup=b.as_markup(), parse_mode="HTML")
    await c.answer()


# ==========================================
# 5. КОМАНДЫ-ЧАТА ДЛЯ ИГР (.ttt, .rps, .slot, .guess)
# ==========================================

@router.message(F.text.lower().startswith(".ttt"))
@router.business_message(F.text.lower().startswith(".ttt"))
async def cmd_ttt(message: Message):
    user_id = message.from_user.id
    active_games[user_id] = {
        "game": "ttt",
        "board": [" "] * 9
    }
    await message.answer(
        "❌⭕ <b>Крестики-Нолики</b>\nТвой ход!",
        reply_markup=get_ttt_keyboard(active_games[user_id]["board"]),
        parse_mode="HTML"
    )


@router.message(F.text.lower().startswith(".rps"))
@router.business_message(F.text.lower().startswith(".rps"))
async def cmd_rps(message: Message):
    b = InlineKeyboardBuilder()
    b.button(text="🪨 Камень", callback_data="rps_rock")
    b.button(text="✂️ Ножницы", callback_data="rps_scissors")
    b.button(text="📄 Бумага", callback_data="rps_paper")
    b.adjust(3)
    await message.answer("✂️ <b>Камень-Ножницы-Бумага</b>\nСделай выбор:", reply_markup=b.as_markup(), parse_mode="HTML")


@router.message(F.text.lower().startswith(".slot"))
@router.business_message(F.text.lower().startswith(".slot"))
async def cmd_slot(message: Message):
    try:
        await message.delete()
    except Exception:
        pass
    await message.answer_dice(emoji="🎰")


@router.message(F.text.lower().startswith(".guess"))
@router.business_message(F.text.lower().startswith(".guess"))
async def cmd_guess(message: Message):
    secret = random.randint(1, 100)
    active_games[message.from_user.id] = {
        "game": "guess",
        "secret": secret,
        "attempts": 0
    }
    await message.answer("🎯 Я загадал число от 1 до 100. Пиши числа в чат!")
