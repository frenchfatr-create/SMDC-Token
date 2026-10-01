from html import escape

from aiogram import Router, F
from aiogram.types import CallbackQuery

from config import (
    ADMIN_IDS,
    RECEIPT_CHAT_ID,
)

from core.constants import ORDER_STATUS_NAMES

from db.orders import (
    get_order,
    set_order_status,
    get_recent_orders,
)

from db.ads import (
    get_ad,
    set_status,
)

from core.channel import edit_ad_channel_post

from keyboards.admin import (
    admin_panel_kb,
    order_admin_kb,
)


router = Router()

bot_ref = None


def set_bot(bot):
    global bot_ref
    bot_ref = bot


def get_ad_id_from_order(order):
    details = order["details"] or ""

    prefix = "marketplace_ad_id="

    if not details.startswith(prefix):
        return None

    try:
        return int(
            details[len(prefix):].split(";")[0]
        )
    except Exception:
        return None


def order_text(order):
    rub = float(order["amount_rub"] or 0)
    stars = int(order["amount_stars"] or 0)

    price_parts = []

    if rub > 0:
        price_parts.append(
            f"{rub:.2f} ₽"
        )

    if stars > 0:
        price_parts.append(
            f"{stars} ⭐"
        )

    price = " / ".join(price_parts) or "—"

    return (
        f"🧾 <b>Заказ {escape(order['order_number'])}</b>\n\n"
        f"👤 Покупатель: "
        f"@{escape(order['username'] or 'не указан')} "
        f"(<code>{order['user_id']}</code>)\n"
        f"🎮 {escape(order['game'])}\n"
        f"📦 {escape(order['product_name'])}\n"
        f"🔢 Количество: {order['quantity']}\n"
        f"💰 Сумма: <b>{escape(price)}</b>\n"
        f"💳 Способ: "
        f"{escape(order['payment_method'] or 'не указан')}\n"
        f"📌 Статус: "
        f"<b>{ORDER_STATUS_NAMES.get(order['status'], order['status'])}</b>"
    )


async def edit_admin_order_message(
    callback: CallbackQuery,
    order,
):
    text = order_text(order)
    markup = order_admin_kb(
        order["order_number"],
        order["status"],
    )

    try:
        if callback.message.photo:
            await callback.message.edit_caption(
                caption=text,
                reply_markup=markup,
            )
        else:
            await callback.message.edit_text(
                text,
                reply_markup=markup,
            )

        return True

    except Exception:
        return False


@router.callback_query(F.data == "admin_orders")
async def list_orders(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(
            "⛔ Нет прав",
            show_alert=True,
        )
        return

    rows = await get_recent_orders()

    if rows:
        body = (
            "📋 <b>ПОСЛЕДНИЕ ЗАКАЗЫ</b>\n\n"
            + "\n".join(
                f"<code>{escape(r['order_number'])}</code> — "
                f"{escape(r['product_name'])} — "
                f"{ORDER_STATUS_NAMES.get(r['status'], r['status'])}"
                for r in rows
            )
        )
    else:
        body = (
            "📋 <b>ПОСЛЕДНИЕ ЗАКАЗЫ</b>\n\n"
            "Заказов пока нет."
        )

    await callback.message.edit_text(
        body,
        reply_markup=admin_panel_kb(),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("order:"))
async def action(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(
            "⛔ Нет прав",
            show_alert=True,
        )
        return

    _, action_name, number = callback.data.split(
        ":",
        2,
    )

    order = await get_order(number)

    if not order:
        await callback.answer(
            "❌ Заказ не найден",
            show_alert=True,
        )
        return

    status_map = {
        "paid": "paid",
        "complete": "completed",
        "reject": "rejected",
    }

    new_status = status_map.get(
        action_name
    )

    if not new_status:
        await callback.answer(
            "❌ Неизвестное действие",
            show_alert=True,
        )
        return

    # Защита от неправильного порядка действий.
    if action_name == "paid":
        if order["status"] != "receipt_sent":
            await callback.answer(
                "Оплату можно подтвердить только после получения чека.",
                show_alert=True,
            )
            return

    if action_name == "complete":
        if order["status"] != "paid":
            await callback.answer(
                "Сначала нужно подтвердить оплату.",
                show_alert=True,
            )
            return

    if action_name == "reject":
        if order["status"] in (
            "completed",
            "rejected",
            "cancelled",
        ):
            await callback.answer(
                "Заказ уже завершён.",
                show_alert=True,
            )
            return

    # При завершении marketplace-товар станет sold.
    ad = None

    if new_status == "completed":
        ad_id = get_ad_id_from_order(order)

        if ad_id:
            ad = await get_ad(ad_id)

            if ad and ad["status"] == "published":
                await set_status(
                    ad_id,
                    "sold",
                )

                if bot_ref:
                    await edit_ad_channel_post(
                        bot_ref,
                        ad,
                        "🔴 ПРОДАН",
                    )

    await set_order_status(
        number,
        new_status,
        callback.from_user.id,
    )

    # Получаем уже обновлённый заказ.
    updated = await get_order(number)

    if updated:
        await edit_admin_order_message(
            callback,
            updated,
        )

    if bot_ref:
        try:
            if new_status == "paid":
                await bot_ref.send_message(
                    order["user_id"],
                    f"💰 <b>Оплата подтверждена!</b>\n\n"
                    f"Заказ: <code>{number}</code>\n"
                    "📦 Заказ передан в выполнение.",
                )

            elif new_status == "completed":
                await bot_ref.send_message(
                    order["user_id"],
                    f"🎉 <b>Заказ завершён!</b>\n\n"
                    f"Заказ: <code>{number}</code>\n"
                    "Спасибо за покупку.",
                )

            elif new_status == "rejected":
                await bot_ref.send_message(
                    order["user_id"],
                    f"❌ <b>Оплата/заказ отклонены.</b>\n\n"
                    f"Заказ: <code>{number}</code>\n"
                    "Если это ошибка, обратитесь к администратору.",
                )

        except Exception:
            pass

    await callback.answer(
        "Статус обновлён"
    )