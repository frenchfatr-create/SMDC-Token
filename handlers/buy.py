import json,logging
from html import escape
from aiogram import Router,F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message,CallbackQuery,InlineKeyboardMarkup,InlineKeyboardButton
from config import ADMIN_IDS
from core.constants import KIND_NAMES,PAY_NAMES
from core.utils import format_prices,rating_text,seller_label
from db.ads import get_published_ads,count_published_ads,get_ad,set_status
from db.users import get_user_rating
from db.favorites import toggle_favorite,is_favorite,get_favorites
from db.complaints import create_complaint
from core.channel import edit_ad_channel_post
from db.blocks import is_blocked
from db.logs import write_log
from keyboards.buy import buy_categories_kb,product_list_kb,product_kb
from keyboards.common import main_menu
from states.forms import BuySearch,ComplaintState
router=Router(); bot_ref=None
def set_bot(bot): global bot_ref; bot_ref=bot

async def show_list(c,kind="all",page=0,search=""):
    total=await count_published_ads(kind if kind!="all" else None,search or None)
    ads=await get_published_ads(kind if kind!="all" else None,search or None,10,page*10)
    title="Все товары" if kind=="all" else KIND_NAMES.get(kind,kind)
    await c.message.edit_text(f"🛍 <b>{escape(title)}</b>\n\nДоступно: <b>{total}</b>",reply_markup=product_list_kb(ads,page,total,kind,search)); await c.answer()

@router.callback_query(F.data=="buy")
async def buy(c): await c.message.edit_text("🛍 <b>МАГАЗИН</b>\n\nВыберите категорию или поиск.",reply_markup=buy_categories_kb()); await c.answer()

@router.callback_query(F.data.startswith("buy:cat:"))
async def category(c):
    kind=c.data.split(":",2)[2]; await show_list(c,kind)

@router.callback_query(F.data.startswith("page:"))
async def page(c):
    _,kind,p,search=c.data.split(":",3); await show_list(c,kind,int(p),search)

@router.callback_query(F.data=="noop")
async def noop(c): await c.answer()

@router.callback_query(F.data=="buy:search")
async def search_start(c,state):
    await state.clear(); await state.set_state(BuySearch.query)
    await c.message.edit_text("🔎 <b>ПОИСК</b>\n\nВведите игру, описание, username продавца или номер товара.",reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена",callback_data="buy")]])); await c.answer()

@router.message(BuySearch.query)
async def search_result(m,state):
    q=(m.text or "").strip()
    if not q: await m.answer("❌ Введите запрос."); return
    await state.clear()
    total=await count_published_ads(search=q); ads=await get_published_ads(search=q,limit=10,offset=0)
    if not ads: await m.answer("🔎 Ничего не найдено.",reply_markup=buy_categories_kb()); return
    await m.answer(f"🔎 <b>Результаты:</b> {escape(q)}\nНайдено: {total}",reply_markup=product_list_kb(ads,0,total,"all",q))

@router.callback_query(F.data.startswith("product:"))
async def product(c):
    try:i=int(c.data.split(":",1)[1])
    except: await c.answer("Ошибка товара.",show_alert=True); return
    ad=await get_ad(i)
    if not ad or ad["status"]!="published": await c.answer("Товар больше недоступен.",show_alert=True); return
    rating,_=await get_user_rating(ad["user_id"]); fav=await is_favorite(c.from_user.id,i)
    text=(f"📦 <b>Товар #{ad['product_number']}</b>\n\n🪪 <b>Вид:</b> {escape(KIND_NAMES.get(ad['kind'],ad['kind']))}\n"
          f"🎮 <b>Игра:</b> {escape(ad['game'])}\n👑 <b>Статус:</b> Не продан\n💰 <b>Цена:</b> {format_prices(ad)}\n"
          f"💳 <b>Оплата:</b> {escape(PAY_NAMES.get(ad['payment'],ad['payment']))}\n\n👤 <b>Продавец (SMDC {rating_text(rating)}/5):</b> {escape(seller_label(ad))}\n\n"
          f"📖 <b>Информация:</b>\n{escape(ad['description'])}")
    media=json.loads(ad["media_json"] or "[]")
    if media:
        try:
            first=media[0]
            if first["type"]=="photo": await c.message.answer_photo(first["file_id"])
            else: await c.message.answer_video(first["file_id"])
        except Exception: logging.exception("media view failed")
    await c.message.answer(text,reply_markup=product_kb(i,ad["user_id"],c.from_user.id,fav)); await c.answer()

@router.callback_query(F.data.startswith("favorite:"))
async def favorite(c):
    i=int(c.data.split(":")[1]); ad=await get_ad(i)
    if not ad or ad["status"]!="published": await c.answer("Товар недоступен.",show_alert=True); return
    result=await toggle_favorite(c.from_user.id,i)
    await c.answer("❤️ Добавлено в избранное" if result else "🤍 Убрано из избранного")
    try: await c.message.edit_reply_markup(reply_markup=product_kb(i,ad["user_id"],c.from_user.id,result))
    except: pass

@router.callback_query(F.data=="favorites")
async def favorites(c):
    rows=await get_favorites(c.from_user.id)
    rows=[r for r in rows if r["status"]=="published"]
    if not rows: await c.message.edit_text("❤️ <b>ИЗБРАННОЕ</b>\n\nПока пусто.",reply_markup=buy_categories_kb()); await c.answer(); return
    await c.message.edit_text("❤️ <b>ИЗБРАННОЕ</b>\n\nВыберите товар:",reply_markup=product_list_kb(rows,0,len(rows))); await c.answer()

@router.callback_query(F.data.startswith("contact:"))
async def contact(c):
    i=int(c.data.split(":")[1]); ad=await get_ad(i)
    if not ad or ad["status"]!="published": await c.answer("Товар недоступен.",show_alert=True); return
    await c.message.answer(f"👤 <b>Контакт продавца</b>\n\n{escape(ad['contact'])}"); await c.answer()

@router.callback_query(F.data.startswith("report:"))
async def complaint_start(c,state):
    i=int(c.data.split(":")[1]); ad=await get_ad(i)
    if not ad or ad["status"]!="published": await c.answer("Товар недоступен.",show_alert=True); return
    await state.clear(); await state.update_data(ad_id=i); await state.set_state(ComplaintState.reason)
    await c.message.answer("⚠️ <b>ЖАЛОБА</b>\n\nОпишите причину жалобы одним сообщением."); await c.answer()

@router.message(ComplaintState.reason)
async def complaint_receive(m,state):
    d=await state.get_data(); reason=(m.text or "").strip()
    if not reason or len(reason)>1000: await m.answer("❌ Напишите причину до 1000 символов."); return
    cid=await create_complaint(int(d["ad_id"]),m.from_user.id,reason); await write_log(bot_ref,m.from_user.id,"COMPLAINT",f"Жалоба #{cid} на товар DB {d['ad_id']}")
    await state.clear(); await m.answer("✅ Жалоба отправлена администрации. Спасибо.",reply_markup=main_menu(m.from_user.id))

@router.callback_query(F.data.startswith("mark_sold:"))
async def mark_sold(c):
    i=int(c.data.split(":")[1]); ad=await get_ad(i)
    if not ad: await c.answer("Товар не найден.",show_alert=True); return
    if c.from_user.id!=ad["user_id"] and c.from_user.id not in ADMIN_IDS: await c.answer("⛔ Нет прав.",show_alert=True); return
    await set_status(i,"sold"); await edit_ad_channel_post(bot_ref,ad,"🔴 ПРОДАН"); await write_log(bot_ref,c.from_user.id,"PRODUCT_SOLD",f"Товар #{ad['product_number']}")
    await c.message.edit_text(f"💰 <b>Товар #{ad['product_number']} отмечен как ПРОДАН.</b>\n\nОн больше не отображается в магазине.",reply_markup=main_menu(c.from_user.id)); await c.answer("Продано")
