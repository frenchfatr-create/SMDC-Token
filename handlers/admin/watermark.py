from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_IDS
from db.settings import get_setting, set_setting
from keyboards.admin import admin_panel_kb, watermark_kb
from keyboards.common import main_menu
from states.forms import AdminWatermark

router = Router()


@router.callback_query(F.data == "admin_watermark")
async def admin_watermark(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return
    watermark = await get_setting("watermark_file_id", "")
    status = "🟢 установлен" if watermark else "🔴 не установлен"
    await callback.message.edit_text(
        "🖼 <b>ВОДЯНОЙ ЗНАК</b>\n\n"
        f"Статус: {status}\n\n"
        "Водяной знак автоматически накладывается на фотографии "
        "перед публикацией товара в канал.\n\n"
        "Видео не изменяются.",
        reply_markup=watermark_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "watermark_set")
async def watermark_set(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return
    await state.clear()
    await state.set_state(AdminWatermark.photo)
    await callback.message.edit_text(
        "🖼 <b>УСТАНОВКА ВОДЯНОГО ЗНАКА</b>\n\n"
        "Отправьте сюда фотографию, которая будет использоваться "
        "как водяной знак.\n\n"
        "Лучше использовать PNG с прозрачным фоном.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_watermark")]
        ]),
    )
    await callback.answer()


@router.message(AdminWatermark.photo, F.photo)
async def watermark_photo(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        return
    await set_setting("watermark_file_id", message.photo[-1].file_id)
    await state.clear()
    await message.answer(
        "✅ <b>Водяной знак сохранён.</b>\n\n"
        "Теперь фотографии новых публикаций будут автоматически "
        "получать этот водяной знак.",
        reply_markup=main_menu(message.from_user.id),
    )


@router.message(AdminWatermark.photo)
async def watermark_wrong(message: Message):
    await message.answer("🖼 Отправьте именно фотографию водяного знака.")


@router.callback_query(F.data == "watermark_delete")
async def watermark_delete(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return
    await set_setting("watermark_file_id", "")
    await callback.message.edit_text(
        "🗑 <b>Водяной знак удалён.</b>\n\n"
        "Новые фотографии будут публиковаться без водяного знака.",
        reply_markup=admin_panel_kb(),
    )
    await callback.answer("Водяной знак удалён.")