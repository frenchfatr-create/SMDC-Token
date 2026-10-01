from html import escape

from aiogram import Router, F
from aiogram.types import CallbackQuery

from config import ADMIN_IDS

from core.constants import ORDER_STATUS_NAMES

from db.orders import (
    get_order,
    set_order_status,
    get_recent_orders,
)

from keyboards.admin import (
    admin_panel_kb,
    order_admin_kb,
)


router = Router()

bot_ref = None


def set_bot(bot):
    global bot_ref
    bot_ref = bot


def order_text(order):
    rub = float(order["amount_rub"] or 0)
    stars = int(order["amount_stars"] or 0)

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
        if price_parts
        else "—"
    )

    return (
        f"🧾 <b>Заказ {escape(order['order_number'])}</b>\n\n"
        f"👤 Покупатель: "
        f"@{escape(order['username'] or 'не указан')} "
        f"(<code>{order['user_id']}</code>)\n"
        f"🎮 {escape(order['game'])}\n"
        f"📦 {escape(order['product_name'])}\n"
        f"🔢 Количество: {order['quantity']}\n"
        f"💰 Сумма: <b>{escape(price)}</b>\n"
        f"💳 Способ оплаты: "
        f"{escape(order['payment_method'] or 'не указан')}\n\n"
        f"📊 <b>Статус:</b> "
        f"{ORDER_STATUS_NAMES.get(order['status'], order['status'])}"
    )


async def update_order_message(
    callback: CallbackQuery,
    order,
):
    text = order_text(order)

    keyboard = order_admin_kb(
        order["order_number"],
        order["status"],
    )

    try:
        # Чек обычно является photo/document.
        if callback.message.photo:
            await callback.message.edit_caption(
                caption=text,
                reply_markup=keyboard,
            )

        elif callback.message.document:
            await callback.message.edit_caption(
                caption=text,
                reply_markup=keyboard,
            )

        else:
            await callback.message.edit_text(
                text,
                reply_markup=keyboard,
            )

    except Exception:
        # Если сообщение уже нельзя редактировать,
        # просто не ломаем обработчик.
        pass


@router.callback_query(
    F.data == "admin_orders"
)
async def list_orders(
    callback: CallbackQuery,
):
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
                (
                    f"<code>{escape(r['order_number'])}</code> — "
                    f"{escape(r['product_name'])}\n"
                    f"{ORDER_STATUS_NAMES.get(r['status'], r['status'])}"
                )
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


@router.callback_query(
    F.data.startswith("order:")
)
async def action(
    callback: CallbackQuery,
):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(
            "⛔ Нет прав",
            show_alert=True,
        )
        return

    try:
        _, action_name, number = (
            callback.data.split(
                ":",
                2,
            )
        )
    except ValueError:
        await callback.answer(
            "❌ Ошибка заказа",
            show_alert=True,
        )
        return

    order = await get_order(number)

    if not order:
        await callback.answer(
            "❌ Заказ не найден",
            show_alert=True,
        )
        return

    # -------------------------
    # 💰 ОПЛАТА ПРОШЛА
    # -------------------------

    if action_name == "paid":
        if order["status"] != "receipt_sent":
            await callback.answer(
                "Сначала пользователь должен отправить чек.",
                show_alert=True,
            )
            return

        await set_order_status(
            number,
            "paid",
            callback.from_user.id,
        )

        updated = await get_order(
            number
        )

        if updated:
            await update_order_message(
                callback,
                updated,
            )

        if bot_ref:
            try:
                await bot_ref.send_message(
                    order["user_id"],
                    (
                        f"💰 <b>Оплата подтверждена!</b>\n\n"
                        f"Заказ: <code>{number}</code>\n\n"
                        "📦 Заказ передан в выполнение."
                    ),
                )
            except Exception:
                pass

        await callback.answer(
            "✅ Оплата подтверждена"
        )

        return

    # -------------------------
    # 🎉 ЗАКАЗ ВЫПОЛНЕН
    # -------------------------

    if action_name == "complete":
        if order["status"] != "paid":
            await callback.answer(
                "Сначала подтвердите оплату.",
                show_alert=True,
            )
            return

        await set_order_status(
            number,
            "completed",
            callback.from_user.id,
        )

        updated = await get_order(
            number
        )

        if updated:
            await update_order_message(
                callback,
                updated,
            )

        if bot_ref:
            try:
                await bot_ref.send_message(
                    order["user_id"],
                    (
                        f"🎉 <b>Заказ выполнен!</b>\n\n"
                        f"Заказ: <code>{number}</code>\n"
                        "Спасибо за покупку."
                    ),
                )
            except Exception:
                pass

        await callback.answer(
            "🎉 Заказ завершён"
        )

        return

    # -------------------------
    # ❌ ОТКЛОНИТЬ
    # -------------------------

    if action_name == "reject":
        if order["status"] in (
            "completed",
            "rejected",
            "cancelled",
        ):
            await callback.answer(
                "Заказ уже закрыт.",
                show_alert=True,
            )
            return

        await set_order_status(
            number,
            "rejected",
            callback.from_user.id,
        )

        updated = await get_order(
            number
        )

        if updated:
            await update_order_message(
                callback,
                updated,
            )

        if bot_ref:
            try:
                await bot_ref.send_message(
                    order["user_id"],
                    (
                        f"❌ <b>Заказ отклонён.</b>\n\n"
                        f"Заказ: <code>{number}</code>\n\n"
                        "Если это ошибка, обратитесь к администрации."
                    ),
                )
            except Exception:
                pass

        await callback.answer(
            "❌ Заказ отклонён"
        )

        return

    await callback.answer(
        "❌ Неизвестное действие",
        show_alert=True,
    )