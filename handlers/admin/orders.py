from html import escape
from aiogram import Router,F
from aiogram.types import CallbackQuery
from config import ADMIN_IDS,RECEIPT_CHAT_ID
from core.constants import ORDER_STATUS_NAMES
from db.orders import get_order,set_order_status,get_recent_orders
from keyboards.admin import admin_panel_kb,order_admin_kb
router=Router(); bot_ref=None
def set_bot(bot):
    global bot_ref; bot_ref=bot

def text(o):
    return (f"🧾 <b>{escape(o['order_number'])}</b>\n\n👤 @{escape(o['username'] or 'не указан')} (<code>{o['user_id']}</code>)\n🎮 {escape(o['game'])}\n📦 {escape(o['product_name'])}\n🔢 Количество: {o['quantity']}\n💰 {o['amount_rub']:.2f} ₽"+(f"\n⭐ {o['amount_stars']} Stars" if o['amount_stars'] else '')+f"\n💳 {escape(o['payment_method'])}\n📌 {ORDER_STATUS_NAMES.get(o['status'],o['status'])}")
@router.callback_query(F.data=='admin_orders')
async def list_orders(c):
    if c.from_user.id not in ADMIN_IDS: await c.answer('⛔ Нет прав',show_alert=True); return
    rows=await get_recent_orders()
    body='📋 <b>ПОСЛЕДНИЕ ЗАКАЗЫ</b>\n\n'+('\n'.join(f"<code>{r['order_number']}</code> — {escape(r['product_name'])} — {ORDER_STATUS_NAMES.get(r['status'],r['status'])}" for r in rows) if rows else 'Заказов пока нет.')
    await c.message.edit_text(body,reply_markup=admin_panel_kb()); await c.answer()
@router.callback_query(F.data.startswith('order:'))
async def action(c):
    if c.from_user.id not in ADMIN_IDS: await c.answer('⛔ Нет прав',show_alert=True); return
    _,act,n=c.data.split(':',2); o=await get_order(n)
    if not o: await c.answer('Заказ не найден',show_alert=True); return
    status={'paid':'paid','complete':'completed','reject':'rejected'}.get(act)
    if not status: await c.answer('Неизвестное действие',show_alert=True); return
    await set_order_status(n,status,c.from_user.id)
    await c.message.edit_reply_markup(reply_markup=None)
    await c.message.answer(f"{text(o)}\n\n➡️ Новый статус: <b>{ORDER_STATUS_NAMES[status]}</b>")
    if bot_ref:
        try:
            msg={'paid':f'✅ Оплата по заказу {n} подтверждена.','completed':f'🎉 Заказ {n} выполнен.','rejected':f'❌ Заказ {n} отклонён.'}[status]
            await bot_ref.send_message(o['user_id'],msg)
        except Exception: pass
    await c.answer('Готово')
