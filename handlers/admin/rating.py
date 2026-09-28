import json,logging
from aiogram import Router,F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message,CallbackQuery,InlineKeyboardMarkup,InlineKeyboardButton
from config import ADMIN_IDS,PUBLIC_CHANNEL
from core.utils import rating_text,channel_post_text
from db.users import set_user_rating
from db.ads import get_published_user_ads
from db.logs import write_log
from keyboards.common import main_menu
from states.forms import AdminRating
router=Router(); bot_ref=None
def set_bot(bot): global bot_ref; bot_ref=bot
@router.callback_query(F.data=="admin_rating")
async def start(c,state):
    if c.from_user.id not in ADMIN_IDS: await c.answer("⛔ Нет прав.",show_alert=True); return
    await state.clear(); await state.set_state(AdminRating.user_id); await c.message.edit_text("⭐ <b>ИЗМЕНЕНИЕ РЕЙТИНГА</b>\n\nВведите Telegram ID продавца:",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена",callback_data="admin_panel")]])); await c.answer()
@router.message(AdminRating.user_id)
async def get_id(m,state):
    try: uid=int((m.text or "").strip())
    except: await m.answer("❌ ID должен быть числом."); return
    await state.update_data(user_id=uid); await state.set_state(AdminRating.rating); await m.answer("⭐ Введите рейтинг от 0 до 5. Например: <code>3.8</code>")
@router.message(AdminRating.rating)
async def value(m,state):
    try:r=float((m.text or "").replace(",",".")); assert 0<=r<=5
    except: await m.answer("❌ Рейтинг должен быть числом от 0 до 5."); return
    d=await state.get_data(); uid=int(d["user_id"]); await set_user_rating(uid,r)
    updated=0
    if bot_ref and PUBLIC_CHANNEL:
        for ad in await get_published_user_ads(uid):
            try:
                cap=channel_post_text(ad,r)
                media=json.loads(ad["media_json"] or "[]")
                if media: await bot_ref.edit_message_caption(chat_id=PUBLIC_CHANNEL,message_id=ad["published_message_id"],caption=cap)
                else: await bot_ref.edit_message_text(chat_id=PUBLIC_CHANNEL,message_id=ad["published_message_id"],text=cap)
                updated+=1
            except Exception: logging.exception("rating post update failed")
    await write_log(bot_ref,m.from_user.id,"RATING",f"Продавец {uid}: {r}")
    await state.clear(); await m.answer(f"✅ <b>Рейтинг изменён.</b>\n\nID: <code>{uid}</code>\n⭐ {rating_text(r)}/5\n📢 Обновлено постов: {updated}",reply_markup=main_menu(m.from_user.id))
