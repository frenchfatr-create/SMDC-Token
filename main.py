import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN

from db.init import init_db
from db.ads import expire_old_ads, get_ad
from db.logs import write_log

from core.channel import edit_ad_channel_post

from handlers import (
    start,
    sell,
    buy,
    profile,
    info,
    price_edit,
    super_mechs,
)

# Основной админ-роутер оригинального проекта
from handlers.admin import router as admin_router

# Дополнительные админские модули,
# которые есть в оригинальном SMDC-Token-main,
# но не подключены внутри handlers/admin/router.py
from handlers.admin import (
    blocks,
    logs,
    manage_product,
)


async def expiry_worker(bot: Bot):
    """
    Автоматически снимает просроченные объявления
    с продажи.
    """

    while True:
        try:
            ids = await expire_old_ads()

            for ad_id in ids:
                try:
                    ad = await get_ad(ad_id)

                    if not ad:
                        continue

                    # Обновляем статус поста в канале
                    try:
                        await edit_ad_channel_post(
                            bot,
                            ad,
                            "СНЯТ С ПРОДАЖИ",
                        )
                    except Exception:
                        logging.exception(
                            "Не удалось обновить пост "
                            f"для товара #{ad.get('product_number')}"
                        )

                    # Уведомляем продавца
                    try:
                        await bot.send_message(
                            ad["user_id"],
                            (
                                f"⏰ Товар "
                                f"#{ad['product_number']} "
                                f"автоматически снят с продажи "
                                f"из-за истечения срока."
                            ),
                        )
                    except Exception:
                        pass

                    # Записываем лог
                    try:
                        await write_log(
                            bot,
                            ad["user_id"],
                            "AUTO_EXPIRE",
                            f"Товар #{ad['product_number']}",
                        )
                    except Exception:
                        logging.exception(
                            "Не удалось записать AUTO_EXPIRE"
                        )

                except Exception:
                    logging.exception(
                        f"Ошибка обработки просроченного "
                        f"объявления ID={ad_id}"
                    )

        except Exception:
            logging.exception("expiry worker failed")

        await asyncio.sleep(3600)


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    # Создаём бота
    bot = Bot(
        BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        ),
    )

    # Создаём Dispatcher
    dp = Dispatcher()

    # Передаём Bot в модули,
    # которым он нужен для отправки сообщений
    sell.set_bot(bot)
    buy.set_bot(bot)
    price_edit.set_bot(bot)

    # Админские обработчики
    blocks.set_bot(bot)
    manage_product.set_bot(bot)

    # Эти модули уже находятся внутри admin_router,
    # но им также требуется ссылка на Bot.
    from handlers.admin import moderation
    from handlers.admin import orders
    from handlers.admin import product_number
    from handlers.admin import rating

    moderation.set_bot(bot)
    orders.set_bot(bot)
    product_number.set_bot(bot)
    rating.set_bot(bot)

    # Super Mechs
    super_mechs.set_bot(bot)

    # Инициализация БД
    await init_db()

    # -------------------------------------------------
    # ОСНОВНЫЕ РОУТЕРЫ
    # -------------------------------------------------

    dp.include_router(start.router)
    dp.include_router(sell.router)
    dp.include_router(buy.router)
    dp.include_router(profile.router)
    dp.include_router(info.router)
    dp.include_router(price_edit.router)

    # -------------------------------------------------
    # АДМИНКА
    # -------------------------------------------------

    # Основной админский роутер оригинального проекта.
    #
    # Внутри него уже подключены:
    # panel
    # rating
    # watermark
    # payment_details
    # replace_photo
    # products
    # moderation
    # product_number
    # orders
    dp.include_router(admin_router)

    # В оригинальном router.py эти модули не подключены,
    # поэтому подключаем их здесь.
    dp.include_router(blocks.router)
    dp.include_router(logs.router)
    dp.include_router(manage_product.router)

    # -------------------------------------------------
    # SUPER MECHS
    # -------------------------------------------------

    dp.include_router(super_mechs.router)

    # -------------------------------------------------
    # ФОНОВАЯ ЗАДАЧА
    # -------------------------------------------------

    expiry_task = asyncio.create_task(
        expiry_worker(bot)
    )

    logging.info(
        "Super Mechs Market Bot запущен."
    )

    try:
        await dp.start_polling(bot)

    finally:
        expiry_task.cancel()

        try:
            await expiry_task
        except asyncio.CancelledError:
            pass

        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())