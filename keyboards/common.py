from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
from config import ADMIN_IDS
def main_menu(user_id=None):
    rows=[[InlineKeyboardButton(text="🎮 Super Mechs",callback_data="sm_menu")],[InlineKeyboardButton(text="👥 Рефералы",callback_data="referral_info")],[InlineKeyboardButton(text="🛍 Купить",callback_data="buy"),InlineKeyboardButton(text="📦 Продать товар",callback_data="sell")],[InlineKeyboardButton(text="👤 Мой профиль",callback_data="profile"),InlineKeyboardButton(text="📋 Мои объявления",callback_data="my_ads")],[InlineKeyboardButton(text="🧾 Мои заказы",callback_data="my_orders")],[InlineKeyboardButton(text="ℹ️ Правила",callback_data="rules"),InlineKeyboardButton(text="🆘 Поддержка",callback_data="support")]]
    if user_id in ADMIN_IDS: rows.append([InlineKeyboardButton(text="⚙️ Админ-панель",callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
def cancel_kb(): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена",callback_data="cancel_sell")]])
