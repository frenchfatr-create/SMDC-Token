import json,logging
from aiogram import Router,F
from aiogram.types import CallbackQuery
from config import ADMIN_IDS,PUBLIC_CHANNEL
from core.utils import channel_post_text,make_post_link
from core.watermark import process_photo_with_watermark
from db.ads import get_ad,set_published,set_status,claim_pending
from db.users import get_user_rating
router=Router(); bot_ref=None
def set_bot(bot):
    global bot_ref; bot_ref=bot
async def send_channel_ad(ad):
    media=json.loads(ad['media_json'] or '[]'); rating,_=await get_user_rating(ad['user_id']); caption=channel_post_text(ad,rating); sent=None
    if media:
        first=media[0]
        if first['type']=='photo': sent=await bot_ref.send_photo(PUBLIC_CHANNEL,await process_photo_with_watermark(bot_ref,first['file_id']),caption=caption)
        elif first['type']=='video': sent=await bot_ref.send_video(PUBLIC_CHANNEL,first['file_id'],caption=caption)
        for item in media[1:]:
            if item['type']=='photo': await bot_ref.send_photo(PUBLIC_CHANNEL,await process_photo_with_watermark(bot_ref,item['file_id']))
            elif item['type']=='video': await bot_ref.send_video(PUBLIC_CHANNEL,item['file_id'])
    else: sent=await bot_ref.send_message(PUBLIC_CHANNEL,caption)
    return sent
@router.callback_query(F.data.startswith('approve:'))
async def approve(c):
    if c.from_user.id not in ADMIN_IDS: await c.answer('⛔ Нет прав',show_alert=True); return
    try:i=int(c.data.split(':')[1])
    except: await c.answer('Ошибка',show_alert=True); return
    ad=await get_ad(i)
    if not ad or ad['status']!='pending': await c.answer('Заявка уже обрабатывается/обработана.',show_alert=True); return
    if not PUBLIC_CHANNEL: await c.answer('PUBLIC_CHANNEL не настроен',show_alert=True); return
    if not await claim_pending(i): await c.answer('Заявку уже взял другой администратор.',show_alert=True); return
    try: sent=await send_channel_ad(ad)
    except Exception:
        logging.exception('publish failed'); await set_status(i,'pending'); await c.answer('Ошибка публикации. Заявка возвращена в ожидание.',show_alert=True); return
    await set_published(i,sent.message_id); link=make_post_link(PUBLIC_CHANNEL,sent.message_id); await c.message.edit_reply_markup(reply_markup=None)
    text=f"✅ <b>Товар #{ad['product_number']} опубликован.</b>"+(f'\n🔎 <a href="{link}">Открыть пост</a>' if link else '')
    await c.message.answer(text)
    try: await bot_ref.send_message(ad['user_id'],f"✅ <b>Товар #{ad['product_number']} одобрен и опубликован!</b>"+(f'\n🔎 <a href="{link}">Открыть объявление</a>' if link else ''))
    except Exception: logging.exception('seller notify failed')
    await c.answer('Опубликовано')
@router.callback_query(F.data.startswith('reject:'))
async def reject(c):
    if c.from_user.id not in ADMIN_IDS: await c.answer('⛔ Нет прав',show_alert=True); return
    try:i=int(c.data.split(':')[1])
    except: await c.answer('Ошибка',show_alert=True); return
    ad=await get_ad(i)
    if not ad or ad['status'] not in ('pending','publishing'): await c.answer('Заявка уже обработана.',show_alert=True); return
    await set_status(i,'rejected'); await c.message.edit_reply_markup(reply_markup=None); await c.message.answer(f"❌ <b>Товар #{ad['product_number']} отклонён.</b>")
    try: await bot_ref.send_message(ad['user_id'],f"❌ <b>Ваш товар #{ad['product_number']} отклонён.</b>")
    except Exception: pass
    await c.answer('Отклонено')
