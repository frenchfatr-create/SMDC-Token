from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from db.users import save_user
from keyboards.common import main_menu

router = Router()


REQUIRED_CHANNELS = [
    {
        "username": "@TokenShopFiNSuperMechs",
        "url": "https://t.me/TokenShopFiNSuperMechs",
        "name": "TokenShopFiNSuperMechs",
    },
    {
        "username": "@smdcshop",
        "url": "https://t.me/smdcshop",
        "name": "SMDC Shop",
    },
]


def subscription_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📢 TokenShopFiNSuperMechs",
                    url="https://t.me/TokenShopFiNSuperMechs",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📢 SMDC Shop",
                    url="https://t.me/smdcshop",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Проверить подписку",
                    callback_data="check_required_subscriptions",
                )
            ],
        ]
    )


async def check_subscriptions(bot, user_id: int) -> bool:
    for channel in REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(
                chat_id=channel["username"],
                user_id=user_id,
            )

            if member.status in ("creator", "administrator", "member"):
                continue

            # Для restricted проверяем, что пользователь всё ещё участник
            if member.status == "restricted" and getattr(
                member,
                "is_member",
                False,
            ):
                continue

            return False

        except Exception:
            return False

    return True


async def send_subscription_required(message: Message):
    await message.answer(
        "🔒 <b>Для использования бота нужна подписка</b>\n\n"
        "Подпишитесь на оба канала:\n\n"
        "📢 TokenShopFiNSuperMechs\n"
        "📢 SMDC Shop\n\n"
        "После подписки нажмите «✅ Проверить подписку».",
        reply_markup=subscription_keyboard(),
    )


@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()

    subscribed = await check_subscriptions(
        message.bot,
        message.from_user.id,
    )

    if not subscribed:
        await send_subscription_required(message)
        return

    await save_user(message.from_user)

    await message.answer(
        "🛒 <b>Super Mechs Market</b>\n\n"
        "Добро пожаловать!\n"
        "Здесь можно покупать и выставлять товары.",
        reply_markup=main_menu(message.from_user.id),
    )


@router.callback_query(F.data == "check_required_subscriptions")
async def check_subscription_callback(callback: CallbackQuery):
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

    await callback.answer("✅ Подписка подтверждена!")

    await save_user(callback.from_user)

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