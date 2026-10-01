from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from db.users import save_user, ensure_referral_code, apply_referral, get_referral_count
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
    await ensure_referral_code(message.from_user.id)

    referral_note = ""
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) == 2:
        ok, _ = await apply_referral(message.from_user.id, parts[1])
        if ok:
            referral_note = "\n\n🎁 Реферал засчитан!"

    await message.answer(
        "🛒 <b>Super Mechs Market</b>\n\n"
        "Добро пожаловать!\n"
        "Здесь можно покупать и выставлять товары." + referral_note,
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

@router.callback_query(F.data == "referral_info")
async def referral_info(callback: CallbackQuery):
    code = await ensure_referral_code(callback.from_user.id)
    count = await get_referral_count(callback.from_user.id)

    me = await callback.bot.get_me()
    link = f"https://t.me/{me.username}?start={code}"

    await callback.answer()

    if callback.message:
        await callback.message.answer(
            "👥 <b>Реферальная система</b>\n\n"
            f"🔗 Твоя ссылка:\n<code>{link}</code>\n\n"
            f"👤 Приглашено: <b>{count}</b>\n\n"
            "Отправляй эту ссылку. Новый пользователь будет "
            "закреплён за тобой навсегда после первого запуска."
        )