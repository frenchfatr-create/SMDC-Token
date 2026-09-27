import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from db.init import init_db

from handlers import start, sell, buy, profile, info, price_edit
from handlers.admin import router as admin_router


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    bot = Bot(
        BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()

    # Прокидываем bot в модули, где он нужен
    sell.set_bot(bot)
    price_edit.set_bot(bot)
    from handlers.admin import moderation
    moderation.set_bot(bot)
    from handlers.admin import orders, product_number
    orders.set_bot(bot)
    product_number.set_bot(bot)
    from handlers import super_mechs
    super_mechs.set_bot(bot)

    dp.include_router(start.router)
    dp.include_router(sell.router)
    dp.include_router(buy.router)
    dp.include_router(profile.router)
    dp.include_router(info.router)
    dp.include_router(price_edit.router)
    dp.include_router(admin_router)
    dp.include_router(super_mechs.router)

    await init_db()
    logging.info("Super Mechs Market Bot запущен.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())