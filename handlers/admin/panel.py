from aiogram import Router, F
from aiogram.types import CallbackQuery

from config import ADMIN_IDS
from db.settings import get_setting
from config import PAYMENT_DETAILS
from keyboards.admin import admin_panel_kb

router = Router()


@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав администратора.", show_alert=True)
        return

    watermark = await get_setting("watermark_file_id", "")
    payment = await get_setting("payment_details", PAYMENT_DETAILS)
    status = "установлен" if watermark else "не установлен"
    payment_status = "настроены" if payment else "не настроены"

    await callback.message.edit_text(
        "⚙️ <b>АДМИН-ПАНЕЛЬ</b>\n\n"
        f"🖼 Водяной знак: <b>{status}</b>\n"
        f"💳 Реквизиты: <b>{payment_status}</b>\n\n"
        "Здесь можно управлять рейтингами, реквизитами, водяным знаком и товарами.",
        reply_markup=admin_panel_kb(),
    )
    await callback.answer()