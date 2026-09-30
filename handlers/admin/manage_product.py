from aiogram import Router,F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery,Message
from config import ADMIN_IDS
from db.ads import get_ad_by_product_number,set_status
from db.logs import write_log
from core.channel import edit_ad_channel_post
from keyboards.admin import admin_panel_kb,product_manage_kb
from states.forms import AdminProductManage
router=Router(); bot_ref=None
def set_bot(bot): global bot_ref; bot_ref=bot

@router.callback_query(F.data=="admin_product_manage")
async def start(c,state):
    if c.from_user.id not in ADMIN_IDS: await c.answer("⛔",show_alert=True); return
    await state.clear(); await state.set_state(AdminProductManage.product_number); await c.message.edit_text("🛠 <b>УПРАВЛЕНИЕ ТОВАРОМ</b>\n\nВведите ID товара, например <code>80</code>."); await c.answer()

@router.message(AdminProductManage.product_number)
async def receive(m,state):
    try:n=int((m.text or "").strip())
    except: await m.answer("❌ Введите номер товара."); return
    ad=await get_ad_by_product_number(n)
    if not ad: await m.answer(f"❌ Товар #{n} не найден.",reply_markup=admin_panel_kb()); await state.clear(); return
    await state.clear()
    await m.answer(f"📦 <b>Товар #{n}</b>\n\nСтатус: <b>{ad['status']}</b>\n\nВыберите действие:",reply_markup=product_manage_kb(n))

@router.callback_query(F.data.startswith("manage:"))
async def action(c):
    if c.from_user.id not in ADMIN_IDS: await c.answer("⛔",show_alert=True); return
    _,act,n=c.data.split(":"); n=int(n); ad=await get_ad_by_product_number(n)
    if not ad: await c.answer("Товар не найден",show_alert=True); return
    if ad["status"] not in ("published","sold","removed"):
        await c.answer("Этот товар сейчас нельзя изменить этим действием.",show_alert=True); return
    status="sold" if act=="sold" else "removed"
    if ad["status"]==status: await c.answer("Этот статус уже установлен.",show_alert=True); return
    await set_status(ad["id"],status)
    await edit_ad_channel_post(bot_ref,ad,"🔴 ПРОДАН" if status=="sold" else "⚫ СНЯТ С ПРОДАЖИ")
    await write_log(bot_ref,c.from_user.id,"PRODUCT_STATUS",f"Товар #{n}: {status}")
    await c.message.edit_text(f"✅ Товар #{n} теперь: <b>{'ПРОДАН' if status=='sold' else 'СНЯТ С ПРОДАЖИ'}</b>\n\nОн скрыт из магазина.",reply_markup=admin_panel_kb()); await c.answer()
