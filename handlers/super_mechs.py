from html import escape
from aiogram import Router,F
from aiogram.types import Message,CallbackQuery
from aiogram.fsm.context import FSMContext
from config import ADMIN_IDS,PAYMENT_DETAILS,RECEIPT_CHAT_ID,SUPPORT_CONTACT
from db.settings import get_setting
from core.super_mechs import RUB_PACKS,STAR_PACKS,BOOST_PACKS,rub_tokens,star_tokens,silver_total
from core.constants import ORDER_STATUS_NAMES
from db.orders import create_order,get_order,set_receipt,get_user_orders,set_payment_method
from keyboards.sm import sm_menu,pack_kb,payment_kb
from keyboards.admin import order_admin_kb
from states.forms import OrderFlow
router=Router(); bot_ref=None
def set_bot(bot):
    global bot_ref; bot_ref=bot
async def _new(c,state,ptype,name,qty,rub=0,stars=0,details=''):
    n=await create_order(user_id=c.from_user.id,username=c.from_user.username,game='Super Mechs',product_type=ptype,product_name=name,quantity=qty,amount_rub=rub,amount_stars=stars,details=details,payment_method='card')
    await state.clear(); await state.update_data(order_number=n); await state.set_state(OrderFlow.payment)
    price=(f'{rub:g} ₽' if rub else f'{stars} ⭐')
    await c.message.edit_text(f'🧾 <b>Заказ {n}</b>\n\n🎮 Super Mechs\n📦 {escape(name)}\n💰 К оплате: <b>{price}</b>\n\nВыберите способ оплаты:',reply_markup=payment_kb()); await c.answer()

@router.callback_query(F.data.startswith('sm_order:ad:'))
async def order_ad(c,state):
    try: i=int(c.data.split(':')[-1])
    except: await c.answer('Ошибка товара',show_alert=True); return
    from db.ads import get_ad
    ad=await get_ad(i)
    if not ad or ad['status']!='published': await c.answer('Товар больше недоступен',show_alert=True); return
    await _new(c,state,'marketplace',f'Товар #{ad["product_number"]}: {ad["game"]}',1,float(ad['price']),0,f'Товар #{ad["product_number"]}; продавец ID {ad["user_id"]}')

@router.callback_query(F.data=='sm_menu')
async def menu(c): await c.message.edit_text('🎮 <b>SUPER MECHS</b>\n\nВыберите товар:',reply_markup=sm_menu()); await c.answer()
@router.callback_query(F.data=='sm:rub')
async def rub(c): await c.message.edit_text('💰 <b>ТОКЕНЫ ЗА РУБЛИ</b>\n\n50 ₽ = 7 500 токенов.\nОпт от 500 ₽: каждые +50 ₽ = +7 500 токенов.',reply_markup=pack_kb('smrub',[(f'{r} ₽ → {t:,}'.replace(',',' '),str(r)) for r,t in RUB_PACKS])); await c.answer()
@router.callback_query(F.data.startswith('smrub:'))
async def rub_pick(c,state):
    x=c.data.split(':')[1]
    if x=='custom': await state.clear(); await state.set_state(OrderFlow.quantity); await state.update_data(product_type='tokens_rub'); await c.message.edit_text('💰 Введите сумму в рублях (от 500 ₽).'); await c.answer(); return
    amount=int(x); await _new(c,state,'tokens_rub',f'{rub_tokens(amount):,}'.replace(',',' ')+' токенов',1,amount,0,f'Сумма: {amount} ₽');
@router.message(OrderFlow.quantity)
async def custom_amount(m,state):
    d=await state.get_data(); p=d.get('product_type')
    try:v=int((m.text or '').strip())
    except: await m.answer('❌ Введите целое число.'); return
    try:
        if p=='tokens_rub': tok=rub_tokens(v); await state.clear(); n=await create_order(user_id=m.from_user.id,username=m.from_user.username,game='Super Mechs',product_type=p,product_name=f'{tok:,}'.replace(',',' ')+' токенов',quantity=1,amount_rub=v,details=f'Сумма: {v} ₽',payment_method='card'); await state.update_data(order_number=n); await state.set_state(OrderFlow.payment); await m.answer(f'🧾 <b>Заказ {n}</b>\n💰 {v} ₽ → {tok:,} токенов\n\nВыберите оплату:',reply_markup=payment_kb())
        elif p=='tokens_stars': tok=star_tokens(v); await state.clear(); n=await create_order(user_id=m.from_user.id,username=m.from_user.username,game='Super Mechs',product_type=p,product_name=f'{tok:,}'.replace(',',' ')+' токенов',quantity=1,amount_stars=v,details=f'Stars: {v}',payment_method='stars'); await state.update_data(order_number=n); await state.set_state(OrderFlow.receipt); await m.answer(f'🧾 <b>Заказ {n}</b>\n⭐ {v} Stars → {tok:,} токенов\n\nПосле оплаты отправьте чек/подтверждение сюда.')
        elif p=='silver':
            total=silver_total(v); await state.clear(); n=await create_order(user_id=m.from_user.id,username=m.from_user.username,game='Super Mechs',product_type=p,product_name=f'{v} Silver Boxes',quantity=v,amount_rub=total,details=f'Количество: {v}',payment_method='card'); await state.update_data(order_number=n); await state.set_state(OrderFlow.payment); await m.answer(f'🧾 <b>Заказ {n}</b>\n📦 {v} Silver Boxes\n💰 {total:.2f} ₽\n\nВыберите оплату:',reply_markup=payment_kb())
    except ValueError as e: await m.answer(f'❌ {e}')
@router.callback_query(F.data=='sm:stars')
async def stars(c): await c.message.edit_text('⭐ <b>ТОКЕНЫ ЗА STARS</b>\n\nВыберите тариф. После 250 ⭐ опт идёт шагом 25 ⭐ = +7 500 токенов.',reply_markup=pack_kb('smstars',[(f'{s} ⭐ → {t:,}'.replace(',',' '),str(s)) for s,t in STAR_PACKS])); await c.answer()
@router.callback_query(F.data.startswith('smstars:'))
async def stars_pick(c,state):
    x=c.data.split(':')[1]
    if x=='custom': await state.clear(); await state.set_state(OrderFlow.quantity); await state.update_data(product_type='tokens_stars'); await c.message.edit_text('⭐ Введите количество Stars (после 250 — шаг 25).'); await c.answer(); return
    v=int(x); await _new(c,state,'tokens_stars',f'{star_tokens(v):,}'.replace(',',' ')+' токенов',1,0,v,f'Stars: {v}')
@router.callback_query(F.data=='sm:boost')
async def boost(c): await c.message.edit_text('📈 <b>НАКРУТКА АКЦИЙ</b>\n\n5 = 30 ₽\n10 = 80 ₽\n15 = 130 ₽\n20 = 180 ₽\n\n⚠️ Акция должна быть активна и покупаться за токены. После начала накрутки возврата нет.',reply_markup=pack_kb('smboost',[(f'{q} покупок → {p} ₽',str(q)) for q,p in BOOST_PACKS],custom=False)); await c.answer()
@router.callback_query(F.data.startswith('smboost:'))
async def boost_pick(c,state):
    q=int(c.data.split(':')[1]); price=dict(BOOST_PACKS)[q]; await _new(c,state,'boost',f'Накрутка {q} покупок',q,price,0,'Условия подтверждены пользователем перед заказом.')
@router.callback_query(F.data=='sm:silver')
async def silver(c,state):
    await state.clear(); await state.set_state(OrderFlow.quantity); await state.update_data(product_type='silver')
    await c.message.edit_text('📦 <b>SILVER БОКСЫ</b>\n\n1 шт = 1,5 ₽. Минимум 10 шт.\n\nВведите количество:'); await c.answer()

@router.callback_query(F.data=='sm:fuel')
async def fuel(c,state):
    await _new(c,state,'fuel','999 ед. топлива',999,100,0,'999 ед. топлива')

@router.callback_query(F.data.startswith('sm_pay:'))
async def choose_pay(c,state):
    d=await state.get_data(); method=c.data.split(':')[1]; n=d.get('order_number')
    if not n: await c.answer('Заказ не найден',show_alert=True); return
    if method=='stars':
        await set_payment_method(n,'stars'); await c.message.edit_text(f'⭐ <b>Заказ {n}</b>\n\nПосле оплаты Stars отправьте сюда скриншот/чек.'); await state.set_state(OrderFlow.receipt)
    else:
        await set_payment_method(n,'card'); details=await get_setting('payment_details', PAYMENT_DETAILS); shown=escape(details) if details else '⚠️ Реквизиты пока не настроены. Обратитесь к администратору.'; await c.message.edit_text(f'💳 <b>Оплата заказа {n}</b>\n\n<b>Реквизиты:</b>\n{shown}\n\nПосле оплаты отправьте сюда фото или файл чека.'); await state.set_state(OrderFlow.receipt)
    await c.answer()
@router.message(OrderFlow.receipt,F.photo)
async def receipt_photo(m,state): await _receipt(m,state,m.photo[-1].file_id,'photo')
@router.message(OrderFlow.receipt,F.document)
async def receipt_doc(m,state): await _receipt(m,state,m.document.file_id,'document')
async def _receipt(m,state,file_id,file_type):
    d=await state.get_data(); n=d.get('order_number'); o=await get_order(n) if n else None
    if not o: await state.clear(); await m.answer('❌ Заказ не найден.'); return
    await set_receipt(n,file_id,file_type); await state.clear()
    if bot_ref and RECEIPT_CHAT_ID:
        text=f'🧾 <b>НОВЫЙ ЧЕК • {n}</b>\n\n👤 @{escape(m.from_user.username or "не указан")} (<code>{m.from_user.id}</code>)\n📦 {escape(o["product_name"])}\n💰 {o["amount_rub"]:.2f} ₽' + (f'\n⭐ {o["amount_stars"]}' if o['amount_stars'] else '')
        if file_type=='photo': await bot_ref.send_photo(RECEIPT_CHAT_ID,file_id,caption=text,reply_markup=order_admin_kb(n))
        else: await bot_ref.send_document(RECEIPT_CHAT_ID,file_id,caption=text,reply_markup=order_admin_kb(n))
    await m.answer(f'✅ <b>Чек принят.</b>\n\nВаш номер: <code>{n}</code>\nСтатус: 🧾 Чек отправлен.\n\nСохраните номер заказа.',reply_markup=sm_menu())
@router.callback_query(F.data=='my_orders')
async def my_orders(c):
    rows=await get_user_orders(c.from_user.id)
    if not rows: await c.message.edit_text('🧾 <b>МОИ ЗАКАЗЫ</b>\n\nЗаказов пока нет.',reply_markup=sm_menu()); await c.answer(); return
    text='🧾 <b>МОИ ЗАКАЗЫ</b>\n\n'+ '\n'.join(f"<code>{r['order_number']}</code> — {escape(r['product_name'])} — {ORDER_STATUS_NAMES.get(r['status'],r['status'])}" for r in rows)
    await c.message.edit_text(text,reply_markup=sm_menu()); await c.answer()
