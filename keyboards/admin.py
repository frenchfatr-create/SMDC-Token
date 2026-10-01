from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def admin_kb(ad_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Одобрить",
                    callback_data=f"approve:{ad_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"reject:{ad_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💰 Цена",
                    callback_data=f"price_edit:menu:{ad_id}"
                ),
                InlineKeyboardButton(
                    text="🔢 Номер",
                    callback_data=f"product_number:menu:{ad_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🖼 Фото",
                    callback_data=f"replace_photo:{ad_id}"
                ),
            ],
        ]
    )


# =========================
# АДМИН-ПАНЕЛЬ — СТРАНИЦА 1
# =========================

def admin_panel_kb(logs_on=False):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Заказы",
                    callback_data="admin_orders"
                ),
                InlineKeyboardButton(
                    text="📦 Товары",
                    callback_data="admin_products"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⭐ Рейтинг",
                    callback_data="admin_rating"
                ),
                InlineKeyboardButton(
                    text="🖼 Водяной знак",
                    callback_data="admin_watermark"
                ),
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
                    text="➡️ Следующая страница",
                    callback_data="admin_panel_page:2"
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


# =========================
# АДМИН-ПАНЕЛЬ — СТРАНИЦА 2
# =========================

def admin_panel_page2_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📥 Импорт объявления",
                    callback_data="admin_import_ad"
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
                    text="⬅️ Предыдущая страница",
                    callback_data="admin_panel_page:1"
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


def watermark_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🖼 Установить",
                    callback_data="watermark_set"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить",
                    callback_data="watermark_delete"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Админ-панель",
                    callback_data="admin_panel"
                )
            ],
        ]
    )


def order_admin_kb(number, status="receipt_sent"):
    if status == "receipt_sent":
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💰 Оплата прошла",
                        callback_data=f"order:paid:{number}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Отклонить",
                        callback_data=f"order:reject:{number}"
                    )
                ],
            ]
        )

    if status == "paid":
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🎉 Заказ выполнен",
                        callback_data=f"order:complete:{number}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ Отклонить",
                        callback_data=f"order:reject:{number}"
                    )
                ],
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=[])


def product_manage_kb(product_number):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 Продано",
                    callback_data=f"manage:sold:{product_number}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Снять с продажи",
                    callback_data=f"manage:remove:{product_number}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Админ-панель",
                    callback_data="admin_panel"
                )
            ],
        ]
    )


def block_action_kb(user_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚫 Заблокировать",
                    callback_data=f"block:{user_id}"
                ),
                InlineKeyboardButton(
                    text="✅ Разблокировать",
                    callback_data=f"unblock:{user_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Админ-панель",
                    callback_data="admin_panel"
                )
            ],
        ]
    )