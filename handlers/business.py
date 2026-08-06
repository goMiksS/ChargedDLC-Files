import os
from pathlib import Path
from uuid import uuid4
from aiogram import Router, Bot
from aiogram.types import Message, BusinessMessagesDeleted, BusinessConnection, FSInputFile

from config import MEDIA_DIR
from db.database import (
    register_user, save_message, get_saved_message, mark_deleted,
    save_edit, get_user_settings
)

router = Router()
Path(MEDIA_DIR).mkdir(exist_ok=True)


async def get_owner_id_from_connection(bot: Bot, business_connection_id: str) -> int | None:
    try:
        conn = await bot.get_business_connection(business_connection_id)
        return conn.user.id
    except Exception:
        return None


async def download_media_safe(bot: Bot, file_id: str, ext: str) -> str | None:
    """Универсальное безопасное скачивание файлов любого размера (>20MB)"""
    file_name = f"{uuid4()}.{ext}"
    file_path = str(Path(MEDIA_DIR) / file_name)
    try:
        file = await bot.get_file(file_id)
        # Если API локальный, путь может быть сразу абсолютным физ. файлом на диске
        if file.file_path and os.path.isabs(file.file_path) and os.path.exists(file.file_path):
            os.replace(file.file_path, file_path)
        else:
            await bot.download_file(file.file_path, file_path)
        return file_path
    except Exception as e:
        print(f"Error downloading file {file_id}: {e}")
        return None


@router.business_connection()
async def on_business_connection(event: BusinessConnection, bot: Bot):
    user = event.user
    if event.is_enabled:
        await register_user(user.id, user.username or "", user.full_name or "", event.id)
        try:
            await bot.send_message(
                user.id,
                "✅ <b>Бот успешно подключён!</b>\n\n"
                "Теперь я буду сохранять сообщения в твоих чатах (включая файлы > 20 MB).\n"
                "Удаления и правки будут приходить сюда.\n\n"
                "Напиши .help чтобы увидеть все команды.",
                parse_mode="HTML"
            )
        except Exception:
            pass


@router.business_message()
async def on_business_message(message: Message, bot: Bot):
    if not message.business_connection_id:
        return

    owner_id = await get_owner_id_from_connection(bot, message.business_connection_id)
    if not owner_id:
        return

    await register_user(owner_id, "", "", message.business_connection_id)

    settings = await get_user_settings(owner_id)
    save_own = settings.get("save_own", True)
    save_media = settings.get("save_media", True)

    if message.from_user and message.from_user.id == owner_id and not save_own:
        return

    content_type = "text"
    text = message.text
    caption = message.caption
    file_id = None
    file_path = None
    raw = message.model_dump_json()

    if message.reply_to_message:
        reply = message.reply_to_message
        if reply.has_protected_content or getattr(reply, "has_media_spoiler", False):
            await save_protected_media(bot, owner_id, reply)

    if message.photo and save_media:
        content_type = "photo"
        photo = message.photo[-1]
        file_id = photo.file_id
        file_path = await download_media_safe(bot, file_id, "jpg")
    elif message.video and save_media:
        content_type = "video"
        file_id = message.video.file_id
        file_path = await download_media_safe(bot, file_id, "mp4")
    elif message.video_note and save_media:
        content_type = "video_note"
        file_id = message.video_note.file_id
        file_path = await download_media_safe(bot, file_id, "mp4")
    elif message.voice and save_media:
        content_type = "voice"
        file_id = message.voice.file_id
        file_path = await download_media_safe(bot, file_id, "ogg")
    elif message.audio and save_media:
        content_type = "audio"
        file_id = message.audio.file_id
        file_path = await download_media_safe(bot, file_id, "mp3")
    elif message.document and save_media:
        content_type = "document"
        file_id = message.document.file_id
        ext = (message.document.file_name or "file").split(".")[-1][:8]
        file_path = await download_media_safe(bot, file_id, ext)
    elif message.sticker:
        content_type = "sticker"
        file_id = message.sticker.file_id
    elif message.animation and save_media:
        content_type = "animation"
        file_id = message.animation.file_id

    from_user = message.from_user
    await save_message(
        user_id=owner_id,
        chat_id=message.chat.id,
        message_id=message.message_id,
        from_user_id=from_user.id if from_user else 0,
        from_username=from_user.username if from_user else "",
        from_name=from_user.full_name if from_user else "Unknown",
        content_type=content_type,
        text=text,
        caption=caption,
        file_id=file_id,
        file_path=file_path,
        raw_json=raw
    )


async def save_protected_media(bot: Bot, owner_id: int, msg: Message):
    try:
        if msg.photo:
            path = await download_media_safe(bot, msg.photo[-1].file_id, "jpg")
            if path:
                await bot.send_photo(owner_id, FSInputFile(path), caption="🔒 Сохранено protected/view-once фото")
        elif msg.video:
            path = await download_media_safe(bot, msg.video.file_id, "mp4")
            if path:
                await bot.send_video(owner_id, FSInputFile(path), caption="🔒 Сохранено protected/view-once видео")
        elif msg.video_note:
            path = await download_media_safe(bot, msg.video_note.file_id, "mp4")
            if path:
                await bot.send_video_note(owner_id, FSInputFile(path))
                await bot.send_message(owner_id, "🔒 Сохранён protected кружочек")
        elif msg.voice:
            path = await download_media_safe(bot, msg.voice.file_id, "ogg")
            if path:
                await bot.send_voice(owner_id, FSInputFile(path), caption="🔒 Сохранено protected голосовое")
    except Exception as e:
        try:
            await bot.send_message(owner_id, f"Не удалось сохранить protected медиа: {e}")
        except Exception:
            pass


@router.edited_business_message()
async def on_edited_business_message(message: Message, bot: Bot):
    if not message.business_connection_id:
        return
    owner_id = await get_owner_id_from_connection(bot, message.business_connection_id)
    if not owner_id:
        return

    settings = await get_user_settings(owner_id)
    old = await get_saved_message(owner_id, message.chat.id, message.message_id)
    old_text = (old["text"] or old["caption"] or "") if old else "—"
    new_text = message.text or message.caption or "—"

    await save_edit(owner_id, message.chat.id, message.message_id, old_text, new_text)

    if settings.get("notify_edit", True):
        from_user = message.from_user
        name = from_user.full_name if from_user else "Кто-то"
        uname = f"@{from_user.username}" if from_user and from_user.username else ""
        text = (
            f"✏️ <b>Сообщение отредактировано</b>\n"
            f"От: {name} {uname}\n"
            f"Чат ID: <code>{message.chat.id}</code>\n\n"
            f"<b>Было:</b>\n{old_text[:500]}\n\n"
            f"<b>Стало:</b>\n{new_text[:500]}"
        )
        try:
            await bot.send_message(owner_id, text, parse_mode="HTML")
        except Exception:
            pass


@router.deleted_business_messages()
async def on_deleted_business_messages(event: BusinessMessagesDeleted, bot: Bot):
    owner_id = await get_owner_id_from_connection(bot, event.business_connection_id)
    if not owner_id:
        return

    settings = await get_user_settings(owner_id)
    await mark_deleted(owner_id, event.chat.id, event.message_ids)

    if not settings.get("notify_delete", True):
        return

    for mid in event.message_ids:
        saved = await get_saved_message(owner_id, event.chat.id, mid)
        if not saved:
            continue

        name = saved["from_name"] or "Кто-то"
        uname = f"@{saved['from_username']}" if saved["from_username"] else ""
        header = (
            f"🗑 <b>Сообщение удалено</b>\n"
            f"От: {name} {uname}\n"
            f"Чат ID: <code>{event.chat.id}</code>\n"
            f"Тип: {saved['content_type']}\n"
        )

        try:
            if saved["content_type"] == "text":
                body = f"{header}\n<code>{saved['text'] or ''}</code>"
                await bot.send_message(owner_id, body, parse_mode="HTML")
            elif saved["content_type"] == "photo" and saved["file_path"] and Path(saved["file_path"]).exists():
                caption = f"{header}\n{saved['caption'] or ''}"
                await bot.send_photo(owner_id, FSInputFile(saved["file_path"]), caption=caption, parse_mode="HTML")
            elif saved["content_type"] == "video" and saved["file_path"] and Path(saved["file_path"]).exists():
                caption = f"{header}\n{saved['caption'] or ''}"
                await bot.send_video(owner_id, FSInputFile(saved["file_path"]), caption=caption, parse_mode="HTML")
            elif saved["content_type"] == "video_note" and saved["file_path"] and Path(saved["file_path"]).exists():
                await bot.send_video_note(owner_id, FSInputFile(saved["file_path"]))
                await bot.send_message(owner_id, header, parse_mode="HTML")
            elif saved["content_type"] in ("voice", "audio") and saved["file_path"] and Path(saved["file_path"]).exists():
                await bot.send_voice(owner_id, FSInputFile(saved["file_path"]), caption=header, parse_mode="HTML")
            elif saved["content_type"] == "document" and saved["file_path"] and Path(saved["file_path"]).exists():
                await bot.send_document(owner_id, FSInputFile(saved["file_path"]), caption=header, parse_mode="HTML")
            else:
                body = f"{header}\n{saved['text'] or saved['caption'] or saved['content_type']}"
                await bot.send_message(owner_id, body, parse_mode="HTML")
        except Exception as e:
            try:
                await bot.send_message(owner_id, f"{header}\n(ошибка отправки медиа: {e})", parse_mode="HTML")
            except Exception:
                pass
