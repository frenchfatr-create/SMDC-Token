from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
from config import ADMIN_IDS
from core.constants import KIND_NAMES
from core.utils import format_price
def buy_categories_kb(): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📦 Все товары",callback_data="buy:cat:all")],[InlineKeyboardButton(text="🪪 Аккаунты",callback_data="buy:cat:account"),InlineKeyboardButton(text="🪙 Валюта",callback_data="buy:cat:currency")],[InlineKeyboardButton(text="🛠 Услуги",callback_data="buy:cat:service"),InlineKeyboardButton(text="📦 Другое",callback_data="buy:cat:other")],[InlineKeyboardButton(text="🔎 Поиск",callback_data="buy:search")],[InlineKeyboardButton(text="🔙 Главное меню",callback_data="back_menu")]])
def product_list_kb(ads):
    rows=[]
    for a in ads: rows.append([InlineKeyboardButton(text=f"Товар #{a['product_number']} • {KIND_NAMES.get(a['kind'],a['kind'])} • {format_price(a['price'])}",callback_data=f"product:{a['id']}")])
    rows += [[InlineKeyboardButton(text="🔎 Поиск",callback_data="buy:search"),InlineKeyboardButton(text="📂 Категории",callback_data="buy")]]
    return InlineKeyboardMarkup(inline_keyboard=rows)
def product_kb(ad_id,seller_id,viewer_id):
    rows=[[InlineKeyboardButton(text="🛒 Купить через бота",callback_data=f"sm_order:ad:{ad_id}")],[InlineKeyboardButton(text="👤 Связаться с продавцом",callback_data=f"contact:{ad_id}")],[InlineKeyboardButton(text="💰 Изменить цену",callback_data=f"price_edit:menu:{ad_id}")]]
    if viewer_id==seller_id or viewer_id in ADMIN_IDS: rows.append([InlineKeyboardButton(text="💰 Отметить проданным",callback_data=f"mark_sold:{ad_id}")])
    rows.append([InlineKeyboardButton(text="🔙 Назад",callback_data="buy")]); return InlineKeyboardMarkup(inline_keyboard=rows)
