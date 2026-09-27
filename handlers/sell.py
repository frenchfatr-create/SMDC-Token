import logging
from aiogram import Router, F
from aiogram.enums import ContentType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from config import ADMIN_IDS
from core.constants import KIND_NAMES, PAY_NAMES
from core.utils import moderation_text
from db.ads import create_ad, get_ad, set_status
from db.users import save_user
from keyboards.common import main_menu, cancel_kb
from keyboards.sell import kind_kb, payment_kb
from keyboards.admin import admin_kb
from states.forms import SellForm
from html import escape

router = Router()
bot_ref = None  # проставим в main


def set_bot(bot):
    global bot_ref
    bot_ref = bot


@router.callback_query(F.data == "sell")
async def sell_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(SellForm.kind)
    await callback.message.edit_text(
        "🔥 <b>ВЫСТАВЛЕНИЕ ТОВАРА</b>\n\n"
        "⚠️ Объявление пройдёт модерацию.\n\n"
        "<b>Шаг 1 из 7</b>\n"
        "Выберите вид товара:",
        reply_markup=kind_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("kind:"))
async def sell_kind(callback: CallbackQuery, state: FSMContext):
    kind = callback.data.split(":", 1)[1]
    if kind not in KIND_NAMES:
        await callback.answer("Неизвестный вид товара.", show_alert=True)
        return
    await state.update_data(kind=kind)
    await state.set_state(SellForm.game)
    await callback.message.edit_text(
        f"✅ Вид товара: <b>{KIND_NAMES[kind]}</b>\n\n"
        "<b>Шаг 2 из 7</b>\n"
        "Укажите игру.\n\n"
        "Пример: <i>Super Mechs</i>",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(SellForm.game)
async def sell_game(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        await message.answer("❌ Напишите название игры.")
        return
    await state.update_data(game=text)
    await state.set_state(SellForm.description)
    await message.answer(
        "✅ Игра сохранена.\n\n"
        "<b>Шаг 3 из 7</b>\n"
        "Введите описание товара.",
        reply_markup=cancel_kb(),
    )


@router.message(SellForm.description)
async def sell_description(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        await message.answer("❌ Описание не может быть пустым.")
        return
    await state.update_data(description=text, media=[])
    await state.set_state(SellForm.media)
    await message.answer(
        "✅ Описание сохранено.\n\n"
        "<b>Шаг 4 из 7</b>\n"
        "Отправьте фото или видео товара.\n"
        "Можно несколько.\n\n"
        "После последнего файла нажмите /done.",
        reply_markup=cancel_kb(),
    )


@router.message(
    SellForm.media,
    F.content_type.in_({ContentType.PHOTO, ContentType.VIDEO}),
)
async def sell_media(message: Message, state: FSMContext):
    data = await state.get_data()
    media = data.get("media", [])
    if message.photo:
        media.append({"type": "photo", "file_id": message.photo[-1].file_id})
    elif message.video:
        media.append({"type": "video", "file_id": message.video.file_id})
    await state.update_data(media=media)
    await message.answer(
        f"📸 Медиафайл #{len(media)} добавлен.\n\n"
        "Отправьте следующий файл или нажмите /done."
    )


@router.message(SellForm.media, Command("done"))
async def sell_media_done(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data.get("media"):
        await message.answer("⚠️ Добавьте хотя бы одно фото или видео.")
        return
    await state.set_state(SellForm.contact)
    await message.answer(
        "<b>Шаг 5 из 7</b>\n"
        "Введите контакт для связи.\n\n"
        "Например: @username",
        reply_markup=cancel_kb(),
    )


@router.message(SellForm.media)
async def sell_media_wrong(message: Message):
    await message.answer("📸 Отправьте фото/видео или нажмите /done.")


@router.message(SellForm.contact)
async def sell_contact(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        await message.answer("❌ Введите контакт.")
        return
    await state.update_data(contact=text)
    await state.set_state(SellForm.payment)
    await message.answer(
        "<b>Шаг 6 из 7</b>\n"
        "Выберите способ оплаты:",
        reply_markup=payment_kb(),
    )


@router.callback_query(SellForm.payment, F.data.startswith("pay:"))
async def sell_payment(callback: CallbackQuery, state: FSMContext):
    payment = callback.data.split(":", 1)[1]
    if payment not in PAY_NAMES:
        await callback.answer("Неизвестный способ оплаты.", show_alert=True)
        return
    await state.update_data(payment=payment)
    await state.set_state(SellForm.price)
    await callback.message.edit_text(
        f"✅ Способ оплаты: <b>{escape(PAY_NAMES[payment])}</b>\n\n"
        "<b>Шаг 7 из 7</b>\n"
        "Введите цену в рублях.\n\n"
        "Например: <code>357</code>",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(SellForm.price)
async def sell_price(message: Message, state: FSMContext):
    raw = (
        (message.text or "")
        .replace(",", ".")
        .replace("₽", "")
        .strip()
    )
    try:
        price = float(raw)
        if price <= 0 or price > 10_000_000:
            raise ValueError
    except ValueError:
        await message.answer(
            "❌ Введите корректную цену, например <code>357</code>."
        )
        return

    data = await state.get_data()
    data["price"] = price

    ad_id = await create_ad(data, message.from_user.id, message.from_user.username)
    ad = await get_ad(ad_id)
    media_count = len(data.get("media", []))
    text = moderation_text(ad, media_count)

    if not ADMIN_IDS:
        await set_status(ad_id, "error")
        await message.answer(
            "⚠️ Заявка создана, но ADMIN_IDS не настроен."
        )
        await state.clear()
        return

    for admin_id in ADMIN_IDS:
        try:
            await bot_ref.send_message(admin_id, text, reply_markup=admin_kb(ad_id))
            for item in data.get("media", []):
                if item["type"] == "photo":
                    await bot_ref.send_photo(admin_id, item["file_id"])
                elif item["type"] == "video":
                    await bot_ref.send_video(admin_id, item["file_id"])
        except Exception:
            logging.exception("Не удалось отправить заявку админу %s", admin_id)

    await state.clear()
    await message.answer(
        f"✅ <b>ЗАЯВКА #{ad_id} ОТПРАВЛЕНА НА МОДЕРАЦИЮ!</b>\n\n"
        "⏱ Ожидайте решения администратора.\n"
        "📋 Статус можно посмотреть в «Мои объявления».",
        reply_markup=main_menu(message.from_user.id),
    )


@router.callback_query(F.data == "cancel_sell")
async def cancel_sell(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Выставление товара отменено.",
        reply_markup=main_menu(callback.from_user.id),
    )
    await callback.answer()


@router.message(Command("sell"))
async def sell_command(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(SellForm.kind)
    await message.answer("📦 Выберите вид товара:", reply_markup=kind_kb())


@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Действие отменено.",
        reply_markup=main_menu(message.from_user.id),
    )