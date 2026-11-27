
import asyncio
import logging
import os
from pathlib import Path

from aiohttp import web

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
    channel_import,
)

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


# =====================================
# MINI APP
# =====================================

WEBAPP_DIR = Path(__file__).parent / "webapp"


async def health(request):
    return web.json_response({
        "status": "ok",
        "message": "SMDC Mini App is running"
    })


async def index(request):
    return web.FileResponse(
        WEBAPP_DIR / "index.html"
    )


async def start_web_server():
    app = web.Application()
    
    from webapp_api import init_db, setup_api

    await init_db()
    setup_api(app)

    app.router.add_get("/health", health)
    app.router.add_get("/", index)

    app.router.add_static(
        "/",
        path=str(WEBAPP_DIR),
        show_index=False
    )

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", "8000"))

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port
    )

    await site.start()

    logging.info(
        f"Mini App запущен на порту {port}"
    )

    return runner


# =====================================
# AUTO EXPIRY WORKER
# =====================================

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
            logging.exception(
                "expiry worker failed"
            )

        await asyncio.sleep(3600)


# =====================================
# MAIN
# =====================================

async def main():

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    # Инициализация базы данных
    await init_db()

    # Создание бота
    bot = Bot(
        BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
        ),
    )

    dp = Dispatcher()

    # Передача Bot модулям
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

    # Middleware подписки
    subscription_middleware = SubscriptionMiddleware()

    dp.message.outer_middleware(
        subscription_middleware
    )

    dp.callback_query.outer_middleware(
        subscription_middleware
    )

    # Пользовательские роутеры
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

    # Админские роутеры
    dp.include_router(admin_router)

    dp.include_router(blocks.router)
    dp.include_router(manage_product.router)
    dp.include_router(referrals.router)

    logging.info(
        "Super Mechs Market Bot запущен"
    )

    # Запуск фоновой задачи
    expiry_task = asyncio.create_task(
        expiry_worker(bot)
    )

    web_runner = None

    try:

        # Запуск Mini App
        web_runner = await start_web_server()

        # Запуск Telegram-бота
        await dp.start_polling(bot)

    finally:

        logging.info(
            "Остановка приложения..."
        )

        expiry_task.cancel()

        try:
            await expiry_task
        except asyncio.CancelledError:
            pass

        # Остановка HTTP-сервера
        if web_runner:
            await web_runner.cleanup()

        # Закрытие Telegram-сессии
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
