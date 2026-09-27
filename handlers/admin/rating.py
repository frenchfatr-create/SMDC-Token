from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_IDS
from core.utils import rating_text
from db.users import set_user_rating
from keyboards.common import main_menu
from states.forms import AdminRating

router = Router()


@router.callback_query(F.data == "admin_rating")
async def admin_rating_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return
    await state.clear()
    await state.set_state(AdminRating.user_id)
    await callback.message.edit_text(
        "⭐ <b>ИЗМЕНЕНИЕ РЕЙТИНГА</b>\n\n"
        "Введите Telegram ID продавца.\n\n"
        "Например:\n<code>1955966085</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
        ]),
    )
    await callback.answer()


@router.message(AdminRating.user_id)
async def admin_rating_user(message: Message, state: FSMContext):
    raw = (message.text or "").strip()
    try:
        user_id = int(raw)
    except ValueError:
        await message.answer("❌ ID должен состоять только из цифр.")
        return
    await state.update_data(user_id=user_id)
    await state.set_state(AdminRating.rating)
    await message.answer(
        "⭐ Теперь введите новый рейтинг.\n\n"
        "Допустимый диапазон: <code>0</code> — <code>5</code>\n\n"
        "Например: <code>3.8</code>"
    )


@router.message(AdminRating.rating)
async def admin_rating_value(message: Message, state: FSMContext):
    raw = (message.text or "").replace(",", ".").strip()
    try:
        rating = float(raw)
        if rating < 0 or rating > 5:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Рейтинг должен быть числом от 0 до 5.\n\n"
            "Например: <code>3.8</code>"
        )
        return

    data = await state.get_data()
    user_id = int(data["user_id"])
    await set_user_rating(user_id, rating)
    await state.clear()

    await message.answer(
        "✅ <b>Рейтинг изменён.</b>\n\n"
        f"👤 ID: <code>{user_id}</code>\n"
        f"⭐ Новый рейтинг: <b>{rating_text(rating)}/5</b>",
        reply_markup=main_menu(message.from_user.id),
    )