import json,logging
from html import escape
from aiogram import Router,F
from aiogram.types import Message,CallbackQuery,InlineKeyboardMarkup,InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from config import ADMIN_IDS,PUBLIC_CHANNEL
from core.constants import KIND_NAMES,KIND_EMOJI,PAY_NAMES
from core.utils import format_price,rating_text,seller_label
from db.ads import get_ad,update_ad_price
from db.users import get_user_rating
from keyboards.common import main_menu
from states.forms import PriceEdit
router=Router(); bot_ref=None
def set_bot(bot):
    global bot_ref; bot_ref=bot
def _cancel(i): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена",callback_data=f"price_edit:cancel:{i}")]])
@router.callback_query(F.data.startswith("price_edit:menu:"))
async def price_menu(c,state):
    try:i=int(c.data.split(":")[2])
    except: await c.answer("Ошибка ID",show_alert=True); return
    ad=await get_ad(i)
    if not ad or (c.from_user.id not in ADMIN_IDS and c.from_user.id!=ad["user_id"]): await c.answer("⛔ Нет прав или товар не найден",show_alert=True); return
    await state.clear(); await state.update_data(ad_id=i); await state.set_state(PriceEdit.new_price)
    await c.message.answer(f"💰 <b>Товар #{ad['product_number']}</b>\nТекущая цена: <b>{format_price(ad['price'])}</b>\n\nВведите новую цену:",reply_markup=_cancel(i)); await c.answer()
@router.callback_query(F.data.startswith("price_edit:cancel:"))
async def cancel(c,state): await state.clear(); await c.message.edit_text("❌ Изменение цены отменено.",reply_markup=main_menu(c.from_user.id)); await c.answer()
@router.message(PriceEdit.new_price)
async def receive(m,state):
    try:v=float((m.text or '').replace(',','.').replace('₽','').strip()); assert 0<v<=10000000
    except: await m.answer("❌ Введите корректную цену, например <code>4.5</code>."); return
    data=await state.get_data(); i=int(data['ad_id']); ad=await get_ad(i)
    if not ad: await state.clear(); await m.answer("❌ Товар не найден"); return
    old=float(ad['price']); await update_ad_price(i,v); await state.clear()
    if bot_ref and PUBLIC_CHANNEL and ad['status']=='published' and ad['published_message_id']:
        try:
            rating,_=await get_user_rating(ad['user_id']); cap=_build_caption(ad,rating,v)
            media=json.loads(ad['media_json'] or '[]')
            if media: await bot_ref.edit_message_caption(chat_id=PUBLIC_CHANNEL,message_id=ad['published_message_id'],caption=cap)
            else: await bot_ref.edit_message_text(chat_id=PUBLIC_CHANNEL,message_id=ad['published_message_id'],text=cap)
        except Exception: logging.exception('price post edit failed')
    await m.answer(f"✅ Цена товара #{ad['product_number']} изменена: {format_price(old)} → <b>{format_price(v)}</b>",reply_markup=main_menu(m.from_user.id))
def _build_caption(ad,rating,new_price):
    return f"📦<b>Товар #{ad['product_number']} — {escape(KIND_NAMES.get(ad['kind'],ad['kind']))} {KIND_EMOJI.get(ad['kind'],'📦')}</b>\n🎮<b>Игра:</b> {escape(ad['game'])}\n👑<b>Статус:</b> Не продан\n💰<b>Цена:</b> {format_price(new_price)}\n💳<b>Способ оплаты:</b> {escape(PAY_NAMES.get(ad['payment'],ad['payment']))}\n\n👤<b>Продавец (SMDC {rating_text(rating)}/5):</b> {escape(seller_label(ad))}\n\n📖<b>Информация о товаре:</b> {escape(ad['description'])}"
