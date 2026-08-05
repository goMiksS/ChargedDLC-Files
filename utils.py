import re
from datetime import datetime

def format_date(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%d.%m.%Y %H:%M:%S")

def truncate_text(text, length=100):
    if not text:
        return ""
    return text[:length] + "..." if len(text) > length else text

def escape_markdown(text):
    """Экранирование спецсимволов для Telegram Markdown"""
    if not text:
        return ""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def extract_mentions(text):
    """Извлекает упоминания @username из текста"""
    if not text:
        return []
    return re.findall(r'@(\w+)', text)

def is_command(text):
    return text and text.startswith('/')
