from html import escape
from config import PUBLIC_CHANNEL_URL
from core.constants import KIND_NAMES,KIND_EMOJI,PAY_NAMES

def format_price(price):
    v=float(price); return f"{v:.0f} ₽" if v.is_integer() else f"{v:.2f} ₽"
def rating_text(rating): return f"{rating:.1f}".replace('.',',')
def seller_label(ad):
    u=(ad['username'] or '').strip(); return '@'+u.lstrip('@') if u else 'не указан'
def make_post_link(channel,message_id):
    if PUBLIC_CHANNEL_URL: return f"{PUBLIC_CHANNEL_URL.rstrip('/')}/{message_id}"
    if channel.startswith('@'): return f"https://t.me/{channel[1:]}/{message_id}"
    return None
def moderation_text(ad,media_count):
    return (f"🆕 <b>НОВАЯ ЗАЯВКА • ТОВАР #{ad['product_number']}</b>\n\n👤 <b>Продавец:</b> {escape(seller_label(ad))}\n├ ID: <code>{ad['user_id']}</code>\n└ Контакт: {escape(ad['contact'])}\n\n📦 <b>Товар:</b> {escape(KIND_NAMES.get(ad['kind'],ad['kind']))}\n🎮 <b>Игра:</b> {escape(ad['game'])}\n📝 <b>Описание:</b> {escape(ad['description'])}\n💰 <b>Цена:</b> {format_price(ad['price'])}\n💳 <b>Оплата:</b> {escape(PAY_NAMES.get(ad['payment'],ad['payment']))}\n📸 <b>Медиа:</b> {media_count}\n\nВыберите действие:")
def channel_post_text(ad,rating):
    return (f"📦<b>Товар #{ad['product_number']} — {escape(KIND_NAMES.get(ad['kind'],ad['kind']))} {KIND_EMOJI.get(ad['kind'],'📦')}</b>\n🎮<b>Игра:</b> {escape(ad['game'])}\n👑<b>Статус:</b> Не продан\n💰<b>Цена:</b> {format_price(ad['price'])}\n💳<b>Способ оплаты:</b> {escape(PAY_NAMES.get(ad['payment'],ad['payment']))}\n\n👤<b>Продавец (SMDC {rating_text(rating)}/5):</b> {escape(seller_label(ad))}\n\n📖<b>Информация о товаре:</b> {escape(ad['description'])}")
