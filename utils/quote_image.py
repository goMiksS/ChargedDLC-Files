"""Генерация картинки-цитаты"""
import io
import textwrap
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None


def _font(size: int):
    # Стандартные пути шрифтов на Linux (Debian/Ubuntu/Render)
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def make_quote_image(text: str, username: str, width: int = 800, min_height: int = 400) -> io.BytesIO:
    if Image is None:
        raise RuntimeError("Pillow not installed. Install it via 'pip install Pillow'")

    # Цветовая палитра
    bg = (28, 28, 36)
    accent = (120, 180, 255)
    text_color = (240, 240, 245)
    name_color = (160, 160, 175)

    font_quote = _font(32)
    font_name = _font(22)
    font_big = _font(72)

    # Форматирование и перенос текста (ограничение до 500 символов)
    clean_text = text.strip()[:500]
    wrapped_text = textwrap.fill(clean_text, width=38)

    # Временный холст для расчета размеров вывода
    tmp_img = Image.new("RGB", (1, 1))
    tmp_draw = ImageDraw.Draw(tmp_img)
    
    # Расчет высоты блока текста
    text_bbox = tmp_draw.multiline_textbbox((0, 0), wrapped_text, font=font_quote, spacing=12)
    text_height = text_bbox[3] - text_bbox[1]

    # Динамический расчет высоты холста (текст + отступы под кавычку и ник)
    calculated_height = 110 + text_height + 80
    height = max(min_height, calculated_height)

    # Итоговый холст
    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    # Декоративная акцентная полоса слева
    draw.rectangle([0, 0, 8, height], fill=accent)

    # Большая кавычка
    draw.text((35, 20), "“", font=font_big, fill=accent)

    # Отрисовка текста цитаты
    draw.multiline_text((50, 105), wrapped_text, font=font_quote, fill=text_color, spacing=12)

    # Никнейм автора цитаты в правом нижнем углу
    name = f"@{username}" if username and not username.startswith("@") else (username or "unknown")
    name_bbox = draw.textbbox((0, 0), name, font=font_name)
    tw = name_bbox[2] - name_bbox[0]
    th = name_bbox[3] - name_bbox[1]

    x = width - tw - 40
    y = height - th - 35
    draw.text((x, y), name, font=font_name, fill=name_color)

    # Сохранение в буфер байтов (для отправки в Telegram)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
