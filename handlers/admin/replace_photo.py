import json,logging
from aiogram import Router,F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message,CallbackQuery,InputMediaPhoto
from config import ADMIN_IDS,PUBLIC_CHANNEL
from db.ads import get_ad,update_ad_media
from db.users import get_user_rating
from db.logs import write_log
from core.utils import channel_post_text
from core.watermark import process_photo_with_watermark
from keyboards.common import main_menu
from states.forms import AdminReplacePhoto
router=Router(); bot_ref=None
def set_bot(bot): global bot_ref; bot_ref=bot

@router.callback_query(F.data.startswith("replace_photo:"))
async def replace_photo_start(c,state):
    if c.from_user.id not in ADMIN_IDS: await c.answer("⛔ Нет прав.",show_alert=True); return
    try:i=int(c.data.split(":",1)[1])
    except: await c.answer("Ошибка объявления.",show_alert=True); return
    ad=await get_ad(i)
    if not ad: await c.answer("Объявление не найдено.",show_alert=True); return
    await state.clear(); await state.update_data(ad_id=i); await state.set_state(AdminReplacePhoto.ad_id)
    await c.message.answer(f"🖼 <b>ЗАМЕНА ГЛАВНОГО ФОТО</b>\n\nТовар #{ad['product_number']}\n\nОтправьте новую фотографию.")
    await c.answer()

@router.message(AdminReplacePhoto.ad_id,F.photo)
async def receive(m,state):
    if m.from_user.id not in ADMIN_IDS: await state.clear(); return
    d=await state.get_data(); i=int(d["ad_id"]); ad=await get_ad(i)
    if not ad: await state.clear(); await m.answer("❌ Объявление не найдено."); return
    media=json.loads(ad["media_json"] or "[]"); media.insert(0,{"type":"photo","file_id":m.photo[-1].file_id}); media=media[:10]
    await update_ad_media(i,media)
    if ad["status"]=="published" and bot_ref and PUBLIC_CHANNEL and ad["published_message_id"]:
        try:
            rating,_=await get_user_rating(ad["user_id"])
            processed=await process_photo_with_watermark(bot_ref,m.photo[-1].file_id)
            await bot_ref.edit_message_media(chat_id=PUBLIC_CHANNEL,message_id=ad["published_message_id"],media=InputMediaPhoto(media=processed,caption=channel_post_text(ad,rating)))
        except Exception: logging.exception("Не удалось заменить фото в опубликованном посте")
    await write_log(bot_ref,m.from_user.id,"REPLACE_PHOTO",f"Товар #{ad['product_number']}")
    await state.clear(); await m.answer(f"✅ <b>Главное фото товара #{ad['product_number']} заменено.</b>",reply_markup=main_menu(m.from_user.id))

@router.message(AdminReplacePhoto.ad_id)
async def wrong(m,state): await m.answer("🖼 Отправьте фотографию.")
