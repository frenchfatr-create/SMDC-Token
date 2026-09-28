from aiogram import Router,F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery,Message,InlineKeyboardMarkup,InlineKeyboardButton
from config import ADMIN_IDS
from db.blocks import block_user,unblock_user,get_blocked,is_blocked
from db.logs import write_log
from keyboards.admin import admin_panel_kb,block_action_kb
from states.forms import AdminBlock
router=Router(); bot_ref=None
def set_bot(bot): global bot_ref; bot_ref=bot

@router.callback_query(F.data=="admin_blocks")
async def menu(c):
    if c.from_user.id not in ADMIN_IDS: await c.answer("⛔ Нет прав.",show_alert=True); return
    rows=await get_blocked()
    text="🚫 <b>БЛОКИРОВКИ</b>\n\n"+("\n".join(f"• <code>{r['user_id']}</code> — {r['reason'] or 'без причины'}" for r in rows) if rows else "Список пуст.")
    kb=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 Заблокировать ID",callback_data="admin_block_add")],
        [InlineKeyboardButton(text="🔙 Админ-панель",callback_data="admin_panel")]])
    await c.message.edit_text(text,reply_markup=kb); await c.answer()

@router.callback_query(F.data=="admin_block_add")
async def add(c,state):
    if c.from_user.id not in ADMIN_IDS: await c.answer("⛔",show_alert=True); return
    await state.clear(); await state.set_state(AdminBlock.user_id); await c.message.edit_text("🚫 Введите Telegram ID пользователя:"); await c.answer()

@router.message(AdminBlock.user_id)
async def get_id(m,state):
    try: uid=int((m.text or "").strip())
    except: await m.answer("❌ ID должен быть числом."); return
    await state.update_data(user_id=uid); await state.set_state(AdminBlock.reason); await m.answer("📝 Укажите причину блокировки или отправьте <code>-</code>.")
@router.message(AdminBlock.reason)
async def do_block(m,state):
    d=await state.get_data(); reason=(m.text or "").strip()
    if reason=="-": reason=""
    await block_user(int(d["user_id"]),reason,m.from_user.id); await write_log(bot_ref,m.from_user.id,"BLOCK",f"Пользователь {d['user_id']}; {reason}")
    await state.clear(); await m.answer(f"🚫 Пользователь <code>{d['user_id']}</code> заблокирован.",reply_markup=admin_panel_kb())

@router.callback_query(F.data.startswith("block:"))
async def quick_block(c):
    if c.from_user.id not in ADMIN_IDS: await c.answer("⛔",show_alert=True); return
    uid=int(c.data.split(":")[1]); await block_user(uid,"Блокировка администратором",c.from_user.id); await write_log(bot_ref,c.from_user.id,"BLOCK",f"Пользователь {uid}"); await c.answer("Заблокирован",show_alert=True)
@router.callback_query(F.data.startswith("unblock:"))
async def quick_unblock(c):
    if c.from_user.id not in ADMIN_IDS: await c.answer("⛔",show_alert=True); return
    uid=int(c.data.split(":")[1]); await unblock_user(uid); await write_log(bot_ref,c.from_user.id,"UNBLOCK",f"Пользователь {uid}"); await c.answer("Разблокирован",show_alert=True)
