import json,logging
from core.utils import channel_post_text
from db.users import get_user_rating

async def edit_ad_channel_post(bot,ad,status_text):
    if not bot or not ad["published_message_id"]: return False
    rating,_=await get_user_rating(ad["user_id"])
    caption=channel_post_text(ad,rating,status_text)
    try:
        media=json.loads(ad["media_json"] or "[]")
        if media:
            await bot.edit_message_caption(chat_id=__import__("config").PUBLIC_CHANNEL,message_id=ad["published_message_id"],caption=caption)
        else:
            await bot.edit_message_text(chat_id=__import__("config").PUBLIC_CHANNEL,message_id=ad["published_message_id"],text=caption)
        return True
    except Exception:
        logging.exception("Не удалось обновить пост товара #%s",ad["product_number"])
        return False
