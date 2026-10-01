from aiogram import Router, F
from aiogram.types import CallbackQuery

from config import ADMIN_IDS, PAYMENT_DETAILS
from db.settings import get_setting
from db.logs import logs_enabled

from keyboards.admin import (
    admin_panel_kb,
    admin_panel_page2_kb,
)

router = Router()


@router.callback_query(F.data == "admin_panel")
async def admin_panel(c: CallbackQuery):
    if c.from_user.id not in ADMIN_IDS:
        await c.answer(
            "⛔ Нет прав администратора.",
            show_alert=True
        )
        return

    watermark = await get_setting(
        "watermark_file_id",
        ""
    )

    payment = await get_setting(
        "payment_details",
        PAYMENT_DETAILS
    )

    on = await logs_enabled()

    await c.message.edit_text(
        "⚙️ <b>АДМИН-ПАНЕЛЬ</b>\n\n"
        f"🖼 Водяной знак: "
        f"<b>{'установлен' if watermark else 'не установлен'}</b>\n"
        f"💳 Реквизиты: "
        f"<b>{'настроены' if payment else 'не настроены'}</b>\n"
        f"📜 Логи: "
        f"<b>{'включены' if on else 'выключены'}</b>\n\n"
        "<b>Страница 1/2</b>\n"
        "Управление магазином:",
        reply_markup=admin_panel_kb(on)
    )

    await c.answer()


@router.callback_query(F.data == "admin_panel_page:2")
async def admin_panel_page2(c: CallbackQuery):
    if c.from_user.id not in ADMIN_IDS:
        await c.answer(
            "⛔ Нет прав администратора.",
            show_alert=True
        )
        return

    await c.message.edit_text(
        "⚙️ <b>АДМИН-ПАНЕЛЬ</b>\n\n"
        "<b>Страница 2/2</b>\n"
        "Дополнительное управление:",
        reply_markup=admin_panel_page2_kb()
    )

    await c.answer()


@router.callback_query(F.data == "admin_panel_page:1")
async def admin_panel_page1(c: CallbackQuery):
    if c.from_user.id not in ADMIN_IDS:
        await c.answer(
            "⛔ Нет прав администратора.",
            show_alert=True
        )
        return

    watermark = await get_setting(
        "watermark_file_id",
        ""
    )

    payment = await get_setting(
        "payment_details",
        PAYMENT_DETAILS
    )

    on = await logs_enabled()

    await c.message.edit_text(
        "⚙️ <b>АДМИН-ПАНЕЛЬ</b>\n\n"
        f"🖼 Водяной знак: "
        f"<b>{'установлен' if watermark else 'не установлен'}</b>\n"
        f"💳 Реквизиты: "
        f"<b>{'настроены' if payment else 'не настроены'}</b>\n"
        f"📜 Логи: "
        f"<b>{'включены' if on else 'выключены'}</b>\n\n"
        "<b>Страница 1/2</b>\n"
        "Управление магазином:",
        reply_markup=admin_panel_kb(on)
    )

    await c.answer()