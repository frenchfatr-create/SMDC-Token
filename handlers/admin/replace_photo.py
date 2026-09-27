import json
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from config import ADMIN_IDS
from db.ads import get_ad, update_ad_media
from keyboards.common import main_menu
from states.forms import AdminReplacePhoto

router = Router()


@router.callback_query(F.data.startswith("replace_photo:"))
async def replace_photo_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return

    try:
        ad_id = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("Ошибка объявления.", show_alert=True)
        return

    ad = await get_ad(ad_id)
    if not ad:
        await callback.answer("Объявление не найдено.", show_alert=True)
        return

    await state.clear()
    await state.update_data(ad_id=ad_id)
    await state.set_state(AdminReplacePhoto.ad_id)

    await callback.message.answer(
        f"🖼 <b>ЗАМЕНА ГЛАВНОГО ФОТО</b>\n\n"
        f"Товар #{ad_id}\n\n"
        "Отправьте новую фотографию.\n"
        "Она станет главным фото объявления."
    )
    await callback.answer()


@router.message(AdminReplacePhoto.ad_id, F.photo)
async def replace_photo_receive(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        return

    data = await state.get_data()
    ad_id = int(data["ad_id"])
    ad = await get_ad(ad_id)

    if not ad:
        await state.clear()
        await message.answer("❌ Объявление не найдено.")
        return

    media = json.loads(ad["media_json"] or "[]")
    new_photo = {"type": "photo", "file_id": message.photo[-1].file_id}

    if media:
        media[0] = new_photo
    else:
        media = [new_photo]

    await update_ad_media(ad_id, media)
    await state.clear()

    await message.answer(
        f"✅ <b>Главное фото товара #{ad_id} заменено.</b>\n\n"
        "Если товар будет опубликован после этого, на новое фото "
        "автоматически будет нанесён водяной знак, если он установлен.",
        reply_markup=main_menu(message.from_user.id),
    )


@router.message(AdminReplacePhoto.ad_id)
async def replace_photo_wrong(message: Message):
    await message.answer("🖼 Отправьте фотографию.")