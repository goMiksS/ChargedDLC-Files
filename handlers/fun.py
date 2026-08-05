"""
Все весёлые и пользовательские команды (.check .spam .love .mute и т.д.)
Многие работают в личке с ботом, т.к. это Business-бот (не userbot).
"""

import asyncio
import random
import re
import html
from pathlib import Path
from uuid import uuid4

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import CMD_PREFIX, ADMIN_ID, MEDIA_DIR

router = Router()

# ==================== СОСТОЯНИЯ ====================
class Form(StatesGroup):
    waiting_spam_text = State()
    waiting_spam_count = State()
    waiting_type_text = State()
    waiting_zaebu = State()
    waiting_love = State()
    afk_text = State()
    format_mode = State()

# Хранилища в памяти (на пользователя)
user_format_mode: dict[int, str] = {}      # bold / italic / ...
user_afk: dict[int, str] = {}              # AFK текст
user_troll: dict[int, bool] = {}
active_games: dict[int, dict] = {}         # игры

# ==================== ХЕЛПЕРЫ ====================
def is_cmd(text: str, name: str) -> bool:
    if not text:
        return False
    t = text.lower().strip()
    return t == f"{CMD_PREFIX}{name}" or t.startswith(f"{CMD_PREFIX}{name} ")

def get_arg(text: str) -> str:
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""

# Раскладка для .sw
EN = "qwertyuiop[]asdfghjkl;'zxcvbnm,./QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>?"
RU = "йцукенгшщзхъфывапролджэячсмитьбю.ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,"

def switch_layout(text: str) -> str:
    table = str.maketrans(EN + RU, RU + EN)
    return text.translate(table)

def to_leet(text: str) -> str:
    leet_map = {
        'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '5', 't': '7',
        'A': '4', 'E': '3', 'I': '1', 'O': '0', 'S': '5', 'T': '7',
        'l': '1', 'L': '1', 'b': '8', 'B': '8', 'g': '9', 'G': '9'
    }
    return ''.join(leet_map.get(c, c) for c in text)

def to_kawaii(text: str) -> str:
    faces = [" (◕‿◕)", " (≧◡≦)", " (｡♥‿♥｡)", " ☆*:.｡.o(≧▽≦)o.｡.:*☆", " (づ｡◕‿‿◕｡)づ", " ♡"]
    return text + random.choice(faces)

def love_text(text: str) -> str:
    hearts = ["❤️", "💕", "💖", "💗", "💓", "💞", "💘", "💝"]
    words = text.split()
    return " ".join(w + random.choice(hearts) for w in words)

TROLL_PHRASES = [
    "Ахах, серьёзно? 🤡",
    "Ну ты и выдал...",
    "Кринж полный.",
    "Это ты сейчас серьёзно написал?",
    "Ок, бумер.",
    "Скилл issue.",
    "L + ratio",
    "Не, ну ты даёшь.",
    "Я даже комментировать не буду.",
    "Смешно... нет.",
    "Ты опять за своё?",
    "Понял, принял, осудил.",
]

# ==================== .HELP РАСШИРЕННЫЙ ====================
HELP_FULL = """
📝 <b>Команды SaveMod++</b>

▫️ <b>Работа с сообщениями</b>
  • .check — анализирует файл (ответь на файл)
  • .spam — спамит текстом (в личке с ботом)
  • .help — список команд
  • .love — оформляет текст сердечками
  • .mute — мутит собеседника (симуляция)
  • .sw — переключает раскладку текста
  • .troll — отвечает тролль-фразами
  • .type — набирает текст по буквам
  • .zaebu — надоедает сообщениями

▫️ <b>Форматирование</b>
  • .bold — жирный режим
  • .italic — курсив
  • .monospace — моноширинный
  • .underline — подчёркивание
  • .leet — L33T стиль
  • .kawaii — kawaii-режим
  • .normal — выключить форматирование

▫️ <b>Игры</b>
  • .bw — Закрась поле
  • .dice — кубик
  • .duel — дуэль
  • .flip — монетка
  • .chk — шашки (упрощённо)
  • .ttt — крестики-нолики

▫️ <b>Обработка</b>
  • .clone — клон профиля (инфо)
  • .dox / .info — инфо о пользователе
  • .fv — меняет голос (симуляция)
  • .afk — автоответ AFK
  • .gifts — показывает подарки (заглушка)
  • .nk — отправляет неко-тян

▫️ <b>Утилиты</b>
  • .random .choose .coin .dice .ball .8ball
  • .say .reverse .upper .lower .count
  • .password .uuid .calc .repeat
  • .whoami .server .uptime
  • .joke .quote .fact .weather

▫️ <b>Социальные</b>
  • .ship .rate .howgay .pp
  • .hug .kiss .pat .slap .kill
  • .table .untable .shrug .lenny .magic .fight
  • .short — пересказ
  • .status — ставит статус (симуляция)
  • .story — арт из историй (симуляция)
  • .time — время в профиль (симуляция)
  • .yars — поиск похожих (заглушка)
  • .gif — в GIF (заглушка)
  • .lq — шакалит фото (ответь на фото)

▫️ <b>Остальное</b>
  • .gosu — сюрприз
  • .ping .version .about .id .stats .settings

Справка по команде: <code>.help check</code> или <code>.help чек</code>
"""

HELP_DETAIL = {
    "check": "Ответь на любой файл/фото/видео командой .check — бот проанализирует тип, размер, mime и т.д.",
    "spam": "В личке: .spam → введи текст → количество. Бот будет слать тебе сообщения (для теста).",
    "love": ".love текст   или ответь на сообщение .love — обернёт слова сердечками.",
    "mute": "Симуляция мута. В реальных чатах Business-бот не может мутить.",
    "sw": "Ответь на сообщение или напиши .sw текст — переключит раскладку EN↔RU.",
    "troll": ".troll on/off — включает режим, в котором бот отвечает тролль-фразами на твои сообщения.",
    "type": ".type текст — бот будет «печатать» текст по одной букве.",
    "zaebu": ".zaebu N — пришлёт N надоедливых сообщений (макс 15).",
    "bold": "Включает режим: все твои следующие сообщения бот будет пересылать жирным.",
    "italic": "Режим курсива.",
    "monospace": "Моноширинный режим.",
    "underline": "Подчёркивание.",
    "leet": "L33T-стиль (a→4, e→3 и т.д.).",
    "kawaii": "Добавляет кавайные смайлики.",
    "bw": "Игра «Закрась поле» — мини-головоломка.",
    "dice": "Бросает кубик 🎲",
    "duel": ".duel @user — вызывает на дуэль (симуляция).",
    "flip": "Орёл или решка.",
    "ttt": "Крестики-нолики против бота.",
    "afk": ".afk текст — ставит AFK. Когда тебе напишут (в бизнес-чатах) — бот ответит.",
    "dox": ".dox или .info — показывает известную информацию о тебе/собеседнике.",
    "nk": "Присылает случайную неко-фразу/картинку-заглушку.",
    "lq": "Ответь на фото .lq — «шакалит» (сжимает сильно).",
    "gosu": "Случайный сюрприз.",
}

@router.message(F.text.lower().startswith(f"{CMD_PREFIX}help"))
async def cmd_help_fun(message: Message):
    arg = get_arg(message.text).lower().replace("ё", "е")
    if arg:
        # алиасы
        aliases = {"чек": "check", "спам": "spam", "лав": "love", "свитч": "sw",
                   "тролль": "troll", "тайп": "type", "заебу": "zaebu", "муте": "mute",
                   "докс": "dox", "инфо": "info", "афк": "afk"}
        key = aliases.get(arg, arg)
        detail = HELP_DETAIL.get(key)
        if detail:
            await message.answer(f"<b>.{key}</b>\n\n{detail}", parse_mode="HTML")
        else:
            await message.answer("Команда не найдена. Напиши просто .help")
        return
    await message.answer(HELP_FULL, parse_mode="HTML")

# ==================== РАБОТА С СООБЩЕНИЯМИ ====================

@router.message(F.text.lower().startswith(f"{CMD_PREFIX}check"))
async def cmd_check(message: Message):
    target = message.reply_to_message or message
    if not (target.document or target.photo or target.video or target.audio or target.voice or target.video_note):
        await message.answer("Ответь командой <code>.check</code> на файл / фото / видео", parse_mode="HTML")
        return

    lines = ["📝 <b>Анализ файла</b>\n"]
    if target.document:
        d = target.document
        lines.append(f"Тип: document")
        lines.append(f"Имя: <code>{html.escape(d.file_name or '—')}</code>")
        lines.append(f"MIME: <code>{d.mime_type or '—'}</code>")
        lines.append(f"Размер: {d.file_size or 0} байт")
        lines.append(f"file_id: <code>{d.file_id[:40]}...</code>")
    elif target.photo:
        p = target.photo[-1]
        lines.append(f"Тип: photo")
        lines.append(f"Размер: {p.width}x{p.height}")
        lines.append(f"file_size: {p.file_size or 0}")
    elif target.video:
        v = target.video
        lines.append(f"Тип: video")
        lines.append(f"Размер: {v.width}x{v.height}")
        lines.append(f"Длительность: {v.duration} сек")
        lines.append(f"MIME: {v.mime_type}")
    elif target.voice:
        lines.append(f"Тип: voice | {target.voice.duration} сек")
    elif target.video_note:
        lines.append(f"Тип: video_note | {target.video_note.duration} сек")
    elif target.audio:
        a = target.audio
        lines.append(f"Тип: audio | {a.duration} сек | {a.title or '—'}")

    await message.answer("\n".join(lines), parse_mode="HTML")

@router.message(F.text.lower().startswith(f"{CMD_PREFIX}spam"))
async def cmd_spam(message: Message, state: FSMContext):
    await state.set_state(Form.waiting_spam_text)
    await message.answer("Введи текст для спама (или /cancel):")

@router.message(Form.waiting_spam_text)
async def spam_text(message: Message, state: FSMContext):
    if message.text and message.text.lower() == "/cancel":
        await state.clear()
        await message.answer("Отменено.")
        return
    await state.update_data(spam_text=message.text)
    await state.set_state(Form.waiting_spam_count)
    await message.answer("Сколько раз отправить? (1-20)")

@router.message(Form.waiting_spam_count)
async def spam_count(message: Message, state: FSMContext, bot: Bot):
    try:
        count = int(message.text.strip())
        count = max(1, min(count, 20))
    except:
        await message.answer("Число от 1 до 20")
        return
    data = await state.get_data()
    text = data.get("spam_text", "spam")
    await state.clear()
    await message.answer(f"Начинаю спам x{count}...")
    for i in range(count):
        await bot.send_message(message.chat.id, f"{text} ({i+1}/{count})")
        await asyncio.sleep(0.4)
    await message.answer("Готово.")

@router.message(F.text.lower().startswith(f"{CMD_PREFIX}love"))
async def cmd_love(message: Message):
    text = get_arg(message.text)
    if not text and message.reply_to_message:
        text = message.reply_to_message.text or message.reply_to_message.caption or ""
    if not text:
        await message.answer("Напиши .love текст   или ответь на сообщение")
        return
    await message.answer(love_text(text))

@router.message(F.text.lower().startswith(f"{CMD_PREFIX}mute"))
async def cmd_mute(message: Message):
    await message.answer(
        "🔇 <b>Мут</b>\n\n"
        "Business-бот не может реально мутить пользователей в чатах.\n"
        "Это доступно только администраторам чата или через userbot.\n"
        "Команда оставлена как заглушка.",
        parse_mode="HTML"
    )

@router.message(F.text.lower().startswith(f"{CMD_PREFIX}sw"))
async def cmd_sw(message: Message):
    text = get_arg(message.text)
    if not text and message.reply_to_message:
        text = message.reply_to_message.text or message.reply_to_message.caption or ""
    if not text:
        await message.answer("Напиши .sw текст  или ответь на сообщение")
        return
    await message.answer(f"<code>{html.escape(switch_layout(text))}</code>", parse_mode="HTML")

@router.message(F.text.lower().startswith(f"{CMD_PREFIX}troll"))
async def cmd_troll(message: Message):
    arg = get_arg(message.text).lower()
    uid = message.from_user.id
    if arg in ("on", "вкл", "1", "true"):
        user_troll[uid] = True
        await message.answer("😈 Режим тролля включён. Пиши что угодно.")
    elif arg in ("off", "выкл", "0", "false"):
        user_troll[uid] = False
        await message.answer("Режим тролля выключен.")
    else:
        user_troll[uid] = not user_troll.get(uid, False)
        status = "включён" if user_troll[uid] else "выключен"
        await message.answer(f"😈 Режим тролля {status}")

@router.message(F.text.lower().startswith(f"{CMD_PREFIX}type"))
async def cmd_type(message: Message, bot: Bot):
    text = get_arg(message.text)
    if not text:
        await message.answer("Использование: .type текст")
        return
    msg = await message.answer("✏️")
    current = ""
    for char in text:
        current += char
        try:
            await msg.edit_text(current + "▌")
        except:
            pass
        await asyncio.sleep(0.07)
    await msg.edit_text(current)

@router.message(F.text.lower().startswith(f"{CMD_PREFIX}zaebu"))
async def cmd_zaebu(message: Message, bot: Bot):
    arg = get_arg(message.text)
    try:
        n = int(arg) if arg else 5
        n = max(1, min(n, 15))
    except:
        n = 5
    phrases = [
        "Эй", "Ты тут?", "Ответь", "Ну где ты", "Аллооо",
        "Я жду", "Серьёзно?", "Ну же", "Давай", "Не игнорируй",
        "Я всё ещё здесь", "Хватит молчать", "Отвечай уже"
    ]
    await message.answer(f"Начинаю доставать x{n}...")
    for i in range(n):
        await bot.send_message(message.chat.id, random.choice(phrases))
        await asyncio.sleep(0.5)
    await message.answer("Всё, надоел.")

# ==================== ФОРМАТИРОВАНИЕ ====================

FORMAT_MODES = {
    "bold": ("b", "жирный"),
    "italic": ("i", "курсив"),
    "monospace": ("code", "моноширинный"),
    "underline": ("u", "подчёркнутый"),
    "leet": (None, "L33T"),
    "kawaii": (None, "kawaii"),
}

@router.message(F.text.lower().in_({f"{CMD_PREFIX}bold", f"{CMD_PREFIX}italic", f"{CMD_PREFIX}monospace",
                                    f"{CMD_PREFIX}underline", f"{CMD_PREFIX}leet", f"{CMD_PREFIX}kawaii",
                                    f"{CMD_PREFIX}normal"}))
async def cmd_format_mode(message: Message):
    mode = message.text.lower().strip()[1:]  # убираем точку
    uid = message.from_user.id
    if mode == "normal":
        user_format_mode.pop(uid, None)
        await message.answer("Форматирование выключено.")
        return
    user_format_mode[uid] = mode
    name = FORMAT_MODES.get(mode, (None, mode))[1]
    await message.answer(f"Режим <b>{name}</b> включён.\nПиши сообщения — я буду их оформлять.\nВыключить: .normal", parse_mode="HTML")

# Перехват обычных сообщений для форматирования и тролля
@router.message(F.text & ~F.text.startswith("."))
async def on_plain_text(message: Message, bot: Bot):
    uid = message.from_user.id
    text = message.text

    # Тролль-режим
    if user_troll.get(uid):
        await message.reply(random.choice(TROLL_PHRASES))
        return

    # Форматирование
    mode = user_format_mode.get(uid)
    if not mode:
        return

    if mode == "leet":
        result = to_leet(text)
        await message.answer(result)
    elif mode == "kawaii":
        result = to_kawaii(text)
        await message.answer(result)
    else:
        tag = FORMAT_MODES[mode][0]
        if tag:
            safe = html.escape(text)
            await message.answer(f"<{tag}>{safe}</{tag}>", parse_mode="HTML")

# ==================== ИГРЫ ====================

@router.message(F.text.lower() == f"{CMD_PREFIX}flip")
async def cmd_flip(message: Message):
    result = random.choice(["🦅 Орёл", "🪙 Решка"])
    await message.answer(f"Монетка: <b>{result}</b>", parse_mode="HTML")

@router.message(F.text.lower() == f"{CMD_PREFIX}dice")
async def cmd_dice(message: Message):
    await message.answer_dice(emoji="🎲")

@router.message(F.text.lower().startswith(f"{CMD_PREFIX}duel"))
async def cmd_duel(message: Message):
    await message.answer(
        "⚔️ <b>Дуэль</b>\n\n"
        "Вызови соперника: .duel @username\n"
        "(В Business-боте реальный перевод звёзд недоступен — это симуляция)\n\n"
        f"Ты бросил перчатку! 🧤\n"
        f"Случайный исход: {random.choice(['Победа 🏆', 'Поражение 💀', 'Ничья 🤝'])}",
        parse_mode="HTML"
    )

@router.message(F.text.lower() == f"{CMD_PREFIX}ttt")
async def cmd_ttt(message: Message):
    # Простые крестики-нолики 3x3
    board = [" "] * 9
    def render(b):
        return (
            f"<code>{b[0]}|{b[1]}|{b[2]}\n"
            f"-+-+-\n"
            f"{b[3]}|{b[4]}|{b[5]}\n"
            f"-+-+-\n"
            f"{b[6]}|{b[7]}|{b[8]}</code>\n\n"
            f"Ходи: отправь число 1-9"
        )
    active_games[message.from_user.id] = {"type": "ttt", "board": board, "turn": "X"}
    await message.answer("❌ Крестики-нолики\nТы — X\n\n" + render(board), parse_mode="HTML")

@router.message(F.text.regexp(r"^[1-9]$"))
async def ttt_move(message: Message):
    uid = message.from_user.id
    game = active_games.get(uid)
    if not game or game.get("type") != "ttt":
        return
    pos = int(message.text) - 1
    board = game["board"]
    if board[pos] != " ":
        await message.answer("Клетка занята")
        return
    board[pos] = "X"
    # Победа игрока?
    wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
    if any(board[a]==board[b]==board[c]=="X" for a,b,c in wins):
        await message.answer("🎉 Ты победил!")
        active_games.pop(uid, None)
        return
    if " " not in board:
        await message.answer("Ничья!")
        active_games.pop(uid, None)
        return
    # Ход бота
    empty = [i for i,v in enumerate(board) if v == " "]
    bot_pos = random.choice(empty)
    board[bot_pos] = "O"
    if any(board[a]==board[b]==board[c]=="O" for a,b,c in wins):
        await message.answer("💀 Бот победил!\n" + 
            f"<code>{board[0]}|{board[1]}|{board[2]}\n-+-+-\n{board[3]}|{board[4]}|{board[5]}\n-+-+-\n{board[6]}|{board[7]}|{board[8]}</code>",
            parse_mode="HTML")
        active_games.pop(uid, None)
        return
    render = (
        f"<code>{board[0]}|{board[1]}|{board[2]}\n"
        f"-+-+-\n"
        f"{board[3]}|{board[4]}|{board[5]}\n"
        f"-+-+-\n"
        f"{board[6]}|{board[7]}|{board[8]}</code>"
    )
    await message.answer(render + "\nТвой ход (1-9)", parse_mode="HTML")

@router.message(F.text.lower() == f"{CMD_PREFIX}bw")
async def cmd_bw(message: Message):
    size = 5
    field = [["⬜" for _ in range(size)] for _ in range(size)]
    # случайно закрасим пару
    for _ in range(3):
        field[random.randint(0,4)][random.randint(0,4)] = "⬛"
    text = "🎨 <b>Закрась поле</b>\nНажми на клетку чтобы переключить\n\n"
    text += "\n".join("".join(row) for row in field)
    text += "\n\n(Пока текстовая версия — просто любуйся)"
    await message.answer(text, parse_mode="HTML")

@router.message(F.text.lower() == f"{CMD_PREFIX}chk")
async def cmd_chk(message: Message):
    await message.answer("♟️ Шашки пока в разработке.\nМожешь сыграть в .ttt (крестики-нолики)")

# ==================== ОБРАБОТКА ====================

@router.message(F.text.lower().in_({f"{CMD_PREFIX}dox", f"{CMD_PREFIX}info"}))
async def cmd_dox(message: Message):
    u = message.from_user
    target = message.reply_to_message.from_user if message.reply_to_message else u
    text = (
        f"🕵️ <b>Инфо</b>\n\n"
        f"ID: <code>{target.id}</code>\n"
        f"Имя: {html.escape(target.full_name)}\n"
        f"Юзернейм: @{target.username or 'нет'}\n"
        f"Язык: {target.language_code or '—'}\n"
        f"Premium: {'✅' if target.is_premium else '❌'}\n"
        f"Бот: {'✅' if target.is_bot else '❌'}"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(F.text.lower().startswith(f"{CMD_PREFIX}afk"))
async def cmd_afk(message: Message):
    text = get_arg(message.text) or "Я сейчас AFK, отвечу позже."
    user_afk[message.from_user.id] = text
    await message.answer(f"💤 AFK включён:\n<code>{html.escape(text)}</code>\n\nВыключить: .afk off", parse_mode="HTML")

@router.message(F.text.lower() == f"{CMD_PREFIX}afk off")
async def cmd_afk_off(message: Message):
    user_afk.pop(message.from_user.id, None)
    await message.answer("AFK выключен.")

@router.message(F.text.lower() == f"{CMD_PREFIX}nk")
async def cmd_nk(message: Message):
    neko = [
        "ニャー！ (ня~)",
        "Няяя~ ฅ^•ﻌ•^ฅ",
        "Ты мой хозяин? Ня!",
        "Погладь неко-тян...",
        "Мяу мяу 🐱",
        "Ня-а-а... хочу вкусняшку",
    ]
    await message.answer(random.choice(neko))

@router.message(F.text.lower() == f"{CMD_PREFIX}gosu")
async def cmd_gosu(message: Message):
    surprises = [
        "🎁 Тебе выпал легендарный стикер... но его съела кошка.",
        "✨ +1 к удаче на сегодня.",
        "🍕 Воображаемая пицца доставлена.",
        "🦄 Единорог пробежал мимо.",
        "💫 Звёзды сегодня благосклонны.",
        "🐱 Ня. Просто ня.",
    ]
    await message.answer(random.choice(surprises))

@router.message(F.text.lower().startswith(f"{CMD_PREFIX}lq"))
async def cmd_lq(message: Message, bot: Bot):
    if not message.reply_to_message or not message.reply_to_message.photo:
        await message.answer("Ответь на фото командой .lq")
        return
    photo = message.reply_to_message.photo[-1]
    try:
        file = await bot.get_file(photo.file_id)
        path = Path(MEDIA_DIR) / f"lq_{uuid4()}.jpg"
        await bot.download_file(file.file_path, path)
        # Просто пересылаем с подписью (реальное сильное сжатие требует PIL)
        await message.answer_photo(FSInputFile(path), caption="🖼 Шакал-версия (упрощённо)")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

@router.message(F.text.lower().in_({f"{CMD_PREFIX}clone", f"{CMD_PREFIX}status", f"{CMD_PREFIX}time",
                                    f"{CMD_PREFIX}story", f"{CMD_PREFIX}fv", f"{CMD_PREFIX}gifts",
                                    f"{CMD_PREFIX}yars", f"{CMD_PREFIX}gif", f"{CMD_PREFIX}short"}))
async def cmd_stub(message: Message):
    cmd = message.text.lower().strip()[1:].split()[0]
    explanations = {
        "clone": "Клонирование профиля доступно только через userbot / MTProto.",
        "status": "Смена имени/статуса — только через аккаунт пользователя (userbot).",
        "time": "Время в имени — функция userbot.",
        "story": "Арт из историй требует доступа к stories API от имени пользователя.",
        "fv": "Смена голоса — обработка аудио, можно добавить позже.",
        "gifts": "Список подарков доступен через Business API в новых версиях.",
        "yars": "Поиск источника фото (saucenao и т.п.) — можно подключить API.",
        "gif": "Конвертация в GIF требует ffmpeg + дополнительной обработки.",
        "short": "Пересказ голосового / диалога — нужна speech-to-text + LLM.",
    }
    await message.answer(
        f"ℹ️ <b>.{cmd}</b>\n\n{explanations.get(cmd, 'Команда в разработке.')}\n\n"
        f"Этот бот работает через <b>Business / Автоматизация</b>, поэтому часть userbot-функций недоступна.",
        parse_mode="HTML"
    )

# AFK автоответ (срабатывает на обычные сообщения в личке)
@router.message(F.chat.type == "private", F.text)
async def afk_watcher(message: Message, bot: Bot):
    # Если кто-то пишет владельцу, у которого AFK — но в private это сам пользователь
    # Для бизнес-чатов AFK обрабатывается в business.py при желании
    pass


# ==================== ЕЩЁ БОЛЬШЕ КОМАНД ====================

@router.message(F.text.lower() == f"{CMD_PREFIX}random")
async def cmd_random(message: Message):
    choices = [
        "Да", "Нет", "Возможно", "Точно да", "Точно нет",
        "Спроси позже", "Лучше не надо", "100%", "0%", "50/50"
    ]
    await message.answer(f"🎲 {random.choice(choices)}")

@router.message(F.text.lower().startswith(f"{CMD_PREFIX}choose"))
async def cmd_choose(message: Message):
    arg = get_arg(message.text)
    if not arg or "|" not in arg:
        await message.answer("Использование: <code>.choose вариант1 | вариант2 | вариант3</code>", parse_mode="HTML")
        return
    options = [o.strip() for o in arg.split("|") if o.strip()]
    if len(options) < 2:
        await message.answer("Нужно минимум 2 варианта через |")
        return
    await message.answer(f"🎯 Выбрано: <b>{random.choice(options)}</b>", parse_mode="HTML")

@router.message(F.text.lower() == f"{CMD_PREFIX}coin")
@router.message(F.text.lower() == f"{CMD_PREFIX}flip")
async def cmd_coin(message: Message):
    await message.answer(f"🪙 {random.choice(['Орёл', 'Решка'])}")

@router.message(F.text.lower() == f"{CMD_PREFIX}dice")
async def cmd_dice(message: Message):
    await message.answer_dice(emoji="🎲")

@router.message(F.text.lower() == f"{CMD_PREFIX}ball")
async def cmd_ball(message: Message):
    answers = [
        "Бесспорно", "Предрешено", "Никаких сомнений", "Определённо да",
        "Можешь быть уверен в этом", "Мне кажется — да", "Вероятнее всего",
        "Хорошие перспективы", "Знаки говорят — да", "Да",
        "Пока не ясно, попробуй снова", "Спроси позже", "Лучше не рассказывать",
        "Сейчас нельзя предсказать", "Сконцентрируйся и спроси опять",
        "Даже не думай", "Мой ответ — нет", "По моим данным — нет",
        "Перспективы не очень хорошие", "Весьма сомнительно"
    ]
    await message.answer(f"🎱 {random.choice(answers)}")

@router.message(F.text.lower().startswith(f"{CMD_PREFIX}say"))
async def cmd_say(message: Message):
    text = get_arg(message.text)
    if not text:
        await message.answer("Напиши: .say текст")
        return
    await message.answer(text)

@router.message(F.text.lower().startswith(f"{CMD_PREFIX}reverse"))
async def cmd_reverse(message: Message):
    text = get_arg(message.text)
    if not text and message.reply_to_message:
        text = message.reply_to_message.text or message.reply_to_message.caption or ""
    if not text:
        await message.answer("Ответь на сообщение или напиши .reverse текст")
        return
    await message.answer(text[::-1])

@router.message(F.text.lower().startswith(f"{CMD_PREFIX}upper"))
async def cmd_upper(message: Message):
    text = get_arg(message.text)
    if not text and message.reply_to_message:
        text = message.reply_to_message.text or ""
    if text:
        await message.answer(text.upper())

@router.message(F.text.lower().startswith(f"{CMD_PREFIX}lower"))
async def cmd_lower(message: Message):
    text = get_arg(message.text)
    if not text and message.reply_to_message:
        text = message.reply_to_message.text or ""
    if text:
        await message.answer(text.lower())

@router.message(F.text.lower().startswith(f"{CMD_PREFIX}count"))
async def cmd_count(message: Message):
    text = get_arg(message.text)
    if not text and message.reply_to_message:
        text = message.reply_to_message.text or ""
    if not text:
        await message.answer("Нужен текст")
        return
    chars = len(text)
    words = len(text.split())
    lines = len(text.splitlines())
    await message.answer(f"📊 Символов: {chars}\nСлов: {words}\nСтрок: {lines}")

@router.message(F.text.lower() == f"{CMD_PREFIX}password")
async def cmd_password(message: Message):
    import string
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    pwd = ''.join(random.choice(chars) for _ in range(16))
    await message.answer(f"🔐 <code>{pwd}</code>", parse_mode="HTML")

@router.message(F.text.lower() == f"{CMD_PREFIX}uuid")
async def cmd_uuid(message: Message):
    await message.answer(f"<code>{uuid4()}</code>", parse_mode="HTML")

@router.message(F.text.lower().startswith(f"{CMD_PREFIX}repeat"))
async def cmd_repeat(message: Message):
    arg = get_arg(message.text)
    if not arg:
        await message.answer("Использование: .repeat 5 текст")
        return
    parts = arg.split(maxsplit=1)
    try:
        n = min(int(parts[0]), 20)
        text = parts[1] if len(parts) > 1 else "🔄"
    except:
        await message.answer("Первым должно быть число")
        return
    for _ in range(n):
        await message.answer(text)
        await asyncio.sleep(0.3)

@router.message(F.text.lower() == f"{CMD_PREFIX}uptime")
async def cmd_uptime(message: Message):
    await message.answer("⏱ Бот работает стабильно. Для точного uptime нужен внешний мониторинг.")

@router.message(F.text.lower() == f"{CMD_PREFIX}server")
async def cmd_server(message: Message):
    import platform
    await message.answer(
        f"🖥 <b>Сервер</b>\n"
        f"Python: {platform.python_version()}\n"
        f"ОС: {platform.system()} {platform.release()}\n"
        f"Архитектура: {platform.machine()}",
        parse_mode="HTML"
    )

@router.message(F.text.lower() == f"{CMD_PREFIX}whoami")
async def cmd_whoami(message: Message):
    u = message.from_user
    await message.answer(
        f"👤 <b>Ты</b>\n"
        f"ID: <code>{u.id}</code>\n"
        f"Имя: {u.full_name}\n"
        f"Юзернейм: @{u.username or 'нет'}\n"
        f"Язык: {u.language_code or '?'}\n"
        f"Premium: {'✅' if u.is_premium else '❌'}",
        parse_mode="HTML"
    )

@router.message(F.text.lower().startswith(f"{CMD_PREFIX}calc"))
async def cmd_calc(message: Message):
    expr = get_arg(message.text)
    if not expr:
        await message.answer("Использование: .calc 2+2*3")
        return
    try:
        # Безопасный eval только для простых выражений
        allowed = set("0123456789+-*/().% ")
        if not all(c in allowed for c in expr):
            await message.answer("Только цифры и +-*/()")
            return
        result = eval(expr, {"__builtins__": {}}, {})
        await message.answer(f"🧮 {expr} = <b>{result}</b>", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

@router.message(F.text.lower() == f"{CMD_PREFIX}weather")
async def cmd_weather(message: Message):
    await message.answer("🌤 Для погоды нужен API-ключ OpenWeather. Пока заглушка: сегодня солнечно (наверное).")

@router.message(F.text.lower() == f"{CMD_PREFIX}joke")
async def cmd_joke(message: Message):
    jokes = [
        "Программист ставит себе будильник на 10:00, 10:10, 10:20... чтобы поймать исключение.",
        "— Почему программисты путают Хэллоуин и Рождество? — Потому что Oct 31 == Dec 25.",
        "Баг — это не ошибка, это неожиданная фича.",
        "В мире есть 10 типов людей: те, кто понимает двоичный код, и те, кто нет.",
        "Жена программиста: купи хлеб, и если будут яйца — возьми десяток. Он принёс 10 батонов.",
    ]
    await message.answer(random.choice(jokes))

@router.message(F.text.lower() == f"{CMD_PREFIX}quote")
async def cmd_quote(message: Message):
    quotes = [
        "«Единственный способ делать великие дела — любить то, что ты делаешь.» — Стив Джобс",
        "«Сначала они тебя игнорируют, потом смеются, потом борются, потом ты побеждаешь.» — Ганди",
        "«Будущее принадлежит тем, кто верит в красоту своей мечты.» — Элеонора Рузвельт",
        "«Не бойся совершенства — тебе его никогда не достичь.» — Сальвадор Дали",
        "«Лучший способ предсказать будущее — создать его.» — Авраам Линкольн",
    ]
    await message.answer(random.choice(quotes))

@router.message(F.text.lower() == f"{CMD_PREFIX}fact")
async def cmd_fact(message: Message):
    facts = [
        "Осьминоги имеют три сердца.",
        "Мёд никогда не портится.",
        "У бананов больше генов, чем у человека.",
        "Сердце синего кита настолько большое, что человек может проплыть по его артериям.",
        "Венера — единственная планета, которая вращается по часовой стрелке.",
    ]
    await message.answer(f"📚 {random.choice(facts)}")

@router.message(F.text.lower() == f"{CMD_PREFIX}8ball")
async def cmd_8ball(message: Message):
    await cmd_ball(message)

@router.message(F.text.lower() == f"{CMD_PREFIX}ship")
async def cmd_ship(message: Message):
    if not message.reply_to_message:
        await message.answer("Ответь на сообщение человека, с которым хочешь ship")
        return
    name1 = message.from_user.first_name
    name2 = message.reply_to_message.from_user.first_name if message.reply_to_message.from_user else "???"
    percent = random.randint(0, 100)
    bar = "█" * (percent // 10) + "░" * (10 - percent // 10)
    await message.answer(f"💘 {name1} + {name2}\n[{bar}] {percent}%")

@router.message(F.text.lower() == f"{CMD_PREFIX}rate")
async def cmd_rate(message: Message):
    if message.reply_to_message:
        target = "это"
    else:
        target = "тебя"
    score = random.randint(1, 10)
    await message.answer(f"⭐ Я оцениваю {target} на <b>{score}/10</b>", parse_mode="HTML")

@router.message(F.text.lower() == f"{CMD_PREFIX}howgay")
async def cmd_howgay(message: Message):
    percent = random.randint(0, 100)
    await message.answer(f"🌈 Гей-метр: <b>{percent}%</b>", parse_mode="HTML")

@router.message(F.text.lower() == f"{CMD_PREFIX}pp")
async def cmd_pp(message: Message):
    size = random.randint(1, 30)
    await message.answer(f"🍆 {'8' + '=' * size + 'D'}")

@router.message(F.text.lower() == f"{CMD_PREFIX}kill")
async def cmd_kill(message: Message):
    if not message.reply_to_message:
        await message.answer("Ответь на сообщение жертвы")
        return
    victim = message.reply_to_message.from_user.first_name if message.reply_to_message.from_user else "жертву"
    ways = ["убил взглядом", "отправил в бан", "удалил из реальности", "забанил навсегда", "превратил в бота"]
    await message.answer(f"💀 {message.from_user.first_name} {random.choice(ways)} {victim}")

@router.message(F.text.lower() == f"{CMD_PREFIX}hug")
async def cmd_hug(message: Message):
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user.first_name
    else:
        target = "себя"
    await message.answer(f"🤗 {message.from_user.first_name} крепко обнял(а) {target}")

@router.message(F.text.lower() == f"{CMD_PREFIX}kiss")
async def cmd_kiss(message: Message):
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user.first_name
    else:
        target = "воздух"
    await message.answer(f"😘 {message.from_user.first_name} поцеловал(а) {target}")

@router.message(F.text.lower() == f"{CMD_PREFIX}pat")
async def cmd_pat(message: Message):
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user.first_name
    else:
        target = "себя"
    await message.answer(f"👋 {message.from_user.first_name} погладил(а) {target} по голове")

@router.message(F.text.lower() == f"{CMD_PREFIX}slap")
async def cmd_slap(message: Message):
    if not message.reply_to_message:
        await message.answer("Ответь на сообщение")
        return
    target = message.reply_to_message.from_user.first_name if message.reply_to_message.from_user else "кого-то"
    await message.answer(f"👋 {message.from_user.first_name} дал(а) пощёчину {target}")

@router.message(F.text.lower() == f"{CMD_PREFIX}table")
async def cmd_table(message: Message):
    await message.answer("(╯°□°)╯︵ ┻━┻")

@router.message(F.text.lower() == f"{CMD_PREFIX}untable")
async def cmd_untable(message: Message):
    await message.answer("┬─┬ ノ( ゜-゜ノ)")

@router.message(F.text.lower() == f"{CMD_PREFIX}shrug")
async def cmd_shrug(message: Message):
    await message.answer("¯\\_(ツ)_/¯")

@router.message(F.text.lower() == f"{CMD_PREFIX}lenny")
async def cmd_lenny(message: Message):
    await message.answer("( ͡° ͜ʖ ͡°)")

@router.message(F.text.lower() == f"{CMD_PREFIX}happy")
async def cmd_happy(message: Message):
    await message.answer("⊙﹏⊙")

@router.message(F.text.lower() == f"{CMD_PREFIX}sad")
async def cmd_sad(message: Message):
    await message.answer("⊙︿⊙")

@router.message(F.text.lower() == f"{CMD_PREFIX}magic")
async def cmd_magic(message: Message):
    await message.answer("(∩｀-´)⊃━☆ﾟ.*･｡ﾟ")

@router.message(F.text.lower() == f"{CMD_PREFIX}fight")
async def cmd_fight(message: Message):
    await message.answer("(ง'̀-'́)ง")

# Финальный catch-all для неизвестных .команд
@router.message(F.text.regexp(r"^\.\w+"))
async def unknown_dot_command(message: Message):
    cmd = message.text.split()[0]
    await message.answer(
        f"Команда <code>{html.escape(cmd)}</code> не найдена.\n"
        f"Напиши <code>.help</code> чтобы увидеть все доступные.",
        parse_mode="HTML"
)
