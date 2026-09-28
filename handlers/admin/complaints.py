from html import escape
from aiogram import Router,F
from aiogram.types import CallbackQuery,InlineKeyboardMarkup,InlineKeyboardButton
from config import ADMIN_IDS
from db.complaints import get_open_complaints,close_complaint
from db.ads import get_ad,set_status
from db.blocks import block_user
from db.logs import write_log
from keyboards.admin import admin_panel_kb
from core.channel import edit_ad_channel_post
router=Router(); bot_ref=None
def set_bot(bot): global bot_ref; bot_ref=bot

@router.callback_query(F.data=="admin_complaints")
async def list_(c):
    if c.from_user.id not in ADMIN_IDS: await c.answer("⛔",show_alert=True); return
    rows=await get_open_complaints(20)
    if not rows: await c.message.edit_text("⚠️ <b>ЖАЛОБЫ</b>\n\nОткрытых жалоб нет.",reply_markup=admin_panel_kb()); await c.answer(); return
    text="⚠️ <b>ОТКРЫТЫЕ ЖАЛОБЫ</b>\n\n"
    for r in rows:
        text+=f"#{r['id']} • товар #{r['product_number']} • пользователь <code>{r['user_id']}</code>\n{escape(r['reason'])}\n\n"
    buttons=[]
    for r in rows[:10]:
        buttons.append([InlineKeyboardButton(text=f"🗑 Снять товар #{r['product_number']}",callback_data=f"complaint:remove:{r['id']}")])
        buttons.append([InlineKeyboardButton(text=f"✅ Закрыть #{r['id']}",callback_data=f"complaint:close:{r['id']}")])
    buttons.append([InlineKeyboardButton(text="🔙 Админ-панель",callback_data="admin_panel")])
    await c.message.edit_text(text,reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)); await c.answer()

@router.callback_query(F.data.startswith("complaint:remove:"))
async def remove(c):
    if c.from_user.id not in ADMIN_IDS: await c.answer("⛔",show_alert=True); return
    cid=int(c.data.split(":")[2]); rows=await get_open_complaints(100); r=next((x for x in rows if x["id"]==cid),None)
    if not r: await c.answer("Жалоба не найдена.",show_alert=True); return
    ad=await get_ad(r["ad_id"]); await set_status(ad["id"],"removed"); await close_complaint(cid); await edit_ad_channel_post(bot_ref,ad,"СНЯТ С ПРОДАЖИ")
    await write_log(bot_ref,c.from_user.id,"COMPLAINT_REMOVE",f"Жалоба #{cid}; товар #{ad['product_number']}")
    await c.answer("Товар снят",show_alert=True); await list_(c)

@router.callback_query(F.data.startswith("complaint:close:"))
async def close(c):
    if c.from_user.id not in ADMIN_IDS: await c.answer("⛔",show_alert=True); return
    cid=int(c.data.split(":")[2]); await close_complaint(cid); await c.answer("Жалоба закрыта"); await list_(c)
