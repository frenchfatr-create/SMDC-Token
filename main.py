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

from handlers import start, sell, buy, profile, info, price_edit, super_mechs, channel_import
from handlers.admin import router as admin_router
from handlers.admin import (
    moderation,
    orders,
    product_number,
    blocks,
    manage_product,
    rating,
    complaints,
    referrals,
)

from middlewares.subscription import SubscriptionMiddleware


async def expiry_worker(bot: Bot):
    while True:
        try:
            ids = await expire_old_ads()

            for ad_id in ids:
                ad = await get_ad(ad_id)

                if not ad:
                    continue

                await edit_ad_channel_post(
                    bot,
                    ad,
                    "⚫ СНЯТ С ПРОДАЖИ",
                )

                try:
                    await bot.send_message(
                        ad["user_id"],
                        f"⏰ Товар #{ad['product_number']} "
                        f"автоматически снят с продажи "
                        f"из-за истечения срока.",
                    )
                except Exception:
                    pass

                await write_log(
                    bot,
                    ad["user_id"],
                    "AUTO_EXPIRE",
                    f"Товар #{ad['product_number']}",
                )

        except Exception:
            logging.exception("expiry worker failed")

        await asyncio.sleep(3600)


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    await init_db()

    bot = Bot(
        BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
        ),
    )

    dp = Dispatcher()

    # Передаём Bot модулям, которым он нужен.
    for module in (
        sell,
        buy,
        price_edit,
        super_mechs,
        moderation,
        orders,
        product_number,
        blocks,
        manage_product,
        rating,
        complaints,
        channel_import,
    ):
        module.set_bot(bot)

    # Обязательная подписка.
    #
    # Проверяем и сообщения, и callback-кнопки
    # до передачи их обычным обработчикам.
    subscription_middleware = SubscriptionMiddleware()

    dp.message.outer_middleware(
        subscription_middleware
    )

    dp.callback_query.outer_middleware(
        subscription_middleware
    )

    # Пользовательские роутеры.
    for router in (
        start.router,
        sell.router,
        buy.router,
        profile.router,
        info.router,
        price_edit.router,
        super_mechs.router,
        channel_import.router,
    ):
        dp.include_router(router)

    # Админские роутеры из handlers/admin/router.py.
    dp.include_router(admin_router)

    # Модули, которые не были включены
    # в оригинальный admin/router.py.
    dp.include_router(blocks.router)
    dp.include_router(manage_product.router)
    dp.include_router(referrals.router)

    logging.info(
        "Super Mechs Market Bot запущен"
    )

    expiry_task = asyncio.create_task(
        expiry_worker(bot)
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