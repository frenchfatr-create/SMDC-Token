from aiogram import Router,F
from aiogram.types import CallbackQuery
from config import ADMIN_IDS,PAYMENT_DETAILS
from db.settings import get_setting
from db.logs import logs_enabled
from keyboards.admin import admin_panel_kb
router=Router()
@router.callback_query(F.data=="admin_panel")
async def admin_panel(c):
    if c.from_user.id not in ADMIN_IDS: await c.answer("⛔ Нет прав администратора.",show_alert=True); return
    watermark=await get_setting("watermark_file_id",""); payment=await get_setting("payment_details",PAYMENT_DETAILS); on=await logs_enabled()
    await c.message.edit_text(f"⚙️ <b>АДМИН-ПАНЕЛЬ</b>\n\n🖼 Водяной знак: <b>{'установлен' if watermark else 'не установлен'}</b>\n💳 Реквизиты: <b>{'настроены' if payment else 'не настроены'}</b>\n📜 Логи: <b>{'включены' if on else 'выключены'}</b>\n\nУправление магазином:",reply_markup=admin_panel_kb(on)); await c.answer()
