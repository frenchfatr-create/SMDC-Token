from aiogram import Router,F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message,CallbackQuery
from config import ADMIN_IDS,PUBLIC_CHANNEL
from core.constants import KIND_NAMES,KIND_EMOJI,PAY_NAMES
from core.utils import format_price,rating_text,seller_label
from db.users import get_user_rating
import json
from db.ads import get_ad,update_product_number
from keyboards.common import main_menu
from states.forms import ProductNumberEdit
router=Router(); bot_ref=None
def set_bot(bot):
    global bot_ref; bot_ref=bot
@router.callback_query(F.data.startswith('product_number:menu:'))
async def start(c,state):
    if c.from_user.id not in ADMIN_IDS: await c.answer('⛔ Нет прав',show_alert=True); return
    try:i=int(c.data.split(':')[2])
    except: await c.answer('Ошибка',show_alert=True); return
    ad=await get_ad(i)
    if not ad: await c.answer('Товар не найден',show_alert=True); return
    await state.clear(); await state.update_data(ad_id=i); await state.set_state(ProductNumberEdit.number)
    await c.message.answer(f"🔢 <b>Номер товара</b>\nСейчас: <b>#{ad['product_number']}</b>\n\nВведите новый номер, например <code>25</code>.")
    await c.answer()
@router.message(ProductNumberEdit.number)
async def receive(m,state):
    if m.from_user.id not in ADMIN_IDS: await state.clear(); return
    try:n=int((m.text or '').strip()); assert 1<=n<=999999999
    except: await m.answer('❌ Номер должен быть положительным целым числом.'); return
    data=await state.get_data(); i=int(data['ad_id']); ad=await get_ad(i)
    if not ad: await state.clear(); await m.answer('❌ Товар не найден'); return
    ok=await update_product_number(i,n)
    if not ok: await m.answer(f'❌ Товар #{n} уже существует. Выберите другой номер.'); return
    old=ad['product_number']; await state.clear()
    if bot_ref and PUBLIC_CHANNEL and ad['status']=='published' and ad['published_message_id']:
        try:
            rating,_=await get_user_rating(ad['user_id']); cap=f"📦<b>Товар #{n} — {KIND_NAMES.get(ad['kind'],ad['kind'])} {KIND_EMOJI.get(ad['kind'],'📦')}</b>\n🎮<b>Игра:</b> {ad['game']}\n👑<b>Статус:</b> Не продан\n💰<b>Цена:</b> {format_price(ad['price'])}\n💳<b>Способ оплаты:</b> {PAY_NAMES.get(ad['payment'],ad['payment'])}\n\n👤<b>Продавец (SMDC {rating_text(rating)}/5):</b> {seller_label(ad)}\n\n📖<b>Информация о товаре:</b> {ad['description']}"
            media=json.loads(ad['media_json'] or '[]')
            if media: await bot_ref.edit_message_caption(chat_id=PUBLIC_CHANNEL,message_id=ad['published_message_id'],caption=cap)
            else: await bot_ref.edit_message_text(chat_id=PUBLIC_CHANNEL,message_id=ad['published_message_id'],text=cap)
        except Exception: pass
    await m.answer(f"✅ Публичный номер изменён: #{old} → <b>#{n}</b>.",reply_markup=main_menu(m.from_user.id))
