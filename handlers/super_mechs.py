from html import escape

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import (
    ADMIN_IDS,
    PAYMENT_DETAILS,
    RECEIPT_CHAT_ID,
    SUPPORT_CONTACT,
)

from db.settings import get_setting

from core.super_mechs import (
    RUB_PACKS,
    STAR_PACKS,
    BOOST_PACKS,
    rub_tokens,
    star_tokens,
    silver_total,
)

from core.constants import ORDER_STATUS_NAMES

from db.orders import (
    create_order,
    get_order,
    set_receipt,
    get_user_orders,
    set_payment_method,
)

from db.ads import get_ad

from keyboards.sm import (
    sm_menu,
    pack_kb,
    payment_kb,
)

from keyboards.admin import order_admin_kb

from states.forms import OrderFlow


router = Router()

bot_ref = None


def set_bot(bot):
    global bot_ref
    bot_ref = bot


def marketplace_payment_methods(payment):
    if payment == "card":
        return ("card",)

    if payment == "stars":
        return ("stars",)

    if payment == "both":
        return ("card", "stars")

    # На случай старых объявлений.
    return ("card",)


def marketplace_price(ad, method):
    if method == "stars":
        return int(ad["price_stars"] or 0)

    return float(
        ad["price_rub"]
        or ad["price"]
        or 0
    )


def marketplace_price_text(ad):
    parts = []

    rub = float(
        ad["price_rub"]
        or ad["price"]
        or 0
    )

    stars = int(
        ad["price_stars"]
        or 0
    )

    payment = ad["payment"]

    if payment in ("card", "both") and rub > 0:
        parts.append(
            f"{rub:g} ₽"
        )

    if payment in ("stars", "both") and stars > 0:
        parts.append(
            f"{stars} ⭐"
        )

    return " / ".join(parts) or "Цена не указана"


async def _new(
    c,
    state,
    ptype,
    name,
    qty,
    rub=0,
    stars=0,
    details="",
    payment_methods=None,
):
    n = await create_order(
        user_id=c.from_user.id,
        username=c.from_user.username,
        game="Super Mechs",
        product_type=ptype,
        product_name=name,
        quantity=qty,
        amount_rub=rub,
        amount_stars=stars,
        details=details,
        payment_method="card",
    )

    await state.clear()

    await state.update_data(
        order_number=n
    )

    await state.set_state(
        OrderFlow.payment
    )

    price = (
        f"{rub:g} ₽"
        if rub
        else f"{stars} ⭐"
    )

    await c.message.edit_text(
        f"🧾 <b>Заказ {n}</b>\n\n"
        f"🎮 Super Mechs\n"
        f"📦 {escape(name)}\n"
        f"💰 К оплате: <b>{price}</b>\n\n"
        f"Выберите способ оплаты:",
        reply_markup=payment_kb(
            payment_methods
        ),
    )

    await c.answer()


@router.callback_query(
    F.data.startswith("sm_order:ad:")
)
async def order_ad(c, state):
    try:
        ad_id = int(
            c.data.split(":")[-1]
        )

    except Exception:
        await c.answer(
            "❌ Ошибка товара",
            show_alert=True,
        )
        return

    ad = await get_ad(ad_id)

    if not ad:
        await c.answer(
            "❌ Товар не найден.",
            show_alert=True,
        )
        return

    if ad["status"] != "published":
        await c.answer(
            "❌ Товар больше недоступен.",
            show_alert=True,
        )
        return

    payment = ad["payment"]

    methods = marketplace_payment_methods(
        payment
    )

    rub = float(
        ad["price_rub"]
        or ad["price"]
        or 0
    )

    stars = int(
        ad["price_stars"]
        or 0
    )

    # Защита от нулевой цены.
    if payment in ("card", "both") and rub <= 0:
        if payment == "card":
            await c.answer(
                "❌ У товара не указана цена в рублях.",
                show_alert=True,
            )
            return

    if payment in ("stars", "both") and stars <= 0:
        if payment == "stars":
            await c.answer(
                "❌ У товара не указана цена в Stars.",
                show_alert=True,
            )
            return

    # Для both до выбора оплаты создаём заказ
    # с реальными ценами, а не с нулём.
    n = await create_order(
        user_id=c.from_user.id,
        username=c.from_user.username,
        game=ad["game"],
        product_type="marketplace",
        product_name=(
            f"Товар #{ad['product_number']}: "
            f"{ad['game']}"
        ),
        quantity=1,
        amount_rub=rub,
        amount_stars=stars,
        details=f"marketplace_ad_id={ad_id}",
        payment_method="card",
    )

    await state.clear()

    await state.update_data(
        order_number=n,
        marketplace_ad_id=ad_id,
    )

    await state.set_state(
        OrderFlow.payment
    )

    price_text = marketplace_price_text(
        ad
    )

    await c.message.edit_text(
        f"🧾 <b>Заказ {n}</b>\n\n"
        f"📦 Товар #{ad['product_number']}\n"
        f"🎮 {escape(ad['game'])}\n"
        f"💰 К оплате: <b>{escape(price_text)}</b>\n\n"
        "Выберите способ оплаты:",
        reply_markup=payment_kb(
            methods
        ),
    )

    await c.answer()


@router.callback_query(F.data == "sm_menu")
async def menu(c):
    await c.message.edit_text(
        "🎮 <b>SUPER MECHS</b>\n\n"
        "Выберите товар:",
        reply_markup=sm_menu(),
    )

    await c.answer()


@router.callback_query(F.data == "sm:rub")
async def rub(c):
    await c.message.edit_text(
        "💰 <b>ТОКЕНЫ ЗА РУБЛИ</b>\n\n"
        "50 ₽ = 7 500 токенов.\n"
        "Каждые +1 ₽ = +150 токенов.\n\n"
        "Введите свою сумму от 50 ₽.",
        reply_markup=pack_kb(
            "smrub",
            [
                (
                    f"{r} ₽ → {t:,}".replace(
                        ",",
                        " ",
                    ),
                    str(r),
                )
                for r, t in RUB_PACKS
            ],
        ),
    )

    await c.answer()


@router.callback_query(
    F.data.startswith("smrub:")
)
async def rub_pick(c, state):
    x = c.data.split(":")[1]

    if x == "custom":
        await state.clear()

        await state.set_state(
            OrderFlow.quantity
        )

        await state.update_data(
            product_type="tokens_rub"
        )

        await c.message.edit_text(
            "💰 <b>Введите сумму в рублях.</b>\n\n"
            "Минимум: 50 ₽\n"
            "Курс: 1 ₽ = 150 токенов\n\n"
            "Например:\n"
            "50 → 7 500 токенов\n"
            "100 → 15 000 токенов\n"
            "500 → 75 000 токенов"
        )

        await c.answer()
        return

    amount = int(x)

    await _new(
        c,
        state,
        "tokens_rub",
        f"{rub_tokens(amount):,}".replace(
            ",",
            " ",
        ) + " токенов",
        1,
        amount,
        0,
        f"Сумма: {amount} ₽",
    )


@router.message(
    OrderFlow.quantity
)
async def custom_amount(m, state):
    d = await state.get_data()
    product_type = d.get(
        "product_type"
    )

    try:
        value = int(
            (m.text or "").strip()
        )

    except Exception:
        await m.answer(
            "❌ Введите целое число."
        )
        return

    try:
        if product_type == "tokens_rub":
            tokens = rub_tokens(value)

            await state.clear()

            n = await create_order(
                user_id=m.from_user.id,
                username=m.from_user.username,
                game="Super Mechs",
                product_type=product_type,
                product_name=(
                    f"{tokens:,}".replace(
                        ",",
                        " ",
                    )
                    + " токенов"
                ),
                quantity=1,
                amount_rub=value,
                details=f"Сумма: {value} ₽",
                payment_method="card",
            )

            await state.update_data(
                order_number=n
            )

            await state.set_state(
                OrderFlow.payment
            )

            await m.answer(
                f"🧾 <b>Заказ {n}</b>\n\n"
                f"💰 {value} ₽ → "
                f"{tokens:,}".replace(
                    ",",
                    " ",
                )
                + " токенов\n\n"
                "Выберите оплату:",
                reply_markup=payment_kb(),
            )

        elif product_type == "tokens_stars":
            tokens = star_tokens(value)

            await state.clear()

            n = await create_order(
                user_id=m.from_user.id,
                username=m.from_user.username,
                game="Super Mechs",
                product_type=product_type,
                product_name=(
                    f"{tokens:,}".replace(
                        ",",
                        " ",
                    )
                    + " токенов"
                ),
                quantity=1,
                amount_stars=value,
                details=f"Stars: {value}",
                payment_method="stars",
            )

            await state.update_data(
                order_number=n
            )

            await state.set_state(
                OrderFlow.receipt
            )

            await m.answer(
                f"🧾 <b>Заказ {n}</b>\n\n"
                f"⭐ {value} Stars → "
                f"{tokens:,}".replace(
                    ",",
                    " ",
                )
                + " токенов\n\n"
                "После оплаты отправьте "
                "чек/подтверждение сюда."
            )

        elif product_type == "silver":
            total = silver_total(value)

            await state.clear()

            n = await create_order(
                user_id=m.from_user.id,
                username=m.from_user.username,
                game="Super Mechs",
                product_type=product_type,
                product_name=(
                    f"{value} Silver Boxes"
                ),
                quantity=value,
                amount_rub=total,
                details=f"Количество: {value}",
                payment_method="card",
            )

            await state.update_data(
                order_number=n
            )

            await state.set_state(
                OrderFlow.payment
            )

            await m.answer(
                f"🧾 <b>Заказ {n}</b>\n"
                f"📦 {value} Silver Boxes\n"
                f"💰 {total:.2f} ₽\n\n"
                "Выберите оплату:",
                reply_markup=payment_kb(
                    ("card",)
                ),
            )

    except ValueError as error:
        await m.answer(
            f"❌ {error}"
        )


@router.callback_query(
    F.data == "sm:stars"
)
async def stars(c):
    await c.message.edit_text(
        "⭐ <b>ТОКЕНЫ ЗА STARS</b>\n\n"
        "Выберите тариф.",
        reply_markup=pack_kb(
            "smstars",
            [
                (
                    f"{stars} ⭐ → {tokens:,}".replace(
                        ",",
                        " ",
                    ),
                    str(stars),
                )
                for stars, tokens in STAR_PACKS
            ],
        ),
    )

    await c.answer()


@router.callback_query(
    F.data.startswith("smstars:")
)
async def stars_pick(c, state):
    x = c.data.split(":")[1]

    if x == "custom":
        await state.clear()

        await state.set_state(
            OrderFlow.quantity
        )

        await state.update_data(
            product_type="tokens_stars"
        )

        await c.message.edit_text(
            "⭐ Введите количество Stars."
        )

        await c.answer()
        return

    value = int(x)

    await _new(
        c,
        state,
        "tokens_stars",
        f"{star_tokens(value):,}".replace(
            ",",
            " ",
        ) + " токенов",
        1,
        0,
        value,
        f"Stars: {value}",
        ("stars",),
    )


@router.callback_query(
    F.data == "sm:boost"
)
async def boost(c):
    await c.message.edit_text(
        "📈 <b>НАКРУТКА АКЦИЙ</b>\n\n"
        "5 = 30 ₽\n"
        "10 = 80 ₽\n"
        "15 = 130 ₽\n"
        "20 = 180 ₽\n\n"
        "⚠️ Акция должна быть активна "
        "и покупаться за токены. "
        "После начала накрутки возврата нет.",
        reply_markup=pack_kb(
            "smboost",
            [
                (
                    f"{quantity} покупок → {price} ₽",
                    str(quantity),
                )
                for quantity, price in BOOST_PACKS
            ],
            custom=False,
        ),
    )

    await c.answer()


@router.callback_query(
    F.data.startswith("smboost:")
)
async def boost_pick(c, state):
    quantity = int(
        c.data.split(":")[1]
    )

    price = dict(
        BOOST_PACKS
    )[quantity]

    await _new(
        c,
        state,
        "boost",
        f"Накрутка {quantity} покупок",
        quantity,
        price,
        0,
        "Условия подтверждены пользователем перед заказом.",
        ("card",),
    )


@router.callback_query(
    F.data == "sm:silver"
)
async def silver(c, state):
    await state.clear()

    await state.set_state(
        OrderFlow.quantity
    )

    await state.update_data(
        product_type="silver"
    )

    await c.message.edit_text(
        "📦 <b>SILVER БОКСЫ</b>\n\n"
        "1 шт = 1,5 ₽. Минимум 10 шт.\n\n"
        "Введите количество:"
    )

    await c.answer()


@router.callback_query(
    F.data == "sm:fuel"
)
async def fuel(c, state):
    await _new(
        c,
        state,
        "fuel",
        "999 ед. топлива",
        999,
        100,
        0,
        "999 ед. топлива",
        ("card",),
    )


@router.callback_query(
    F.data.startswith("sm_pay:")
)
async def choose_pay(c, state):
    data = await state.get_data()

    method = c.data.split(":")[1]
    number = data.get(
        "order_number"
    )

    if not number:
        await c.answer(
            "❌ Заказ не найден",
            show_alert=True,
        )
        return

    order = await get_order(
        number
    )

    if not order:
        await c.answer(
            "❌ Заказ не найден",
            show_alert=True,
        )
        return

    # Для marketplace проверяем,
    # что выбранная валюта действительно доступна.
    if order["product_type"] == "marketplace":
        if method == "card" and float(
            order["amount_rub"] or 0
        ) <= 0:
            await c.answer(
                "❌ Для этого товара нет цены в ₽.",
                show_alert=True,
            )
            return

        if method == "stars" and int(
            order["amount_stars"] or 0
        ) <= 0:
            await c.answer(
                "❌ Для этого товара нет цены в ⭐.",
                show_alert=True,
            )
            return

    await set_payment_method(
        number,
        method,
    )

    if method == "stars":
        amount = int(
            order["amount_stars"] or 0
        )

        await c.message.edit_text(
            f"⭐ <b>Заказ {number}</b>\n\n"
            f"К оплате: <b>{amount} ⭐</b>\n\n"
            "После оплаты отправьте сюда "
            "скриншот/чек."
        )

        await state.set_state(
            OrderFlow.receipt
        )

    else:
        amount = float(
            order["amount_rub"] or 0
        )

        details = await get_setting(
            "payment_details",
            PAYMENT_DETAILS,
        )

        shown = (
            escape(details)
            if details
            else
            "⚠️ Реквизиты пока не настроены. "
            "Обратитесь к администратору."
        )

        await c.message.edit_text(
            f"💳 <b>Оплата заказа {number}</b>\n\n"
            f"💰 К оплате: <b>{amount:g} ₽</b>\n\n"
            f"<b>Реквизиты:</b>\n"
            f"{shown}\n\n"
            "После оплаты отправьте сюда "
            "фото или файл чека."
        )

        await state.set_state(
            OrderFlow.receipt
        )

    await c.answer()


@router.message(
    OrderFlow.receipt,
    F.photo,
)
async def receipt_photo(
    message,
    state,
):
    await _receipt(
        message,
        state,
        message.photo[-1].file_id,
        "photo",
    )


@router.message(
    OrderFlow.receipt,
    F.document,
)
async def receipt_doc(
    message,
    state,
):
    await _receipt(
        message,
        state,
        message.document.file_id,
        "document",
    )


async def _receipt(
    message,
    state,
    file_id,
    file_type,
):
    data = await state.get_data()

    number = data.get(
        "order_number"
    )

    order = (
        await get_order(number)
        if number
        else None
    )

    if not order:
        await state.clear()

        await message.answer(
            "❌ Заказ не найден."
        )

        return

    await set_receipt(
        number,
        file_id,
        file_type,
    )

    await state.clear()

    # Получаем свежий заказ со статусом receipt_sent.
    order = await get_order(
        number
    )

    if bot_ref and RECEIPT_CHAT_ID:
        rub = float(
            order["amount_rub"] or 0
        )

        stars = int(
            order["amount_stars"] or 0
        )

        price_parts = []

        if rub > 0:
            price_parts.append(
                f"{rub:g} ₽"
            )

        if stars > 0:
            price_parts.append(
                f"{stars} ⭐"
            )

        price = (
            " / ".join(price_parts)
            or "—"
        )

        seller_text = ""

        # Для marketplace достаём продавца.
        details = order["details"] or ""

        if details.startswith(
            "marketplace_ad_id="
        ):
            try:
                ad_id = int(
                    details.split("=")[1]
                    .split(";")[0]
                )

                ad = await get_ad(
                    ad_id
                )

                if ad:
                    seller_text = (
                        f"\n👤 Продавец: "
                        f"@{escape(ad['username'] or 'не указан')} "
                        f"(<code>{ad['user_id']}</code>)"
                    )
            except Exception:
                pass

        text = (
            f"🧾 <b>НОВЫЙ ЧЕК • {number}</b>\n\n"
            f"👤 Покупатель: "
            f"@{escape(message.from_user.username or 'не указан')} "
            f"(<code>{message.from_user.id}</code>)\n"
            f"📦 {escape(order['product_name'])}\n"
            f"💰 Сумма: <b>{escape(price)}</b>"
            f"{seller_text}\n\n"
            f"📊 Статус: "
            f"<b>{ORDER_STATUS_NAMES['receipt_sent']}</b>"
        )

        if file_type == "photo":
            await bot_ref.send_photo(
                RECEIPT_CHAT_ID,
                file_id,
                caption=text,
                reply_markup=order_admin_kb(
                    number,
                    "receipt_sent",
                ),
            )

        else:
            await bot_ref.send_document(
                RECEIPT_CHAT_ID,
                file_id,
                caption=text,
                reply_markup=order_admin_kb(
                    number,
                    "receipt_sent",
                ),
            )

    await message.answer(
        f"✅ <b>Чек принят.</b>\n\n"
        f"Заказ: <code>{number}</code>\n"
        f"Статус: 🧾 Чек отправлен.\n\n"
        "Ожидайте подтверждения оплаты.",
        reply_markup=sm_menu(),
    )


@router.callback_query(
    F.data == "my_orders"
)
async def my_orders(c):
    rows = await get_user_orders(
        c.from_user.id
    )

    if not rows:
        await c.message.edit_text(
            "🧾 <b>МОИ ЗАКАЗЫ</b>\n\n"
            "Заказов пока нет.",
            reply_markup=sm_menu(),
        )

        await c.answer()
        return

    body = (
        "🧾 <b>МОИ ЗАКАЗЫ</b>\n\n"
        + "\n".join(
            f"<code>{r['order_number']}</code> — "
            f"{escape(r['product_name'])} — "
            f"{ORDER_STATUS_NAMES.get(r['status'], r['status'])}"
            for r in rows
        )
    )

    await c.message.edit_text(
        body,
        reply_markup=sm_menu(),
    )

    await c.answer()