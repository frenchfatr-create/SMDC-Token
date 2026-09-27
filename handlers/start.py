from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from db.users import save_user
from keyboards.common import main_menu

router = Router()


@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await save_user(message.from_user)
    await message.answer(
        "🛒 <b>Super Mechs Market</b>\n\n"
        "Добро пожаловать!\n"
        "Здесь можно покупать и выставлять товары.",
        reply_markup=main_menu(message.from_user.id),
    )