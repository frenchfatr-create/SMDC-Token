from aiogram import Router, F
from aiogram.types import CallbackQuery
from html import escape

from config import ADMIN_IDS
from core.constants import KIND_NAMES, STATUS_NAMES
from core.utils import format_price
from db.ads import get_recent_ads
from keyboards.admin import admin_panel_kb

router = Router()


@router.callback_query(F.data == "admin_products")
async def admin_products(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return

    rows = await get_recent_ads()

    if not rows:
        await callback.message.edit_text(
            "📦 <b>ТОВАРЫ</b>\n\nТоваров пока нет.",
            reply_markup=admin_panel_kb(),
        )
        await callback.answer()
        return

    parts = ["📦 <b>ПОСЛЕДНИЕ ТОВАРЫ</b>\n"]
    for row in rows:
        parts.append(
            f"#{row['product_number']} (DB {row['id']}) — "
            f"{escape(KIND_NAMES.get(row['kind'], row['kind']))} — "
            f"{escape(row['game'])} — "
            f"{format_price(row['price'])} — "
            f"{STATUS_NAMES.get(row['status'], row['status'])}"
        )

    await callback.message.edit_text(
        "\n".join(parts),
        reply_markup=admin_panel_kb(),
    )
    await callback.answer()