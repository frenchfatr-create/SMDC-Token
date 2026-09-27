import json
import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_IDS
from core.constants import KIND_NAMES, PAY_NAMES, STATUS_NAMES
from core.utils import format_price, rating_text, seller_label
from db.ads import get_published_ads, get_ad, set_status
from db.users import get_user_rating
from keyboards.buy import buy_categories_kb, product_list_kb, product_kb
from keyboards.common import main_menu
from states.forms import BuySearch
from html import escape

router = Router()


@router.callback_query(F.data == "buy")
async def buy(callback: CallbackQuery):
    await callback.message.edit_text(
        "🛍 <b>МАГАЗИН</b>\n\n"
        "Выберите категорию или воспользуйтесь поиском.",
        reply_markup=buy_categories_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy:cat:"))
async def buy_category(callback: CallbackQuery):
    kind = callback.data.split(":", 2)[2]
    ads = await get_published_ads(kind=kind)

    if not ads:
        await callback.message.edit_text(
            "🛍 <b>МАГАЗИН</b>\n\n"
            "В этой категории пока нет доступных товаров.",
            reply_markup=buy_categories_kb(),
        )
        await callback.answer()
        return

    title = "Все товары" if kind == "all" else KIND_NAMES.get(kind, kind)
    await callback.message.edit_text(
        f"🛍 <b>{escape(title)}</b>\n\n"
        f"Доступно товаров: <b>{len(ads)}</b>\n\n"
        "Нажмите на товар для просмотра:",
        reply_markup=product_list_kb(ads),
    )
    await callback.answer()


@router.callback_query(F.data == "buy:search")
async def buy_search_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(BuySearch.query)
    await callback.message.edit_text(
        "🔎 <b>ПОИСК ТОВАРОВ</b>\n\n"
        "Введите название игры, описание или часть названия товара.\n\n"
        "Например: <code>Super Mechs</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="buy")]
        ]),
    )
    await callback.answer()


@router.message(BuySearch.query)
async def buy_search_result(message: Message, state: FSMContext):
    query = (message.text or "").strip()
    if not query:
        await message.answer("❌ Введите поисковый запрос.")
        return

    ads = await get_published_ads(search=query)
    await state.clear()

    if not ads:
        await message.answer(
            "🔎 <b>Ничего не найдено.</b>\n\nПопробуйте другой запрос.",
            reply_markup=buy_categories_kb(),
        )
        return

    await message.answer(
        f"🔎 <b>Результаты поиска:</b> {escape(query)}\n\n"
        f"Найдено: <b>{len(ads)}</b>",
        reply_markup=product_list_kb(ads),
    )


@router.callback_query(F.data.startswith("product:"))
async def product_details(callback: CallbackQuery):
    try:
        ad_id = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("Ошибка товара.", show_alert=True)
        return

    ad = await get_ad(ad_id)
    if not ad or ad["status"] != "published":
        await callback.answer("Товар больше недоступен.", show_alert=True)
        return

    rating, _ = await get_user_rating(ad["user_id"])
    seller = seller_label(ad)
    price = format_price(ad["price"])

    text = (
        f"📦 <b>Товар #{ad['product_number']}</b>\n\n"
        f"🪪 <b>Вид:</b> {escape(KIND_NAMES.get(ad['kind'], ad['kind']))}\n"
        f"🎮 <b>Игра:</b> {escape(ad['game'])}\n"
        f"👑 <b>Статус:</b> Не продан\n"
        f"💰 <b>Цена:</b> {price}\n"
        f"💳 <b>Оплата:</b> "
        f"{escape(PAY_NAMES.get(ad['payment'], ad['payment']))}\n\n"
        f"👤 <b>Продавец:</b> {escape(seller)}\n"
        f"⭐ <b>Рейтинг SMDC:</b> {rating_text(rating)}/5\n\n"
        f"📖 <b>Описание:</b>\n{escape(ad['description'])}"
    )

    media = json.loads(ad["media_json"] or "[]")
    if media:
        first = media[0]
        try:
            if first["type"] == "photo":
                await callback.message.answer_photo(first["file_id"])
            elif first["type"] == "video":
                await callback.message.answer_video(first["file_id"])
        except Exception:
            logging.exception("Не удалось показать медиа товара #%s", ad_id)

    await callback.message.answer(
        text,
        reply_markup=product_kb(ad_id, ad["user_id"], callback.from_user.id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("contact:"))
async def contact_seller(callback: CallbackQuery):
    try:
        ad_id = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("Ошибка.", show_alert=True)
        return

    ad = await get_ad(ad_id)
    if not ad or ad["status"] != "published":
        await callback.answer("Товар больше недоступен.", show_alert=True)
        return

    await callback.message.answer(
        "👤 <b>Контакт продавца</b>\n\n"
        f"{escape(ad['contact'])}\n\n"
        "Связывайтесь с продавцом по указанному контакту.",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mark_sold:"))
async def mark_sold(callback: CallbackQuery):
    try:
        ad_id = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("Ошибка.", show_alert=True)
        return

    ad = await get_ad(ad_id)
    if not ad:
        await callback.answer("Товар не найден.", show_alert=True)
        return

    if callback.from_user.id != ad["user_id"] and callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет прав.", show_alert=True)
        return

    await set_status(ad_id, "sold")
    await callback.message.edit_text(
        "💰 <b>Товар отмечен как проданный.</b>\n\n"
        f"Товар #{ad['product_number']} больше не отображается в каталоге.",
        reply_markup=main_menu(callback.from_user.id),
    )
    await callback.answer("Товар отмечен проданным.")