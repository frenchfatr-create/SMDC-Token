from html import escape

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_IDS
from db.complaints import get_open_complaints, close_complaint
from db.logs import write_log
from keyboards.admin import admin_panel_kb

router = Router()
bot_ref = None


def set_bot(bot):
    global bot_ref
    bot_ref = bot


@router.callback_query(F.data == "admin_complaints")
async def complaints_menu(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return

    rows = await get_open_complaints(20)
    if not rows:
        await callback.message.edit_text(
            "⚠️ <b>ЖАЛОБЫ</b>\n\nОткрытых жалоб нет.",
            reply_markup=admin_panel_kb(),
        )
        await callback.answer()
        return

    parts = ["⚠️ <b>ОТКРЫТЫЕ ЖАЛОБЫ</b>\n"]
    buttons = []
    for row in rows:
        parts.append(
            f"#{row['id']} • товар #{row['product_number']} • "
            f"пользователь <code>{row['user_id']}</code>\n"
            f"{escape(row['reason'])}\n"
        )
        buttons.append([
            InlineKeyboardButton(
                text=f"✅ Закрыть жалобу #{row['id']}",
                callback_data=f"complaint:close:{row['id']}",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_complaints"),
        InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin_panel"),
    ])

    await callback.message.edit_text(
        "\n".join(parts),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("complaint:close:"))
async def complaint_close(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return

    try:
        complaint_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("Некорректный ID.", show_alert=True)
        return

    await close_complaint(complaint_id)
    await write_log(
        bot_ref,
        callback.from_user.id,
        "COMPLAINT_CLOSED",
        f"Жалоба #{complaint_id}",
    )
    await callback.answer("Жалоба закрыта")
    await complaints_menu(callback)
