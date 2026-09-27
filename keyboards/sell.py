from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def kind_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪪 Аккаунт", callback_data="kind:account")],
        [InlineKeyboardButton(text="🪙 Валюта", callback_data="kind:currency")],
        [InlineKeyboardButton(text="🛠 Услуга", callback_data="kind:service")],
        [InlineKeyboardButton(text="📦 Другое", callback_data="kind:other")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_sell")],
    ])


def payment_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Карта / СБП", callback_data="pay:card")],
        [InlineKeyboardButton(text="⭐ Telegram Stars", callback_data="pay:stars")],
        [InlineKeyboardButton(text="💳 + ⭐ Оба варианта", callback_data="pay:both")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_sell")],
    ])