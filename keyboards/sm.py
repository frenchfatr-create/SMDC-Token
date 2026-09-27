from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton
def sm_menu(): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💰 Токены за ₽",callback_data="sm:rub")],[InlineKeyboardButton(text="⭐ Токены за Stars",callback_data="sm:stars")],[InlineKeyboardButton(text="📈 Накрутка акций",callback_data="sm:boost")],[InlineKeyboardButton(text="📦 Silver боксы",callback_data="sm:silver")],[InlineKeyboardButton(text="⛽️ Топливо",callback_data="sm:fuel")],[InlineKeyboardButton(text="🧾 Мои заказы",callback_data="my_orders")],[InlineKeyboardButton(text="🔙 Главное меню",callback_data="back_menu")]])
def pack_kb(prefix,items,custom=True):
    rows=[[InlineKeyboardButton(text=label,callback_data=f"{prefix}:{value}")] for label,value in items]
    if custom: rows.append([InlineKeyboardButton(text="✍️ Другое количество",callback_data=f"{prefix}:custom")])
    rows.append([InlineKeyboardButton(text="🔙 Назад",callback_data="sm_menu")]); return InlineKeyboardMarkup(inline_keyboard=rows)
def payment_kb(): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💳 Карта / СБП",callback_data="sm_pay:card")],[InlineKeyboardButton(text="⭐ Telegram Stars",callback_data="sm_pay:stars")],[InlineKeyboardButton(text="❌ Отмена",callback_data="sm_menu")]])
