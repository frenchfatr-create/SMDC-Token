import asyncio,logging
from aiogram import Bot,Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import BOT_TOKEN
from db.init import init_db
from db.ads import expire_old_ads,get_ad,set_status
from db.logs import write_log
from core.channel import edit_ad_channel_post
from handlers import start,sell,buy,profile,info,price_edit
from handlers.admin import router as admin_router
from handlers.admin import moderation,orders,product_number,blocks,manage_product,complaints,rating

async def expiry_worker(bot):
    while True:
        try:
            ids=await expire_old_ads()
            for i in ids:
                ad=await get_ad(i)
                if ad:
                    await edit_ad_channel_post(bot,ad,"СНЯТ С ПРОДАЖИ")
                    try: await bot.send_message(ad["user_id"],f"⏰ Товар #{ad['product_number']} автоматически снят с продажи из-за истечения срока.")
                    except Exception: pass
                    await write_log(bot,ad["user_id"],"AUTO_EXPIRE",f"Товар #{ad['product_number']}")
        except Exception:
            logging.exception("expiry worker failed")
        await asyncio.sleep(3600)

async def main():
    logging.basicConfig(level=logging.INFO,format="%(asctime)s | %(levelname)s | %(message)s")
    bot=Bot(BOT_TOKEN,default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp=Dispatcher()
    sell.set_bot(bot); buy.set_bot(bot); price_edit.set_bot(bot); moderation.set_bot(bot); orders.set_bot(bot); product_number.set_bot(bot)
    blocks.set_bot(bot); manage_product.set_bot(bot); complaints.set_bot(bot); rating.set_bot(bot)
    from handlers import super_mechs
    super_mechs.set_bot(bot)
    dp.include_router(start.router); dp.include_router(sell.router); dp.include_router(buy.router); dp.include_router(profile.router)
    dp.include_router(info.router); dp.include_router(price_edit.router); dp.include_router(admin_router); dp.include_router(super_mechs.router)
    await init_db()
    task=asyncio.create_task(expiry_worker(bot))
    logging.info("Super Mechs Market Bot запущен.")
    try: await dp.start_polling(bot)
    finally: task.cancel(); await bot.session.close()

if __name__=="__main__": asyncio.run(main())
