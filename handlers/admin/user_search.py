from html import escape

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_IDS
from db.users import get_user_rating
from db.ads import get_user_ads_count
from db.blocks import is_blocked
from keyboards.admin import admin_panel_kb
from states.forms import AdminUserSearch

router = Router()


@router.callback_query(F.data == "admin_user")
async def start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return
    await state.clear()
    await state.set_state(AdminUserSearch.user_id)
    await callback.message.edit_text(
        "👤 <b>ПОИСК ПОЛЬЗОВАТЕЛЯ</b>\n\nВведите Telegram ID:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
        ]),
    )
    await callback.answer()


@router.message(AdminUserSearch.user_id)
async def receive(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        return
    try:
        user_id = int((message.text or "").strip())
    except ValueError:
        await message.answer("❌ ID должен быть числом.")
        return

    rating, count = await get_user_rating(user_id)
    ads_count = await get_user_ads_count(user_id)
    blocked = await is_blocked(user_id)
    await state.clear()

    await message.answer(
        "👤 <b>ПОЛЬЗОВАТЕЛЬ</b>\n\n"
        f"ID: <code>{user_id}</code>\n"
        f"⭐ Рейтинг: <b>{rating:.1f}/5</b> ({count} оценок)\n"
        f"📦 Объявлений: <b>{ads_count}</b>\n"
        f"🚫 Блокировка: <b>{'ДА' if blocked else 'НЕТ'}</b>",
        reply_markup=admin_panel_kb(),
    )
