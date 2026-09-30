from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_IDS
from db.blocks import (
    block_user,
    unblock_user,
    is_blocked,
    get_blocked,
)

router = Router()

_bot: Bot | None = None


def set_bot(bot: Bot):
    global _bot
    _bot = bot


class BlockStates(StatesGroup):
    waiting_block_id = State()
    waiting_unblock_id = State()


def blocks_menu_kb():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔴 Заблокировать",
                    callback_data="admin_block_user",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🟢 Разблокировать",
                    callback_data="admin_unblock_user",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Список заблокированных",
                    callback_data="admin_blocked_list",
                )
            ],
        ]
    )


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.callback_query(F.data == "admin_blocks")
async def blocks_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await callback.message.edit_text(
        "🚫 <b>Управление блокировками</b>\n\n"
        "Выберите действие:",
        reply_markup=blocks_menu_kb(),
    )

    await callback.answer()


@router.callback_query(F.data == "admin_block_user")
async def start_block_user(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await state.set_state(BlockStates.waiting_block_id)

    await callback.message.answer(
        "🔴 <b>Блокировка пользователя</b>\n\n"
        "Отправьте Telegram ID пользователя."
    )

    await callback.answer()


@router.message(BlockStates.waiting_block_id)
async def process_block_user(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    try:
        user_id = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer(
            "❌ Некорректный ID.\n"
            "Отправьте Telegram ID числом."
        )
        return

    if await is_blocked(user_id):
        await message.answer(
            f"ℹ️ Пользователь <code>{user_id}</code> уже заблокирован."
        )
        await state.clear()
        return

    await block_user(
        user_id=user_id,
        reason="Заблокирован администратором",
        blocked_by=message.from_user.id,
    )

    await state.clear()

    await message.answer(
        f"🔴 Пользователь <code>{user_id}</code> заблокирован."
    )

    # Если пользователь сейчас взаимодействует с ботом,
    # дополнительно уведомляем его.
    if _bot:
        try:
            await _bot.send_message(
                user_id,
                "🚫 Вы были заблокированы в боте.",
            )
        except Exception:
            pass


@router.callback_query(F.data == "admin_unblock_user")
async def start_unblock_user(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await state.set_state(BlockStates.waiting_unblock_id)

    await callback.message.answer(
        "🟢 <b>Разблокировка пользователя</b>\n\n"
        "Отправьте Telegram ID пользователя."
    )

    await callback.answer()


@router.message(BlockStates.waiting_unblock_id)
async def process_unblock_user(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    try:
        user_id = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer(
            "❌ Некорректный ID.\n"
            "Отправьте Telegram ID числом."
        )
        return

    if not await is_blocked(user_id):
        await message.answer(
            f"ℹ️ Пользователь <code>{user_id}</code> не находится в блокировке."
        )
        await state.clear()
        return

    await unblock_user(user_id)

    await state.clear()

    await message.answer(
        f"🟢 Пользователь <code>{user_id}</code> разблокирован."
    )

    if _bot:
        try:
            await _bot.send_message(
                user_id,
                "🟢 Вы были разблокированы в боте.",
            )
        except Exception:
            pass


@router.callback_query(F.data == "admin_blocked_list")
async def blocked_users_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    rows = await get_blocked()

    if not rows:
        text = (
            "📋 <b>Заблокированные пользователи</b>\n\n"
            "Список пуст."
        )
    else:
        lines = [
            "📋 <b>Заблокированные пользователи</b>",
            "",
        ]

        for row in rows:
            user_id = row["user_id"]
            reason = row["reason"] or "Причина не указана"
            created_at = row["created_at"] or ""

            lines.append(
                f"🔴 <code>{user_id}</code>\n"
                f"Причина: {reason}\n"
                f"Дата: {created_at}\n"
            )

        text = "\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=blocks_menu_kb(),
    )

    await callback.answer()