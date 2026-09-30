from aiogram import Router, F
from aiogram.types import CallbackQuery

from config import ADMIN_IDS
from db.stats import get_stats
from keyboards.admin import admin_panel_kb

router = Router()


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return

    s = await get_stats()
    text = (
        "📊 <b>СТАТИСТИКА</b>\n\n"
        f"👤 Пользователей: <b>{s['users']}</b>\n"
        f"📦 Всего объявлений: <b>{s['ads']}</b>\n"
        f"⏳ На модерации: <b>{s['pending']}</b>\n"
        f"🟢 Опубликовано: <b>{s['published']}</b>\n"
        f"💰 Продано: <b>{s['sold']}</b>\n"
        f"⚫ Снято: <b>{s['removed']}</b>\n"
        f"🧾 Заказов: <b>{s['orders']}</b>\n"
        f"⚠️ Открытых жалоб: <b>{s['complaints']}</b>"
    )
    await callback.message.edit_text(text, reply_markup=admin_panel_kb())
    await callback.answer()