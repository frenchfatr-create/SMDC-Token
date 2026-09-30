import logging
import time
from html import escape

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from config import ADMIN_IDS, SELL_COOLDOWN_SECONDS
from core.constants import KIND_NAMES, PAY_NAMES
from core.utils import moderation_text, format_prices
from db.ads import create_ad, get_ad, set_status
from db.users import save_user
from db.blocks import is_blocked
from db.logs import write_log
from keyboards.common import main_menu, cancel_kb
from keyboards.sell import kind_kb, payment_kb, sell_preview_kb
from keyboards.admin import admin_kb
from states.forms import SellForm

router = Router()
bot_ref = None
last_sell_start = {}


def set_bot(bot):
    global bot_ref
    bot_ref = bot


async def _start(user_id):
    if await is_blocked(user_id):
        return False, "⛔ Вам запрещено выставлять товары на продажу."
    now = time.monotonic()
    previous = last_sell_start.get(user_id, 0)
    if now - previous < SELL_COOLDOWN_SECONDS:
        wait = SELL_COOLDOWN_SECONDS - int(now - previous)
        return False, f"⏳ Подождите {wait} сек. перед новой заявкой."
    last_sell_start[user_id] = now
    return True, ""


async def begin(callback, state):
    ok, msg = await _start(callback.from_user.id)
    if not ok:
        await callback.answer(msg, show_alert=True)
        return
    await save_user(callback.from_user)
    await state.clear()
    await state.set_state(SellForm.kind)
    await write_log(bot_ref, callback.from_user.id, "SELL_START", "Начато выставление товара")
    await callback.message.edit_text(
        "🔥 <b>ВЫСТАВЛЕНИЕ ТОВАРА</b>\n\n"
        "⚠️ Объявление пройдёт модерацию.\n\n"
        "<b>Шаг 1</b> — выберите вид товара:",
        reply_markup=kind_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "sell")
async def sell_start(callback, state):
    await begin(callback, state)


@router.message(Command("sell"))
async def sell_command(message, state):
    ok, msg = await _start(message.from_user.id)
    if not ok:
        await message.answer(msg)
        return
    await save_user(message.from_user)
    await state.clear()
    await state.set_state(SellForm.kind)
    await message.answer("📦 Выберите вид товара:", reply_markup=kind_kb())


@router.callback_query(F.data.startswith("kind:"))
async def sell_kind(callback, state):
    kind = callback.data.split(":", 1)[1]
    if kind not in KIND_NAMES:
        await callback.answer("Неизвестный вид.", show_alert=True)
        return
    await state.update_data(kind=kind)
    await state.set_state(SellForm.game)
    await callback.message.edit_text(
        f"✅ Вид: <b>{KIND_NAMES[kind]}</b>\n\nУкажите игру.",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(SellForm.game)
async def sell_game(message, state):
    if await is_blocked(message.from_user.id):
        await state.clear()
        await message.answer("🚫 Вам запрещено выставлять товары.")
        return
    text = (message.text or "").strip()
    if not 1 <= len(text) <= 100:
        await message.answer("❌ Название игры должно быть от 1 до 100 символов.")
        return
    await state.update_data(game=text)
    await state.set_state(SellForm.description)
    await message.answer("📝 Введите описание товара.", reply_markup=cancel_kb())


@router.message(SellForm.description)
async def sell_description(message, state):
    if await is_blocked(message.from_user.id):
        await state.clear()
        await message.answer("🚫 Вам запрещено выставлять товары.")
        return
    text = (message.text or "").strip()
    if not 1 <= len(text) <= 3000:
        await message.answer("❌ Описание должно быть от 1 до 3000 символов.")
        return
    data = await state.get_data()
    await state.update_data(description=text)

    if data.get("kind") == "currency":
        await state.set_state(SellForm.tokens)
        await message.answer(
            "🪙 <b>Количество токенов</b>\n\n"
            "Введите количество токенов от <b>1</b> до <b>7500</b>.",
            reply_markup=cancel_kb(),
        )
        return

    await state.update_data(media=[])
    await state.set_state(SellForm.media)
    await message.answer(
        "📸 Отправьте фото или видео товара. Можно несколько.\n\n"
        "После последнего файла нажмите /done.",
        reply_markup=cancel_kb(),
    )


@router.message(SellForm.tokens)
async def sell_tokens(message, state):
    if await is_blocked(message.from_user.id):
        await state.clear()
        await message.answer("🚫 Вам запрещено выставлять товары.")
        return
    try:
        tokens = int((message.text or "").strip().replace(" ", ""))
    except ValueError:
        await message.answer("❌ Введите целое число токенов.")
        return
    if not 1 <= tokens <= 7500:
        await message.answer("❌ Количество токенов должно быть от 1 до 7500.")
        return
    await state.update_data(tokens=tokens, media=[])
    await state.set_state(SellForm.media)
    await message.answer(
        "📸 Отправьте фото или видео товара. После последнего — /done.",
        reply_markup=cancel_kb(),
    )


@router.message(SellForm.media, F.photo)
async def sell_photo(message, state):
    if await is_blocked(message.from_user.id):
        await state.clear()
        await message.answer("🚫 Вам запрещено выставлять товары.")
        return
    data = await state.get_data()
    media = data.get("media", [])
    if len(media) >= 10:
        await message.answer("❌ Максимум 10 медиафайлов.")
        return
    media.append({"type": "photo", "file_id": message.photo[-1].file_id})
    await state.update_data(media=media)
    await message.answer(f"📸 Медиа #{len(media)} добавлено. Ещё или /done.")


@router.message(SellForm.media, F.video)
async def sell_video(message, state):
    if await is_blocked(message.from_user.id):
        await state.clear()
        await message.answer("🚫 Вам запрещено выставлять товары.")
        return
    data = await state.get_data()
    media = data.get("media", [])
    if len(media) >= 10:
        await message.answer("❌ Максимум 10 медиафайлов.")
        return
    media.append({"type": "video", "file_id": message.video.file_id})
    await state.update_data(media=media)
    await message.answer(f"🎬 Медиа #{len(media)} добавлено. Ещё или /done.")


@router.message(SellForm.media, Command("done"))
async def sell_media_done(message, state):
    if await is_blocked(message.from_user.id):
        await state.clear()
        await message.answer("🚫 Вам запрещено выставлять товары.")
        return
    data = await state.get_data()
    if not data.get("media"):
        await message.answer("⚠️ Добавьте хотя бы одно фото или видео.")
        return
    await state.set_state(SellForm.contact)
    await message.answer("📞 Введите контакт для связи.", reply_markup=cancel_kb())


@router.message(SellForm.media)
async def sell_media_wrong(message):
    await message.answer("📸 Отправьте фото/видео или нажмите /done.")


@router.message(SellForm.contact)
async def sell_contact(message, state):
    if await is_blocked(message.from_user.id):
        await state.clear()
        await message.answer("🚫 Вам запрещено выставлять товары.")
        return
    text = (message.text or "").strip()
    if not 1 <= len(text) <= 300:
        await message.answer("❌ Контакт должен содержать от 1 до 300 символов.")
        return
    await state.update_data(contact=text)
    await state.set_state(SellForm.payment)
    await message.answer("💳 Выберите способ оплаты:", reply_markup=payment_kb())


def _number(text, stars=False):
    raw = (text or "").replace(",", ".").replace("₽", "").replace("⭐", "").strip()
    value = float(raw)
    if stars:
        value = int(value)
        if value <= 0 or value > 10_000_000:
            raise ValueError
        return value
    if value < 50 or value > 10_000_000:
        raise ValueError
    return value


@router.callback_query(SellForm.payment, F.data.startswith("pay:"))
async def sell_payment(callback, state):
    if await is_blocked(callback.from_user.id):
        await state.clear()
        await callback.answer("🚫 Вам запрещено выставлять товары.", show_alert=True)
        return
    payment = callback.data.split(":", 1)[1]
    if payment not in PAY_NAMES:
        await callback.answer("Неизвестный способ.", show_alert=True)
        return
    await state.update_data(payment=payment)
    await state.set_state(SellForm.price_rub if payment in ("card", "both") else SellForm.price_stars)
    if payment == "card":
        text = "💰 Введите цену в рублях. Минимум — 50 ₽."
    elif payment == "stars":
        text = "⭐ Введите цену в Telegram Stars."
    else:
        text = "💰 Введите цену в рублях. Минимум — 50 ₽."
    await callback.message.edit_text(text, reply_markup=cancel_kb())
    await callback.answer()


@router.message(SellForm.price_rub)
async def price_rub(message, state):
    try:
        value = _number(message.text)
    except ValueError:
        await message.answer("❌ Цена в рублях должна быть числом от 50 ₽.")
        return
    await state.update_data(price_rub=value)
    data = await state.get_data()
    if data.get("payment") == "both":
        await state.set_state(SellForm.price_stars)
        await message.answer("⭐ Теперь введите цену в Stars.")
        return
    await show_preview(message, state)


@router.message(SellForm.price_stars)
async def price_stars(message, state):
    try:
        value = _number(message.text, stars=True)
    except ValueError:
        await message.answer("❌ Введите положительное целое число Stars.")
        return
    await state.update_data(price_stars=value)
    await show_preview(message, state)


async def show_preview(message, state):
    data = await state.get_data()
    payment = data["payment"]
    if payment in ("card", "both") and float(data.get("price_rub", 0) or 0) < 50:
        await message.answer("❌ Минимальная цена — 50 ₽.")
        return
    if payment == "stars" and int(data.get("price_stars", 0) or 0) <= 0:
        await message.answer("❌ Укажите цену в Stars.")
        return
    data["price"] = float(data.get("price_rub", 0) or 0)
    preview = (
        "📝 <b>ПРЕДПРОСМОТР</b>\n\n"
        f"📦 {escape(KIND_NAMES[data['kind']])}\n"
        f"🎮 {escape(data['game'])}\n"
        + (f"🪙 {int(data.get('tokens', 0))} токенов\n" if data.get("tokens") else "")
        + f"📝 {escape(data['description'])}\n"
        f"💰 <b>{format_prices({'price_rub': data.get('price_rub', 0), 'price_stars': data.get('price_stars', 0), 'payment': payment})}</b>\n"
        f"💳 {escape(PAY_NAMES[payment])}\n"
        f"📸 Медиа: {len(data.get('media', []))}\n"
        f"👤 Контакт: {escape(data['contact'])}"
    )
    await state.set_state(SellForm.preview)
    await message.answer(preview, reply_markup=sell_preview_kb())


@router.callback_query(SellForm.preview, F.data == "sell:submit")
async def submit(callback, state):
    if await is_blocked(callback.from_user.id):
        await state.clear()
        await callback.answer("🚫 Вам запрещено выставлять товары.", show_alert=True)
        return
    data = await state.get_data()
    if data.get("kind") == "currency" and not 1 <= int(data.get("tokens", 0) or 0) <= 7500:
        await callback.answer("Количество токенов должно быть от 1 до 7500.", show_alert=True)
        return
    if data.get("payment") in ("card", "both") and float(data.get("price_rub", 0) or 0) < 50:
        await callback.answer("Минимальная цена — 50 ₽.", show_alert=True)
        return

    data["price"] = float(data.get("price_rub", 0) or 0)
    ad_id = await create_ad(data, callback.from_user.id, callback.from_user.username)
    ad = await get_ad(ad_id)

    if not ADMIN_IDS or not bot_ref:
        await set_status(ad_id, "error")
        await state.clear()
        await callback.message.edit_text("⚠️ ADMIN_IDS или BOT не настроен.")
        await callback.answer()
        return

    text = moderation_text(ad, len(data.get("media", [])))
    for admin_id in ADMIN_IDS:
        try:
            await bot_ref.send_message(admin_id, text, reply_markup=admin_kb(ad_id))
            for item in data.get("media", []):
                if item["type"] == "photo":
                    await bot_ref.send_photo(admin_id, item["file_id"])
                else:
                    await bot_ref.send_video(admin_id, item["file_id"])
        except Exception:
            logging.exception("Не удалось отправить заявку админу %s", admin_id)

    await write_log(bot_ref, callback.from_user.id, "SELL_SUBMIT", f"Заявка #{ad_id}")
    await state.clear()
    await callback.message.edit_text(
        f"✅ <b>ЗАЯВКА #{ad_id} ОТПРАВЛЕНА НА МОДЕРАЦИЮ!</b>\n\nОжидайте решения.",
        reply_markup=main_menu(callback.from_user.id),
    )
    await callback.answer()


@router.callback_query(SellForm.preview, F.data == "sell:edit:description")
async def edit_description(callback, state):
    await state.set_state(SellForm.description)
    await callback.message.edit_text("✏️ Введите новое описание:", reply_markup=cancel_kb())
    await callback.answer()


@router.callback_query(SellForm.preview, F.data == "sell:edit:price")
async def edit_price(callback, state):
    data = await state.get_data()
    target = SellForm.price_rub if data.get("payment") in ("card", "both") else SellForm.price_stars
    await state.set_state(target)
    await callback.message.edit_text(
        "💰 Введите новую цену в рублях:" if target == SellForm.price_rub else "⭐ Введите новую цену Stars:",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.callback_query(SellForm.preview, F.data == "sell:edit:media")
async def edit_media(callback, state):
    await state.update_data(media=[])
    await state.set_state(SellForm.media)
    await callback.message.edit_text("📸 Отправьте новые фото/видео. После последнего — /done.", reply_markup=cancel_kb())
    await callback.answer()


@router.callback_query(F.data == "cancel_sell")
async def cancel_sell(callback, state):
    await state.clear()
    await callback.message.edit_text("❌ Действие отменено.", reply_markup=main_menu(callback.from_user.id))
    await callback.answer()


@router.message(Command("cancel"))
async def cancel_command(message, state):
    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=main_menu(message.from_user.id))
