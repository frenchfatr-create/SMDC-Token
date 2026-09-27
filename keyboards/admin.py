from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton

def admin_kb(ad_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Одобрить",callback_data=f"approve:{ad_id}"),InlineKeyboardButton(text="❌ Отклонить",callback_data=f"reject:{ad_id}")],
        [InlineKeyboardButton(text="💰 Изменить цену",callback_data=f"price_edit:menu:{ad_id}"),InlineKeyboardButton(text="🔢 Номер товара",callback_data=f"product_number:menu:{ad_id}")],
        [InlineKeyboardButton(text="🖼 Заменить фото",callback_data=f"replace_photo:{ad_id}")],
    ])
def admin_panel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Заказы",callback_data="admin_orders"),InlineKeyboardButton(text="📦 Товары",callback_data="admin_products")],
        [InlineKeyboardButton(text="⭐ Рейтинг",callback_data="admin_rating"),InlineKeyboardButton(text="🖼 Водяной знак",callback_data="admin_watermark")],
        [InlineKeyboardButton(text="💳 Реквизиты",callback_data="admin_payment_details")],
        [InlineKeyboardButton(text="🔙 Главное меню",callback_data="back_menu")],
    ])
def watermark_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🖼 Установить",callback_data="watermark_set")],[InlineKeyboardButton(text="🗑 Удалить",callback_data="watermark_delete")],[InlineKeyboardButton(text="🔙 Админ-панель",callback_data="admin_panel")]])

def order_admin_kb(number):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Оплата подтверждена",callback_data=f"order:paid:{number}")],
        [InlineKeyboardButton(text="🎉 Заказ выполнен",callback_data=f"order:complete:{number}")],
        [InlineKeyboardButton(text="❌ Отклонить",callback_data=f"order:reject:{number}")],
    ])
