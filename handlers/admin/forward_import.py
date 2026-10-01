import logging

from aiogram import Router, F
from aiogram.types import Message

from config import ADMIN_IDS
from db.ads import (
    create_ad,
    set_published,
    update_product_number,
    get_ad,
)
from db.channel_import import (
    imported_ad_id,
    save_imported_ad,
)
from handlers.channel_import import _parse


router = Router()


@router.message(
    F.forward_origin
)
async def import_forwarded_channel_post(message: Message):
    # Только администраторы
    if not message.from_user:
        return

    if message.from_user.id not in ADMIN_IDS:
        return

    origin = message.forward_origin

    # Нам нужны именно пересланные сообщения из канала
    if not origin:
        return

    # В aiogram 3 для пересылки из канала используется
    # MessageOriginChannel.
    source_chat = getattr(origin, "chat", None)
    source_message_id = getattr(origin, "message_id", None)

    if not source_chat or not source_message_id:
        return

    # Защита от повторного импорта
    existing = await imported_ad_id(
        source_chat.id,
        source_message_id,
    )

    if existing:
        await message.answer(
            f"⚠️ Этот пост уже добавлен как товар #{existing}."
        )
        return

    # Берём текст / подпись пересланного поста
    raw_text = message.text or message.caption or ""

    parsed = _parse(raw_text)

    if not parsed:
        await message.answer(
            "❌ Не удалось распознать объявление.\n\n"
            "Проверь, что ты переслал обычный пост товара "
            "в формате канала."
        )
        return

    # Продавец берётся из самого текста объявления
    username = parsed["seller"].lstrip("@")

    # Медиа пересланного сообщения
    media = []

    if message.photo:
        media.append(
            {
                "type": "photo",
                "file_id": message.photo[-1].file_id,
            }
        )

    elif message.video:
        media.append(
            {
                "type": "video",
                "file_id": message.video.file_id,
            }
        )

    # Если у сообщения есть username канала —
    # сохраняем ссылку на исходный пост.
    if source_chat.username:
        contact = (
            f"https://t.me/"
            f"{source_chat.username}/"
            f"{source_message_id}"
        )
    else:
        contact = str(source_message_id)

    data = {
        "kind": parsed["kind"],
        "game": parsed["game"],
        "description": parsed["description"],
        "contact": contact,
        "payment": parsed["payment"],
        "price_rub": parsed["price_rub"],
        "price_stars": parsed["price_stars"],
        "tokens": parsed["tokens"],
        "media": media,
    }

    try:
        # Создаём объявление
        ad_id = await create_ad(
            data,
            0,
            username,
        )

        # Сохраняем оригинальный номер товара
        await update_product_number(
            ad_id,
            parsed["source_product_number"],
        )

        ad = await get_ad(ad_id)

        if not ad:
            await message.answer(
                "❌ Объявление создалось, "
                "но не удалось получить его из базы."
            )
            return

        # Делаем товар опубликованным в каталоге.
        # None означает, что отдельного поста в публичном
        # канале для этого объявления нет.
        await set_published(
            ad_id,
            None,
        )

        # Запоминаем исходный пост,
        # чтобы второй раз его не импортировать.
        saved = await save_imported_ad(
            source_chat.id,
            source_message_id,
            ad_id,
        )

        if not saved:
            logging.warning(
                "Forwarded channel post already imported: %s/%s",
                source_chat.id,
                source_message_id,
            )

            await message.answer(
                f"⚠️ Этот пост уже был импортирован."
            )
            return

        await message.answer(
            "✅ Объявление добавлено!\n\n"
            f"🆔 Товар: #{ad['product_number']}\n"
            f"🎮 Игра: {ad['game']}\n"
            f"💰 Цена: "
            f"{ad['price_rub']} ₽"
            + (
                f" / {ad['price_stars']} ⭐"
                if ad["price_stars"]
                else ""
            )
        )

        logging.info(
            "Admin %s imported forwarded channel post "
            "%s/%s as ad #%s",
            message.from_user.id,
            source_chat.id,
            source_message_id,
            ad_id,
        )

    except Exception:
        logging.exception(
            "Failed to import forwarded channel post"
        )

        await message.answer(
            "❌ Произошла ошибка при добавлении объявления."
        )