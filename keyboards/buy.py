from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
from config import ADMIN_IDS
from core.constants import KIND_NAMES
from core.utils import format_prices

def buy_categories_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Все товары",callback_data="buy:cat:all")],
        [InlineKeyboardButton(text="🪪 Аккаунты",callback_data="buy:cat:account"),InlineKeyboardButton(text="🪙 Валюта",callback_data="buy:cat:currency")],
        [InlineKeyboardButton(text="🛠 Услуги",callback_data="buy:cat:service"),InlineKeyboardButton(text="📦 Другое",callback_data="buy:cat:other")],
        [InlineKeyboardButton(text="🔎 Поиск",callback_data="buy:search"),InlineKeyboardButton(text="❤️ Избранное",callback_data="favorites")],
        [InlineKeyboardButton(text="🔙 Главное меню",callback_data="back_menu")]
    ])

def product_list_kb(ads,page=0,total=0,kind="all",search=""):
    rows=[]
    for a in ads:
        rows.append([InlineKeyboardButton(text=f"#{a['product_number']} • {KIND_NAMES.get(a['kind'],a['kind'])} • {format_prices(a)}",callback_data=f"product:{a['id']}")])
    nav=[]
    if page>0: nav.append(InlineKeyboardButton(text="◀️",callback_data=f"page:{kind}:{page-1}:{search}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{max(1,(total+9)//10)}",callback_data="noop"))
    if (page+1)*10<total: nav.append(InlineKeyboardButton(text="▶️",callback_data=f"page:{kind}:{page+1}:{search}"))
    if nav: rows.append(nav)
    rows.append([InlineKeyboardButton(text="🔎 Поиск",callback_data="buy:search"),InlineKeyboardButton(text="📂 Категории",callback_data="buy")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def product_kb(ad_id,seller_id,viewer_id,favorite=False):
    rows=[
        [InlineKeyboardButton(text="🛒 Купить через бота",callback_data=f"sm_order:ad:{ad_id}")],
        [InlineKeyboardButton(text="👤 Связаться с продавцом",callback_data=f"contact:{ad_id}")],
        [InlineKeyboardButton(text=("❤️ Убрать из избранного" if favorite else "🤍 В избранное"),callback_data=f"favorite:{ad_id}")],
        [InlineKeyboardButton(text="⚠️ Пожаловаться",callback_data=f"report:{ad_id}")]
    ]
    if viewer_id==seller_id or viewer_id in ADMIN_IDS:
        rows.append([InlineKeyboardButton(text="💰 Отметить проданным",callback_data=f"mark_sold:{ad_id}")])
    rows.append([InlineKeyboardButton(text="🔙 Назад",callback_data="buy")])
    return InlineKeyboardMarkup(inline_keyboard=rows)