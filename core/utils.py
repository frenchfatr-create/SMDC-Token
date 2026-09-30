from html import escape
from config import PUBLIC_CHANNEL_URL
from core.constants import KIND_NAMES, KIND_EMOJI, PAY_NAMES


def format_rub(price):
    v = float(price or 0)
    return f"{v:.0f} ₽" if v.is_integer() else f"{v:.2f} ₽"


def format_stars(stars):
    return f"{int(stars or 0)} ⭐"


def format_prices(ad):
    rub = float(ad["price_rub"] if "price_rub" in ad.keys() else ad["price"] or 0)
    stars = int(ad["price_stars"] if "price_stars" in ad.keys() else 0)
    payment = ad["payment"]
    if payment == "card":
        return format_rub(rub)
    if payment == "stars":
        return format_stars(stars)
    if rub and stars:
        return f"{format_rub(rub)} / {format_stars(stars)}"
    if rub:
        return format_rub(rub)
    if stars:
        return format_stars(stars)
    return "Цена не указана"


def format_price(price):
    return format_rub(price)


def rating_text(rating):
    return f"{float(rating):.1f}".replace(".", ",")


def seller_label(ad):
    u = (ad["username"] or "").strip()
    return "@" + u.lstrip("@") if u else "не указан"


def make_post_link(channel, message_id):
    if PUBLIC_CHANNEL_URL:
        return f"{PUBLIC_CHANNEL_URL.rstrip('/')}/{message_id}"
    if channel.startswith("@"):
        return f"https://t.me/{channel[1:]}/{message_id}"
    return None


def moderation_text(ad, media_count):
    tokens = int(ad["tokens"] or 0) if "tokens" in ad.keys() else 0
    token_line = f"🪙 <b>Токены:</b> {tokens}\n" if tokens else ""
    return (
        f"🆕 <b>НОВАЯ ЗАЯВКА • ТОВАР #{ad['product_number']}</b>\n\n"
        f"👤 <b>Продавец:</b> {escape(seller_label(ad))}\n"
        f"├ ID: <code>{ad['user_id']}</code>\n"
        f"└ Контакт: {escape(ad['contact'])}\n\n"
        f"📦 <b>Товар:</b> {escape(KIND_NAMES.get(ad['kind'], ad['kind']))}\n"
        f"🎮 <b>Игра:</b> {escape(ad['game'])}\n"
        f"{token_line}"
        f"📝 <b>Описание:</b> {escape(ad['description'])}\n"
        f"💰 <b>Цена:</b> {format_prices(ad)}\n"
        f"💳 <b>Оплата:</b> {escape(PAY_NAMES.get(ad['payment'], ad['payment']))}\n"
        f"📸 <b>Медиа:</b> {media_count}\n\nВыберите действие:"
    )


def channel_post_text(ad, rating, status_text="Не продан"):
    tokens = int(ad["tokens"] or 0) if "tokens" in ad.keys() else 0
    token_line = f"🪙<b>Количество:</b> {tokens} токенов\n" if tokens else ""
    return (
        f"📦<b>Товар #{ad['product_number']} — {escape(KIND_NAMES.get(ad['kind'], ad['kind']))} {KIND_EMOJI.get(ad['kind'], '📦')}</b>\n"
        f"🎮<b>Игра:</b> {escape(ad['game'])}\n"
        f"👑<b>Статус:</b> {escape(status_text)}\n"
        f"{token_line}"
        f"💰<b>Цена:</b> {format_prices(ad)}\n"
        f"💳<b>Способ оплаты:</b> {escape(PAY_NAMES.get(ad['payment'], ad['payment']))}\n\n"
        f"👤<b>Продавец (SMDC {rating_text(rating)}/5):</b> {escape(seller_label(ad))}\n\n"
        f"📖<b>Информация о товаре:</b> {escape(ad['description'])}\n\n"
        f'🔎<b>Ссылка на пост:</b> <a href="https://t.me/smdcshop">SMDC</a>.'
    )
