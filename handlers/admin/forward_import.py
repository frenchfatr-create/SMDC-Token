import logging

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from config import ADMIN_IDS
from states.forms import AdminImport

from db.ads import (
    create_ad,
    get_ad,
    set_published,
    update_product_number,
)

from db.channel_import import (
    imported_ad_id,
    save_imported_ad,
)

from handlers.channel_import import _parse


router = Router()


# =========================
# НАЖАЛИ "ИМПОРТ ОБЪЯВЛЕНИЯ"
# =========================

@router.callback_query(F.data == "admin_import_ad")
async def start_import(
    callback: CallbackQuery,
    state: FSMContext,
):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer(
            "⛔ Нет прав администратора.",
            show_alert=True,
        )
        return

    await state.clear()
    await state.set_state(
        AdminImport.waiting_post
    )

    await callback.message.edit_text(
        "📥 <b>ИМПОРТ ОБЪЯВЛЕНИЯ</b>\n\n"
        "Перешли мне <b>пост из канала</b>, "
        "который нужно добавить в магазин.\n\n"
        "Бот автоматически попробует определить:\n"
        "• номер товара\n"
        "• игру\n"
        "• тип товара\n"
        "• описание\n"
        "• цену\n"
        "• способ оплаты\n"
        "• количество токенов\n"
        "• фото / видео\n\n"
        "❌ Для отмены нажми /cancel"
    )

    await callback.answer()


# =========================
# ОТМЕНА
# =========================

@router.message(
    AdminImport.waiting_post,
    F.text == "/cancel",
)
async def cancel_import(
    message: Message,
    state: FSMContext,
):
    await state.clear()

    await message.answer(
        "❌ Импорт отменён."
    )


# =========================
# ПОЛУЧИЛИ ПЕРЕСЛАННЫЙ ПОСТ
# =========================

@router.message(
    AdminImport.waiting_post,
    F.forward_origin,
)
async def receive_forwarded_post(
    message: Message,
    state: FSMContext,
):
    if not message.from_user:
        return

    if message.from_user.id not in ADMIN_IDS:
        await state.clear()
        return

    origin = message.forward_origin

    if not origin:
        await message.answer(
            "❌ Это не пересланный пост."
        )
        return

    # Telegram channel origin
    source_chat = getattr(
        origin,
        "chat",
        None,
    )

    source_message_id = getattr(
        origin,
        "message_id",
        None,
    )

    if not source_chat or not source_message_id:
        await message.answer(
            "❌ Не удалось определить исходный канал."
        )
        return

    # =========================
    # ПРОВЕРКА НА ДУБЛЬ
    # =========================

    existing = await imported_ad_id(
        source_chat.id,
        source_message_id,
    )

    if existing:
        await message.answer(
            "⚠️ Этот пост уже импортирован.\n\n"
            f"🆔 Товар: #{existing}"
        )

        await state.clear()
        return

    # =========================
    # ТЕКСТ ПОСТА
    # =========================

    raw_text = (
        message.text
        or message.caption
        or ""
    )

    parsed = _parse(raw_text)

    if not parsed:
        await message.answer(
            "❌ Не удалось распознать объявление.\n\n"
            "Проверь, что пересланный пост имеет "
            "формат объявлений магазина."
        )
        return

    # =========================
    # ПРОДАВЕЦ
    # =========================

    username = (
        parsed.get("seller") or ""
    ).lstrip("@")

    # =========================
    # МЕДИА
    # =========================

    media = []

    if message.photo:
        media.append(
            {
                "type": "photo",
                "file_id": message.photo[-1].file_id,
            }
        )

    elif message.video:
        media.append(
            {
                "type": "video",
                "file_id": message.video.file_id,
            }
        )

    # =========================
    # ССЫЛКА НА ИСХОДНЫЙ ПОСТ
    # =========================

    if source_chat.username:
        contact = (
            f"https://t.me/"
            f"{source_chat.username}/"
            f"{source_message_id}"
        )
    else:
        contact = str(
            source_message_id
        )

    # =========================
    # ДАННЫЕ ОБЪЯВЛЕНИЯ
    # =========================

    data = {
        "kind": parsed["kind"],
        "game": parsed["game"],
        "description": parsed["description"],
        "contact": contact,
        "payment": parsed["payment"],
        "price_rub": parsed["price_rub"],
        "price_stars": parsed["price_stars"],
        "tokens": parsed["tokens"],
        "media": media,
    }

    try:
        # =========================
        # СОЗДАЁМ ТОВАР
        # =========================

        ad_id = await create_ad(
            data,
            0,
            username,
        )

        # =========================
        # СОХРАНЯЕМ НОМЕР ИЗ
        # ИСХОДНОГО ПОСТА
        # =========================

        number_updated = await update_product_number(
            ad_id,
            parsed["source_product_number"],
        )

        if not number_updated:
            logging.warning(
                "Не удалось установить номер товара #%s "
                "из исходного поста",
                parsed["source_product_number"],
            )

        # =========================
        # ПОЛУЧАЕМ ТОВАР
        # =========================

        ad = await get_ad(ad_id)

        if not ad:
            await message.answer(
                "❌ Товар создался, "
                "но не удалось получить его из базы."
            )

            await state.clear()
            return

        # =========================
        # СРАЗУ ПУБЛИКУЕМ В БД
        # =========================

        await set_published(
            ad_id,
            None,
        )

        # =========================
        # СОХРАНЯЕМ СВЯЗЬ
        # С ИСХОДНЫМ ПОСТОМ
        # =========================

        saved = await save_imported_ad(
            source_chat.id,
            source_message_id,
            ad_id,
        )

        if not saved:
            logging.warning(
                "Пост уже был импортирован: "
                "%s/%s",
                source_chat.id,
                source_message_id,
            )

            await message.answer(
                "⚠️ Этот пост уже был импортирован."
            )

            await state.clear()
            return

        # =========================
        # ГОТОВО
        # =========================

        price_text = ""

        if ad["price_rub"]:
            price_text = (
                f"{ad['price_rub']} ₽"
            )

        if ad["price_stars"]:
            if price_text:
                price_text += " / "

            price_text += (
                f"{ad['price_stars']} ⭐"
            )

        await message.answer(
            "✅ <b>ОБЪЯВЛЕНИЕ ДОБАВЛЕНО!</b>\n\n"
            f"🆔 Товар: <b>#{ad['product_number']}</b>\n"
            f"🎮 Игра: <b>{ad['game']}</b>\n"
            f"💰 Цена: <b>{price_text}</b>\n"
            f"📦 Тип: <b>{ad['kind']}</b>\n"
            f"👤 Продавец: "
            f"<b>@{username}</b>\n\n"
            "Объявление уже находится в магазине."
        )

        await state.clear()

        logging.info(
            "Admin %s imported channel post "
            "%s/%s as ad #%s",
            message.from_user.id,
            source_chat.id,
            source_message_id,
            ad_id,
        )

    except Exception:
        logging.exception(
            "Ошибка импорта пересланного объявления"
        )

        await message.answer(
            "❌ Произошла ошибка при импорте объявления.\n"
            "Подробности смотри в логах."
        )

        await state.clear()


# =========================
# ЕСЛИ АДМИН ПРИСЛАЛ НЕ ПОСТ
# =========================

@router.message(
    AdminImport.waiting_post,
)
async def wrong_import_message(
    message: Message,
):
    await message.answer(
        "⚠️ Я жду именно <b>пересланный пост из канала</b>.\n\n"
        "Открой пост → «Переслать» → выбери этого бота."
    )