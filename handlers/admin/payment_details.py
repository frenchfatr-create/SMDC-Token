from html import escape

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_IDS, PAYMENT_DETAILS
from db.settings import get_setting, set_setting
from keyboards.admin import admin_panel_kb
from states.forms import AdminPaymentDetails

router = Router()


def payment_details_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить реквизиты", callback_data="payment_details:edit")],
        [InlineKeyboardButton(text="🗑 Очистить", callback_data="payment_details:clear")],
        [InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin_panel")],
    ])


async def current_details() -> str:
    return await get_setting("payment_details", PAYMENT_DETAILS)


@router.callback_query(F.data == "admin_payment_details")
async def payment_details_menu(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return

    details = await current_details()
    shown = escape(details) if details else "<i>не настроены</i>"
    await callback.message.edit_text(
        "💳 <b>РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ</b>\n\n"
        f"{shown}\n\n"
        "Эти реквизиты бот будет показывать покупателю перед отправкой чека.\n"
        "Изменения сохраняются в базе данных и не пропадут после перезапуска.",
        reply_markup=payment_details_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "payment_details:edit")
async def payment_details_edit(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return

    await state.clear()
    await state.set_state(AdminPaymentDetails.value)
    await callback.message.edit_text(
        "💳 <b>ИЗМЕНЕНИЕ РЕКВИЗИТОВ</b>\n\n"
        "Отправьте одним сообщением реквизиты, которые должны видеть покупатели.\n\n"
        "Например:\n"
        "<code>💳 Карта: 1234 5678 9012 3456\n"
        "Получатель: Иван Иванов\n"
        "После оплаты отправьте чек.</code>\n\n"
        "❗ Не отправляйте сюда секретные данные вроде PIN или CVV.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_payment_details")]
        ]),
    )
    await callback.answer()


@router.message(AdminPaymentDetails.value)
async def payment_details_receive(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        return

    value = (message.text or "").strip()
    if not value:
        await message.answer("❌ Реквизиты не могут быть пустыми.")
        return
    if len(value) > 3500:
        await message.answer("❌ Реквизиты слишком длинные. Максимум — 3500 символов.")
        return

    await set_setting("payment_details", value)
    await state.clear()
    await message.answer(
        "✅ <b>Реквизиты сохранены.</b>\n\n"
        "Теперь новые покупатели будут получать обновлённые реквизиты.",
        reply_markup=admin_panel_kb(),
    )


@router.callback_query(F.data == "payment_details:clear")
async def payment_details_clear(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return

    await set_setting("payment_details", "")
    await callback.message.edit_text(
        "🗑 <b>Реквизиты очищены.</b>\n\n"
        "Перед приёмом новых заказов не забудьте установить актуальные реквизиты.",
        reply_markup=admin_panel_kb(),
    )
    await callback.answer("Реквизиты очищены.")
