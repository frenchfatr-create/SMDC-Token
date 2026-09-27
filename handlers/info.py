from aiogram import Router, F
from aiogram.types import CallbackQuery

from keyboards.common import main_menu

router = Router()


@router.callback_query(F.data == "rules")
async def rules(callback: CallbackQuery):
    await callback.message.edit_text(
        "ℹ️ <b>ПРАВИЛА</b>\n\n"
        "1. Публикуйте только реальные объявления.\n"
        "2. Все объявления проходят модерацию.\n"
        "3. Запрещённые товары и услуги не публикуются.\n"
        "4. Не отправляйте лишние персональные данные.\n"
        "5. Администрация может отклонить объявление.\n"
        "6. Не вводите покупателей в заблуждение.\n"
        "7. После продажи обязательно отметьте товар проданным.",
        reply_markup=main_menu(callback.from_user.id),
    )
    await callback.answer()


@router.callback_query(F.data == "support")
async def support(callback: CallbackQuery):
    await callback.message.edit_text(
        "🆘 <b>ПОДДЕРЖКА</b>\n\n"
        "По вопросам работы магазина обратитесь к администрации.",
        reply_markup=main_menu(callback.from_user.id),
    )
    await callback.answer()


@router.callback_query(F.data == "back_menu")
async def back_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🛒 <b>Super Mechs Market</b>\n\nВыберите действие:",
        reply_markup=main_menu(callback.from_user.id),
    )
    await callback.answer()