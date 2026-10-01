def admin_panel_kb(logs_on=False):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Заказы", callback_data="admin_orders"),
                InlineKeyboardButton(text="📦 Товары", callback_data="admin_products"),
            ],
            [
                InlineKeyboardButton(
                    text="📥 Импорт объявления",
                    callback_data="admin_import_ad"
                ),
            ],
            [
                InlineKeyboardButton(text="⭐ Рейтинг", callback_data="admin_rating"),
                InlineKeyboardButton(text="🖼 Водяной знак", callback_data="admin_watermark"),
            ],
            [
                InlineKeyboardButton(
                    text="💳 Реквизиты",
                    callback_data="admin_payment_details"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🚫 Блокировки",
                    callback_data="admin_blocks"
                ),
                InlineKeyboardButton(
                    text=f"📜 Логи: {'🟢' if logs_on else '🔴'}",
                    callback_data="admin_logs"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📊 Статистика",
                    callback_data="admin_stats"
                ),
                InlineKeyboardButton(
                    text="👤 Найти пользователя",
                    callback_data="admin_user"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🛠 Управление товаром",
                    callback_data="admin_product_manage"
                ),
                InlineKeyboardButton(
                    text="⚠️ Жалобы",
                    callback_data="admin_complaints"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Главное меню",
                    callback_data="back_menu"
                ),
            ],
        ]
    )