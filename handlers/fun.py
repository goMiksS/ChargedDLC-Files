import asyncio
import random
import html
import string
import platform
from uuid import uuid4

from aiogram import Router, F
from aiogram.types import Message

from config import CMD_PREFIX

router = Router()

def is_priv(message: Message) -> bool:
    return message.chat.type == "private" and not getattr(message, "business_connection_id", None)


# Список известных команд — чтобы catch-all их не перехватывал
KNOWN = {
    "help", "помощь", "stats", "стата", "stat", "settings", "настройки", "set",
    "profile", "я", "me", "id", "ping", "version", "about", "search", "export",
    "clear", "last", "media", "admin", "users", "clean", "broadcast", "shop", "vip", "магазин", "give",
    "sw", "reverse", "upper", "lower", "count", "leet", "kawaii", "love",
    "type", "say", "repeat", "random", "choose", "coin", "flip", "dice",
    "ball", "8ball", "password", "uuid", "calc", "ship", "rate", "howgay",
    "pp", "hug", "kiss", "pat", "slap", "kill", "table", "untable", "shrug",
    "lenny", "magic", "fight", "joke", "quote", "fact", "dox", "info",
    "whoami", "server"
}


async def safe_edit(message: Message, text: str, parse_mode="HTML"):
    try:
        await message.edit_text(text, parse_mode=parse_mode)
        return
    except Exception:
        pass
    try:
        await message.answer(text, parse_mode=parse_mode)
    except Exception:
        pass


def get_arg(text: str) -> str:
    parts = (text or "").split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


def get_target_text(message: Message) -> str:
    arg = get_arg(message.text or "")
    if arg:
        return arg
    if message.reply_to_message:
        return message.reply_to_message.text or message.reply_to_message.caption or ""
    return ""


EN = "qwertyuiop[]asdfghjkl;'zxcvbnm,./QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>?"
RU = "йцукенгшщзхъфывапролджэячсмитьбю.ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,"


def switch_layout(text: str) -> str:
    return text.translate(str.maketrans(EN + RU, RU + EN))


def to_leet(text: str) -> str:
    m = {'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '5', 't': '7',
         'A': '4', 'E': '3', 'I': '1', 'O': '0', 'S': '5', 'T': '7',
         'l': '1', 'L': '1', 'b': '8', 'B': '8'}
    return ''.join(m.get(c, c) for c in text)


def to_kawaii(text: str) -> str:
    return text + random.choice([" (◕‿◕)", " (≧◡≦)", " (｡♥‿♥｡)", " ☆"])


def love_text(text: str) -> str:
    hearts = ["❤️", "💕", "💖", "💗"]
    return " ".join(w + random.choice(hearts) for w in text.split())


def cmd_name(text: str) -> str:
    if not text:
        return ""
    t = text.lower().strip()
    if t.startswith("."):
        return t[1:].split()[0]
    return ""


# ===== TEXT =====
@router.message(F.text.lower().startswith(".sw"))
@router.business_message(F.text.lower().startswith(".sw"))
async def cmd_sw(message: Message):
    text = get_target_text(message)
    if not text:
        await safe_edit(message, "Ответь на сообщение или напиши <code>.sw текст</code>")
        return
    await safe_edit(message, switch_layout(text), parse_mode=None)


@router.message(F.text.lower().startswith(".reverse"))
@router.business_message(F.text.lower().startswith(".reverse"))
async def cmd_reverse(message: Message):
    text = get_target_text(message)
    if not text:
        await safe_edit(message, "Нужен текст")
        return
    await safe_edit(message, text[::-1], parse_mode=None)


@router.message(F.text.lower().startswith(".upper"))
@router.business_message(F.text.lower().startswith(".upper"))
async def cmd_upper(message: Message):
    text = get_target_text(message)
    if text:
        await safe_edit(message, text.upper(), parse_mode=None)


@router.message(F.text.lower().startswith(".lower"))
@router.business_message(F.text.lower().startswith(".lower"))
async def cmd_lower(message: Message):
    text = get_target_text(message)
    if text:
        await safe_edit(message, text.lower(), parse_mode=None)


@router.message(F.text.lower().startswith(".count"))
@router.business_message(F.text.lower().startswith(".count"))
async def cmd_count(message: Message):
    text = get_target_text(message)
    if not text:
        await safe_edit(message, "Нужен текст")
        return
    await safe_edit(message, f"Символов: {len(text)}\nСлов: {len(text.split())}\nСтрок: {len(text.splitlines())}")


@router.message(F.text.lower().startswith(".leet"))
@router.business_message(F.text.lower().startswith(".leet"))
async def cmd_leet(message: Message):
    text = get_target_text(message)
    if text:
        await safe_edit(message, to_leet(text), parse_mode=None)


@router.message(F.text.lower().startswith(".kawaii"))
@router.business_message(F.text.lower().startswith(".kawaii"))
async def cmd_kawaii(message: Message):
    text = get_target_text(message)
    if text:
        await safe_edit(message, to_kawaii(text), parse_mode=None)


@router.message(F.text.lower().startswith(".love"))
@router.business_message(F.text.lower().startswith(".love"))
async def cmd_love(message: Message):
    text = get_target_text(message)
    if text:
        await safe_edit(message, love_text(text), parse_mode=None)


@router.message(F.text.lower().startswith(".say"))
@router.business_message(F.text.lower().startswith(".say"))
async def cmd_say(message: Message):
    text = get_arg(message.text or "")
    if text:
        await safe_edit(message, text, parse_mode=None)


@router.message(F.text.lower().startswith(".type"))
@router.business_message(F.text.lower().startswith(".type"))
async def cmd_type(message: Message):
    text = get_arg(message.text or "")
    if not text:
        await safe_edit(message, "Использование: <code>.type текст</code>")
        return
    current = ""
    for ch in text:
        current += ch
        try:
            await message.edit_text(current)
        except Exception:
            break
        await asyncio.sleep(0.1)


@router.message(F.text.lower().startswith(".repeat"))
@router.business_message(F.text.lower().startswith(".repeat"))
async def cmd_repeat(message: Message):
    arg = get_arg(message.text or "")
    if not arg:
        await safe_edit(message, "Использование: <code>.repeat 3 текст</code>")
        return
    parts = arg.split(maxsplit=1)
    try:
        n = min(int(parts[0]), 8)
        text = parts[1] if len(parts) > 1 else "🔄"
    except Exception:
        await safe_edit(message, "Первым должно быть число")
        return
    await safe_edit(message, text)
    for _ in range(n - 1):
        await message.answer(text)
        await asyncio.sleep(0.2)


# ===== RANDOM =====
@router.message(F.text.lower() == ".random")
@router.business_message(F.text.lower() == ".random")
async def cmd_random(message: Message):
    await safe_edit(message, f"🎲 {random.choice(['Да', 'Нет', 'Возможно', 'Точно да', 'Точно нет', '50/50'])}")


@router.message(F.text.lower().startswith(".choose"))
@router.business_message(F.text.lower().startswith(".choose"))
async def cmd_choose(message: Message):
    arg = get_arg(message.text or "")
    if not arg or "|" not in arg:
        await safe_edit(message, "Использование: <code>.choose a | b | c</code>")
        return
    options = [o.strip() for o in arg.split("|") if o.strip()]
    if len(options) < 2:
        await safe_edit(message, "Нужно минимум 2 варианта")
        return
    await safe_edit(message, f"🎯 <b>{random.choice(options)}</b>")


@router.message(F.text.lower().in_({".coin", ".flip"}))
@router.business_message(F.text.lower().in_({".coin", ".flip"}))
async def cmd_coin(message: Message):
    await safe_edit(message, f"🪙 {random.choice(['Орёл', 'Решка'])}")


@router.message(F.text.lower() == ".dice")
@router.business_message(F.text.lower() == ".dice")
async def cmd_dice(message: Message):
    try:
        await message.delete()
    except Exception:
        pass
    await message.answer_dice(emoji="🎲")


@router.message(F.text.lower().in_({".ball", ".8ball"}))
@router.business_message(F.text.lower().in_({".ball", ".8ball"}))
async def cmd_ball(message: Message):
    answers = [
        "Бесспорно", "Определённо да", "Да", "Вероятнее всего",
        "Хорошие перспективы", "Пока не ясно", "Спроси позже",
        "Даже не думай", "Мой ответ — нет", "Весьма сомнительно"
    ]
    await safe_edit(message, f"🎱 {random.choice(answers)}")


@router.message(F.text.lower() == ".password")
@router.business_message(F.text.lower() == ".password")
async def cmd_password(message: Message):
    chars = string.ascii_letters + string.digits + "!@#$%"
    pwd = ''.join(random.choice(chars) for _ in range(16))
    await safe_edit(message, f"🔐 <code>{pwd}</code>")


@router.message(F.text.lower() == ".uuid")
@router.business_message(F.text.lower() == ".uuid")
async def cmd_uuid(message: Message):
    await safe_edit(message, f"<code>{uuid4()}</code>")


@router.message(F.text.lower().startswith(".calc"))
@router.business_message(F.text.lower().startswith(".calc"))
async def cmd_calc(message: Message):
    expr = get_arg(message.text or "")
    if not expr:
        await safe_edit(message, "Использование: <code>.calc 2+2*3</code>")
        return
    if not all(c in "0123456789+-*/().% " for c in expr):
        await safe_edit(message, "Только цифры и +-*/()")
        return
    try:
        result = eval(expr, {"__builtins__": {}}, {})
        await safe_edit(message, f"🧮 {expr} = <b>{result}</b>")
    except Exception as e:
        await safe_edit(message, f"Ошибка: {e}")


# ===== SOCIAL =====
@router.message(F.text.lower() == ".ship")
@router.business_message(F.text.lower() == ".ship")
async def cmd_ship(message: Message):
    if not message.reply_to_message or not message.reply_to_message.from_user:
        await safe_edit(message, "Ответь на сообщение человека")
        return
    name1 = message.from_user.first_name
    name2 = message.reply_to_message.from_user.first_name
    percent = random.randint(0, 100)
    bar = "█" * (percent // 10) + "░" * (10 - percent // 10)
    await safe_edit(message, f"💘 {name1} + {name2}\n[{bar}] {percent}%")


@router.message(F.text.lower() == ".rate")
@router.business_message(F.text.lower() == ".rate")
async def cmd_rate(message: Message):
    target = "это" if message.reply_to_message else "тебя"
    await safe_edit(message, f"⭐ Оценка {target}: <b>{random.randint(1, 10)}/10</b>")


@router.message(F.text.lower() == ".howgay")
@router.business_message(F.text.lower() == ".howgay")
async def cmd_howgay(message: Message):
    await safe_edit(message, f"🌈 Гей-метр: <b>{random.randint(0, 100)}%</b>")


@router.message(F.text.lower() == ".pp")
@router.business_message(F.text.lower() == ".pp")
async def cmd_pp(message: Message):
    await safe_edit(message, f"🍆 8{'=' * random.randint(1, 20)}D")


@router.message(F.text.lower() == ".hug")
@router.business_message(F.text.lower() == ".hug")
async def cmd_hug(message: Message):
    target = message.reply_to_message.from_user.first_name if message.reply_to_message and message.reply_to_message.from_user else "себя"
    await safe_edit(message, f"🤗 {message.from_user.first_name} обнял(а) {target}")


@router.message(F.text.lower() == ".kiss")
@router.business_message(F.text.lower() == ".kiss")
async def cmd_kiss(message: Message):
    target = message.reply_to_message.from_user.first_name if message.reply_to_message and message.reply_to_message.from_user else "воздух"
    await safe_edit(message, f"😘 {message.from_user.first_name} поцеловал(а) {target}")


@router.message(F.text.lower() == ".pat")
@router.business_message(F.text.lower() == ".pat")
async def cmd_pat(message: Message):
    target = message.reply_to_message.from_user.first_name if message.reply_to_message and message.reply_to_message.from_user else "себя"
    await safe_edit(message, f"👋 {message.from_user.first_name} погладил(а) {target}")


@router.message(F.text.lower() == ".slap")
@router.business_message(F.text.lower() == ".slap")
async def cmd_slap(message: Message):
    if not message.reply_to_message:
        await safe_edit(message, "Ответь на сообщение")
        return
    target = message.reply_to_message.from_user.first_name if message.reply_to_message.from_user else "кого-то"
    await safe_edit(message, f"👋 {message.from_user.first_name} дал(а) пощёчину {target}")


@router.message(F.text.lower() == ".kill")
@router.business_message(F.text.lower() == ".kill")
async def cmd_kill(message: Message):
    if not message.reply_to_message:
        await safe_edit(message, "Ответь на сообщение")
        return
    victim = message.reply_to_message.from_user.first_name if message.reply_to_message.from_user else "жертву"
    await safe_edit(message, f"💀 {message.from_user.first_name} {random.choice(['убил взглядом', 'забанил', 'удалил'])} {victim}")


# ===== MEMES =====
@router.message(F.text.lower() == ".table")
@router.business_message(F.text.lower() == ".table")
async def cmd_table(message: Message):
    await safe_edit(message, "(╯°□°)╯︵ ┻━┻", parse_mode=None)

@router.message(F.text.lower() == ".untable")
@router.business_message(F.text.lower() == ".untable")
async def cmd_untable(message: Message):
    await safe_edit(message, "┬─┬ ノ( ゜-゜ノ)", parse_mode=None)

@router.message(F.text.lower() == ".shrug")
@router.business_message(F.text.lower() == ".shrug")
async def cmd_shrug(message: Message):
    await safe_edit(message, "¯\\_(ツ)_/¯", parse_mode=None)

@router.message(F.text.lower() == ".lenny")
@router.business_message(F.text.lower() == ".lenny")
async def cmd_lenny(message: Message):
    await safe_edit(message, "( ͡° 倾 ͡°)", parse_mode=None)

@router.message(F.text.lower() == ".magic")
@router.business_message(F.text.lower() == ".magic")
async def cmd_magic(message: Message):
    await safe_edit(message, "(∩｀-´)⊃━☆ﾟ.*･｡ﾟ", parse_mode=None)

@router.message(F.text.lower() == ".fight")
@router.business_message(F.text.lower() == ".fight")
async def cmd_fight(message: Message):
    await safe_edit(message, "(ง'̀-'́)ง", parse_mode=None)

@router.message(F.text.lower() == ".joke")
@router.business_message(F.text.lower() == ".joke")
async def cmd_joke(message: Message):
    jokes = [
        "Программист ставит будильник на 10:00, 10:10, 10:20... чтобы поймать исключение.",
        "— Почему программисты путают Хэллоуин и Рождество? — Oct 31 == Dec 25.",
        "Баг — это не ошибка, это неожиданная фича.",
        "В мире есть 10 типов людей: те, кто понимает двоичный код, и те, кто нет.",
    ]
    await safe_edit(message, random.choice(jokes), parse_mode=None)

@router.message(F.text.lower() == ".quote")
@router.business_message(F.text.lower() == ".quote")
async def cmd_quote(message: Message):
    quotes = [
        "«Единственный способ делать великие дела — любить то, что ты делаешь.»",
        "«Лучший способ предсказать будущее — создать его.»",
        "«Не бойся совершенства — тебе его никогда не достичь.»",
    ]
    await safe_edit(message, random.choice(quotes), parse_mode=None)

@router.message(F.text.lower() == ".fact")
@router.business_message(F.text.lower() == ".fact")
async def cmd_fact(message: Message):
    facts = [
        "Осьминоги имеют три сердца.",
        "Мёд никогда не портится.",
        "У бананов больше генов, чем у человека.",
    ]
    await safe_edit(message, f"📚 {random.choice(facts)}")


# ===== INFO =====
@router.message(F.text.lower().in_({".dox", ".info"}))
@router.business_message(F.text.lower().in_({".dox", ".info"}))
async def cmd_dox(message: Message):
    u = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    if not u:
        await safe_edit(message, "Нет данных")
        return
    text = (
        f"👤 <b>Инфо</b>\n\n"
        f"ID: <code>{u.id}</code>\n"
        f"Имя: {u.full_name}\n"
        f"Юзернейм: @{u.username or 'нет'}\n"
        f"Язык: {u.language_code or '?'}\n"
        f"Premium: {'✅' if u.is_premium else '❌'}\n"
        f"Бот: {'✅' if u.is_bot else '❌'}"
    )
    await safe_edit(message, text)


@router.message(F.text.lower() == ".whoami")
@router.business_message(F.text.lower() == ".whoami")
async def cmd_whoami(message: Message):
    u = message.from_user
    await safe_edit(
        message,
        f"👤 <b>Ты</b>\n\n"
        f"ID: <code>{u.id}</code>\n"
        f"Имя: {u.full_name}\n"
        f"Юзернейм: @{u.username or 'нет'}\n"
        f"Premium: {'✅' if u.is_premium else '❌'}"
    )


@router.message(F.text.lower() == ".server")
@router.business_message(F.text.lower() == ".server")
async def cmd_server(message: Message):
    await safe_edit(
        message,
        f"🖥 Python {platform.python_version()}\n"
        f"{platform.system()} {platform.release()}"
    )


# Неизвестные команды — только если команда реально неизвестна
@router.message(F.text.regexp(r"^\.\w+"))
@router.business_message(F.text.regexp(r"^\.\w+"))
async def unknown_dot(message: Message):
    name = cmd_name(message.text or "")
    if name in KNOWN:
        return  # уже обработано другим хендлером
    await safe_edit(
        message,
        f"Команда <code>.{html.escape(name)}</code> не найдена.\nНапиши <code>.help</code>"
    )
