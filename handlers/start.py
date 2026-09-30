from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from db.users import save_user
from keyboards.common import main_menu

from middlewares.subscription import (
    check_subscriptions,
    subscription_keyboard,
)


router = Router()


@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()

    subscribed = await check_subscriptions(
        message.bot,
        message.from_user.id,
    )

    if not subscribed:
        await message.answer(
            "🔒 <b>Требуется подписка</b>\n\n"
            "Для использования бота необходимо подписаться "
            "на оба канала:\n\n"
            "📢 TokenShopFiNSuperMechs\n"
            "📢 SMDC Shop\n\n"
            "После подписки нажмите "
            "«✅ Проверить подписку».",
            reply_markup=subscription_keyboard(),
        )
        return

    await save_user(message.from_user)

    await message.answer(
        "🛒 <b>Super Mechs Market</b>\n\n"
        "Добро пожаловать!\n"
        "Здесь можно покупать и выставлять товары.",
        reply_markup=main_menu(message.from_user.id),
    )


@router.callback_query(F.data == "check_required_subscriptions")
async def check_subscription_callback(
    callback: CallbackQuery,
):
    subscribed = await check_subscriptions(
        callback.bot,
        callback.from_user.id,
    )

    if not subscribed:
        await callback.answer(
            "❌ Вы ещё не подписались на оба канала.",
            show_alert=True,
        )
        return

    await callback.answer(
        "✅ Подписка подтверждена!",
    )

    await save_user(callback.from_user)

    if callback.message:
        try:
            await callback.message.edit_text(
                "🛒 <b>Super Mechs Market</b>\n\n"
                "Добро пожаловать!\n"
                "Здесь можно покупать и выставлять товары.",
            )
        except Exception:
            pass

        await callback.message.answer(
            "Выберите действие:",
            reply_markup=main_menu(callback.from_user.id),
        )