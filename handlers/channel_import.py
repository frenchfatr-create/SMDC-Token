import html
import logging
import re

from aiogram import Router, F
from aiogram.types import Message

from config import IMPORT_CHANNELS, PUBLIC_CHANNEL
from db.ads import create_ad, set_published, update_product_number, get_ad
from db.channel_import import imported_ad_id, save_imported_ad
from db.users import save_user


router = Router()
bot_ref = None


def set_bot(bot):
    global bot_ref
    bot_ref = bot


def _strip_html(value):
    value = value or ""
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"</p>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    return html.unescape(value).strip()


def _channels():
    return {
        item.strip()
        for item in (IMPORT_CHANNELS or "").split(",")
        if item.strip()
    }


def _channel_allowed(message):
    allowed = _channels()
    if not allowed:
        return False

    username = f"@{message.chat.username}" if message.chat.username else ""
    chat_id = str(message.chat.id)

    return chat_id in allowed or username in allowed or (
        username and username.lstrip("@") in allowed
    )


def _is_own_bot_post(message):
    if not bot_ref:
        return False

    if message.from_user and message.from_user.id == bot_ref.id:
        return True

    # Дополнительная защита от повторного импорта
    # стандартных постов, которые сам бот публикует.
    text = _strip_html(message.text or message.caption or "")
    return "🔎Ссылка на пост:" in text or "🔎 Ссылка на пост:" in text


def _parse(text):
    clean = _strip_html(text)
    lines = [line.strip() for line in clean.splitlines()]

    # 📦Товар #80 — Учётная запись 🪪
    m = re.search(
        r"Товар\s*#(\d+)\s*[—-]\s*(.+?)(?:\s+[🪪🪙🛠📦])?\s*$",
        clean,
        flags=re.M,
    )
    if not m:
        return None

    source_product_number = int(m.group(1))
    kind_name = m.group(2).strip().lower()

    kind_map = {
        "учётная запись": "account",
        "учетная запись": "account",
        "валюта": "currency",
        "услуга": "service",
        "другое": "other",
    }

    kind = kind_map.get(kind_name, "other")

    def field(pattern):
        match = re.search(pattern, clean, flags=re.I | re.M)
        return match.group(1).strip() if match else ""

    game = field(r"Игра:\s*(.+)")
    status = field(r"Статус:\s*(.+)")
    price = field(r"Цена:\s*(.+)")
    payment_text = field(r"Способ оплаты:\s*(.+)")
    seller = field(r"Продавец(?:\s*\([^)]*\))?:\s*(@?[A-Za-z0-9_]+)")
    description = field(
        r"Информация о товаре:\s*(.+?)(?=\n\s*🔎|\Z)"
    )

    if not game or not price or not description:
        return None

    if status and status.upper() not in (
        "НЕ ПРОДАН",
        "НЕ ПРОДАН.",
    ):
        # Не импортируем уже проданные/снятые товары.
        return None

    rub = 0
    stars = 0

    rub_match = re.search(
        r"(\d+(?:[.,]\d+)?)\s*₽",
        price,
    )
    stars_match = re.search(
        r"(\d+)\s*⭐",
        price,
    )

    if rub_match:
        rub = float(rub_match.group(1).replace(",", "."))

    if stars_match:
        stars = int(stars_match.group(1))

    if rub > 0 and stars > 0:
        payment = "both"
    elif stars > 0:
        payment = "stars"
    elif rub > 0:
        payment = "card"
    else:
        return None

    token_match = re.search(
        r"Количество:\s*(\d+)\s*токен",
        clean,
        flags=re.I,
    )
    tokens = int(token_match.group(1)) if token_match else 0

    return {
        "source_product_number": source_product_number,
        "kind": kind,
        "game": game[:100],
        "description": description[:3000],
        "contact": "",
        "payment": payment,
        "price_rub": rub,
        "price_stars": stars,
        "tokens": tokens,
        "seller": seller,
    }


def _is_public_channel(message):
    configured = (PUBLIC_CHANNEL or "").strip()

    if not configured:
        return False

    if str(message.chat.id) == configured:
        return True

    username = (
        f"@{message.chat.username}"
        if message.chat.username
        else ""
    )

    return username == configured or username.lstrip("@") == configured.lstrip("@")


@router.channel_post()
async def import_channel_post(message: Message):
    if not _channel_allowed(message):
        return

    if _is_own_bot_post(message):
        return

    # Не импортируем повторно один и тот же Telegram-пост.
    existing = await imported_ad_id(
        message.chat.id,
        message.message_id,
    )

    if existing:
        return

    raw_text = message.text or message.caption or ""
    parsed = _parse(raw_text)

    if not parsed:
        return

    username = parsed["seller"].lstrip("@")

    # Если в посте нет username продавца, используем
    # автора поста, если Telegram его предоставляет.
    if not username and message.from_user:
        username = message.from_user.username or ""

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

    # Для импортированного товара контакт ведёт
    # обратно на исходный пост.
    contact = (
        f"https://t.me/{message.chat.username}/{message.message_id}"
        if message.chat.username
        else str(message.message_id)
    )

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
        ad_id = await create_ad(
            data,
            0,
            username,
        )

        # Сохраняем исходный номер товара, если он
        # свободен. Если уже занят — остаётся новый ID.
        await update_product_number(
            ad_id,
            parsed["source_product_number"],
        )

        ad = await get_ad(ad_id)

        if not ad:
            return

        # Если источник — PUBLIC_CHANNEL, сохраняем
        # message_id как published_message_id, чтобы
        # существующая система могла редактировать пост.
        if _is_public_channel(message):
            await set_published(
                ad_id,
                message.message_id,
            )
        else:
            await set_published(
                ad_id,
                None,
            )

        saved = await save_imported_ad(
            message.chat.id,
            message.message_id,
            ad_id,
        )

        if not saved:
            logging.warning(
                "Channel post #%s was already imported",
                message.message_id,
            )
            return

        logging.info(
            "Imported channel post %s/%s as ad #%s",
            message.chat.id,
            message.message_id,
            ad_id,
        )

    except Exception:
        logging.exception(
            "Failed to import channel post %s/%s",
            message.chat.id,
            message.message_id,
        )
