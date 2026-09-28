from html import escape
from aiogram import Router,F
from aiogram.types import CallbackQuery,InlineKeyboardMarkup,InlineKeyboardButton
from config import ADMIN_IDS
from db.logs import logs_enabled,set_logs_enabled,get_recent_logs
from keyboards.admin import admin_panel_kb
router=Router()
@router.callback_query(F.data=="admin_logs")
async def menu(c):
    if c.from_user.id not in ADMIN_IDS: await c.answer("⛔",show_alert=True); return
    on=await logs_enabled(); rows=await get_recent_logs(20)
    text=f"📜 <b>ЛОГИ</b>\n\nСтатус: {'🟢 ВКЛЮЧЕНЫ' if on else '🔴 ВЫКЛЮЧЕНЫ'}\n\n"
    if rows: text+="\n".join(f"<code>{r['created_at'][:19]}</code> • {escape(r['event'])} • <code>{r['user_id']}</code>\n{escape(r['details'])}" for r in rows[:10])
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Включить" if not on else "🔴 Выключить",callback_data="logs:toggle")],
        [InlineKeyboardButton(text="🔄 Обновить",callback_data="admin_logs")],[InlineKeyboardButton(text="🔙 Админ-панель",callback_data="admin_panel")]])
    await c.message.edit_text(text,reply_markup=kb); await c.answer()
@router.callback_query(F.data=="logs:toggle")
async def toggle(c):
    if c.from_user.id not in ADMIN_IDS: await c.answer("⛔",show_alert=True); return
    on=await logs_enabled(); await set_logs_enabled(not on); await c.answer("Включено" if not on else "Выключено"); await menu(c)
