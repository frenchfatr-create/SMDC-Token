from aiogram import Router, F
from aiogram.types import CallbackQuery
from html import escape

from db.users import save_user, get_user_rating
from db.ads import get_user_ads_count, get_user_ads
from core.constants import KIND_NAMES, STATUS_NAMES
from core.utils import format_price, rating_text
from keyboards.common import main_menu

router = Router()


@router.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):
    await save_user(callback.from_user)
    rating, rating_count = await get_user_rating(callback.from_user.id)
    count = await get_user_ads_count(callback.from_user.id)

    username = callback.from_user.username or "не указан"
    text = (
        "👤 <b>МОЙ ПРОФИЛЬ</b>\n\n"
        f"ID: <code>{callback.from_user.id}</code>\n"
        f"Username: @{escape(username)}\n"
        f"⭐ Рейтинг SMDC: {rating_text(rating)}/5"
    )
    if rating_count:
        text += f" ({rating_count} оценок)"
    text += f"\n📦 Объявлений: {count}"

    await callback.message.edit_text(text, reply_markup=main_menu(callback.from_user.id))
    await callback.answer()


@router.callback_query(F.data == "my_ads")
async def my_ads(callback: CallbackQuery):
    rows = await get_user_ads(callback.from_user.id)

    if not rows:
        text = "📋 <b>МОИ ОБЪЯВЛЕНИЯ</b>\n\nУ вас пока нет объявлений."
    else:
        parts = ["📋 <b>МОИ ОБЪЯВЛЕНИЯ</b>\n"]
        for row in rows:
            parts.append(
                f"📦 <b>Товар #{row['product_number']}</b>\n"
                f"├ {escape(KIND_NAMES.get(row['kind'], row['kind']))}\n"
                f"├ {escape(row['game'])}\n"
                f"├ {format_price(row['price'])}\n"
                f"└ {STATUS_NAMES.get(row['status'], row['status'])}\n"
            )
        text = "\n".join(parts)

    await callback.message.edit_text(text, reply_markup=main_menu(callback.from_user.id))
    await callback.answer()