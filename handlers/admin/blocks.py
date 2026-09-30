from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_IDS

from db.blocks import (
    block_user,
    unblock_user,
    is_blocked,
    get_blocked_users,
)

from keyboards.admin import admin_panel_kb


router = Router()

bot_ref = None


def set_bot(bot):
    global bot_ref
    bot_ref = bot


# ============================================================
# СОСТОЯНИЯ
# ============================================================

class BlockFlow(StatesGroup):
    waiting_block_id = State()
    waiting_unblock_id = State()


# ============================================================
# ПРОВЕРКА АДМИНА
# ============================================================

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ============================================================
# КЛАВИАТУРА БЛОКИРОВКИ
# ============================================================

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
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="admin_panel",
                )
            ],
        ]
    )


# ============================================================
# ОТКРЫТИЕ РАЗДЕЛА БЛОКИРОВКИ
# ============================================================

@router.callback_query(F.data == "admin_blocks")
async def open_blocks(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Нет прав.",
            show_alert=True,
        )
        return

    await state.clear()

    await callback.message.edit_text(
        "🚫 <b>БЛОКИРОВКА ПОЛЬЗОВАТЕЛЕЙ</b>\n\n"
        "Здесь можно заблокировать пользователя по Telegram ID,\n"
        "снять блокировку или посмотреть список заблокированных.",
        reply_markup=blocks_menu_kb(),
    )

    await callback.answer()


# ============================================================
# ЗАБЛОКИРОВАТЬ
# ============================================================

@router.callback_query(F.data == "admin_block_user")
async def start_block(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Нет прав.",
            show_alert=True,
        )
        return

    await state.clear()
    await state.set_state(
        BlockFlow.waiting_block_id
    )

    await callback.message.edit_text(
        "🔴 <b>БЛОКИРОВКА ПОЛЬЗОВАТЕЛЯ</b>\n\n"
        "Отправь Telegram ID пользователя.\n\n"
        "Например:\n"
        "<code>123456789</code>\n\n"
        "Для отмены нажми /cancel",
    )

    await callback.answer()


@router.message(BlockFlow.waiting_block_id)
async def process_block(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    text = (message.text or "").strip()

    if text.lower() == "/cancel":
        await state.clear()

        await message.answer(
            "❌ Действие отменено.",
            reply_markup=blocks_menu_kb(),
        )
        return

    try:
        user_id = int(text)
    except ValueError:
        await message.answer(
            "❌ Telegram ID должен состоять только из цифр.\n\n"
            "Например:\n"
            "<code>123456789</code>"
        )
        return

    if user_id <= 0:
        await message.answer(
            "❌ Некорректный Telegram ID."
        )
        return

    if user_id in ADMIN_IDS:
        await message.answer(
            "⛔ Нельзя заблокировать администратора."
        )
        return

    try:
        already_blocked = await is_blocked(user_id)

        if already_blocked:
            await state.clear()

            await message.answer(
                f"ℹ️ Пользователь <code>{user_id}</code> "
                "уже заблокирован.",
                reply_markup=blocks_menu_kb(),
            )
            return

        await block_user(user_id)

        await state.clear()

        await message.answer(
            "✅ <b>Пользователь заблокирован.</b>\n\n"
            f"👤 Telegram ID: <code>{user_id}</code>\n\n"
            "Пользователь больше не сможет создавать объявления.",
            reply_markup=blocks_menu_kb(),
        )

        # Если пользователь прямо сейчас находится
        # в каком-либо активном сценарии, пытаемся уведомить его.
        if bot_ref:
            try:
                await bot_ref.send_message(
                    user_id,
                    "🚫 <b>Вы заблокированы.</b>\n\n"
                    "Использование функций продавца временно недоступно.",
                )
            except Exception:
                pass

    except Exception as e:
        await message.answer(
            "❌ Не удалось заблокировать пользователя.\n\n"
            f"<code>{e}</code>"
        )


# ============================================================
# РАЗБЛОКИРОВАТЬ
# ============================================================

@router.callback_query(F.data == "admin_unblock_user")
async def start_unblock(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Нет прав.",
            show_alert=True,
        )
        return

    await state.clear()
    await state.set_state(
        BlockFlow.waiting_unblock_id
    )

    await callback.message.edit_text(
        "🟢 <b>РАЗБЛОКИРОВКА ПОЛЬЗОВАТЕЛЯ</b>\n\n"
        "Отправь Telegram ID пользователя.\n\n"
        "Например:\n"
        "<code>123456789</code>\n\n"
        "Для отмены нажми /cancel",
    )

    await callback.answer()


@router.message(BlockFlow.waiting_unblock_id)
async def process_unblock(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    text = (message.text or "").strip()

    if text.lower() == "/cancel":
        await state.clear()

        await message.answer(
            "❌ Действие отменено.",
            reply_markup=blocks_menu_kb(),
        )
        return

    try:
        user_id = int(text)
    except ValueError:
        await message.answer(
            "❌ Telegram ID должен состоять только из цифр.\n\n"
            "Например:\n"
            "<code>123456789</code>"
        )
        return

    if user_id <= 0:
        await message.answer(
            "❌ Некорректный Telegram ID."
        )
        return

    try:
        blocked = await is_blocked(user_id)

        if not blocked:
            await state.clear()

            await message.answer(
                f"ℹ️ Пользователь <code>{user_id}</code> "
                "не находится в списке заблокированных.",
                reply_markup=blocks_menu_kb(),
            )
            return

        await unblock_user(user_id)

        await state.clear()

        await message.answer(
            "✅ <b>Пользователь разблокирован.</b>\n\n"
            f"👤 Telegram ID: <code>{user_id}</code>",
            reply_markup=blocks_menu_kb(),
        )

        if bot_ref:
            try:
                await bot_ref.send_message(
                    user_id,
                    "🟢 <b>Вы разблокированы.</b>\n\n"
                    "Доступ к функциям бота восстановлен.",
                )
            except Exception:
                pass

    except Exception as e:
        await message.answer(
            "❌ Не удалось разблокировать пользователя.\n\n"
            f"<code>{e}</code>"
        )


# ============================================================
# СПИСОК ЗАБЛОКИРОВАННЫХ
# ============================================================

@router.callback_query(F.data == "admin_blocked_list")
async def blocked_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Нет прав.",
            show_alert=True,
        )
        return

    try:
        users = await get_blocked_users()

        if not users:
            text = (
                "📋 <b>ЗАБЛОКИРОВАННЫЕ ПОЛЬЗОВАТЕЛИ</b>\n\n"
                "Список пуст."
            )
        else:
            lines = []

            for item in users:
                if isinstance(item, dict):
                    user_id = item.get("user_id")
                    username = item.get("username")

                    if username:
                        lines.append(
                            f"🔴 <code>{user_id}</code> — @{username}"
                        )
                    else:
                        lines.append(
                            f"🔴 <code>{user_id}</code>"
                        )

                else:
                    lines.append(
                        f"🔴 <code>{item}</code>"
                    )

            text = (
                "📋 <b>ЗАБЛОКИРОВАННЫЕ ПОЛЬЗОВАТЕЛИ</b>\n\n"
                + "\n".join(lines)
            )

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад",
                        callback_data="admin_blocks",
                    )
                ]
            ]
        )

        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
        )

    except Exception as e:
        await callback.message.edit_text(
            "❌ Не удалось получить список заблокированных.\n\n"
            f"<code>{e}</code>",
            reply_markup=blocks_menu_kb(),
        )

    await callback.answer()


# ============================================================
# НАЗАД В АДМИН-ПАНЕЛЬ
# ============================================================

@router.callback_query(F.data == "admin_panel")
async def back_to_admin(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ Нет прав.",
            show_alert=True,
        )
        return

    await state.clear()

    await callback.message.edit_text(
        "🛠 <b>АДМИН-ПАНЕЛЬ</b>",
        reply_markup=admin_panel_kb(),
    )

    await callback.answer()