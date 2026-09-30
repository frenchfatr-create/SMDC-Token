from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_IDS


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


CHECK_CALLBACK = "check_required_subscriptions"


def subscription_keyboard() -> InlineKeyboardMarkup:
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
                    callback_data=CHECK_CALLBACK,
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

            if member.status in (
                "creator",
                "administrator",
                "member",
            ):
                continue

            if (
                member.status == "restricted"
                and getattr(member, "is_member", False)
            ):
                continue

            return False

        except Exception:
            return False

    return True


async def send_subscription_required(target):
    text = (
        "🔒 <b>Требуется подписка</b>\n\n"
        "Для использования бота необходимо подписаться "
        "на оба канала:\n\n"
        "📢 TokenShopFiNSuperMechs\n"
        "📢 SMDC Shop\n\n"
        "После подписки нажмите "
        "«✅ Проверить подписку»."
    )

    if isinstance(target, Message):
        await target.answer(
            text,
            reply_markup=subscription_keyboard(),
        )

    elif isinstance(target, CallbackQuery):
        if target.message:
            await target.message.answer(
                text,
                reply_markup=subscription_keyboard(),
            )

        await target.answer(
            "❌ Сначала подпишитесь на оба канала.",
            show_alert=True,
        )


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[
            [TelegramObject, dict[str, Any]],
            Awaitable[Any],
        ],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:

        user = getattr(event, "from_user", None)

        if user is None:
            return await handler(event, data)

        user_id = user.id

        # Администраторы бота не проходят проверку подписки.
        if user_id in ADMIN_IDS:
            return await handler(event, data)

        # /start должен пройти в start.py,
        # чтобы пользователь получил сообщение о подписке.
        if isinstance(event, Message):
            if event.text and event.text.startswith("/start"):
                return await handler(event, data)

        # Кнопка проверки подписки тоже должна пройти
        # до своего обработчика.
        if isinstance(event, CallbackQuery):
            if event.data == CHECK_CALLBACK:
                return await handler(event, data)

        subscribed = await check_subscriptions(
            event.bot,
            user_id,
        )

        if not subscribed:
            await send_subscription_required(event)
            return None

        return await handler(event, data)