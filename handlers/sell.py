import logging, time
from html import escape
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from config import ADMIN_IDS, SELL_COOLDOWN_SECONDS
from core.constants import KIND_NAMES, PAY_NAMES
from core.utils import moderation_text, format_prices
from db.ads import create_ad, get_ad, set_status
from db.users import save_user
from db.blocks import is_blocked
from db.logs import write_log
from keyboards.common import main_menu, cancel_kb
from keyboards.sell import kind_kb, payment_kb, sell_preview_kb
from keyboards.admin import admin_kb
from states.forms import SellForm

router=Router(); bot_ref=None
last_sell_start={}
def set_bot(bot):
    global bot_ref; bot_ref=bot

async def _start(user_id):
    if await is_blocked(user_id): return False,"⛔ Вам запрещено выставлять товары на продажу."
    now=time.monotonic(); prev=last_sell_start.get(user_id,0)
    if now-prev<SELL_COOLDOWN_SECONDS:
        return False,f"⏳ Подождите {SELL_COOLDOWN_SECONDS-int(now-prev)} сек. перед новой заявкой."
    last_sell_start[user_id]=now; return True,""

async def begin(callback,state):
    ok,msg=await _start(callback.from_user.id)
    if not ok: await callback.answer(msg,show_alert=True); return
    await save_user(callback.from_user); await state.clear(); await state.set_state(SellForm.kind)
    await write_log(bot_ref,callback.from_user.id,"SELL_START","Пользователь начал выставление товара")
    await callback.message.edit_text("🔥 <b>ВЫСТАВЛЕНИЕ ТОВАРА</b>\n\n⚠️ Объявление пройдёт модерацию.\n\n<b>Шаг 1 из 7</b>\nВыберите вид товара:",reply_markup=kind_kb()); await callback.answer()

@router.callback_query(F.data=="sell")
async def sell_start(c,state): await begin(c,state)

@router.callback_query(F.data.startswith("kind:"))
async def sell_kind(c,state):
    kind=c.data.split(":",1)[1]
    if kind not in KIND_NAMES: await c.answer("Неизвестный вид.",show_alert=True); return
    await state.update_data(kind=kind); await state.set_state(SellForm.game)
    await c.message.edit_text(f"✅ Вид: <b>{KIND_NAMES[kind]}</b>\n\n<b>Шаг 2 из 7</b>\nУкажите игру.",reply_markup=cancel_kb()); await c.answer()

@router.message(SellForm.game)
async def sell_game(m,state):
    if await is_blocked(m.from_user.id): await state.clear(); await m.answer("🚫 Вам запрещено выставлять товары."); return
    text=(m.text or "").strip()
    if not text or len(text)>100: await m.answer("❌ Название игры должно быть от 1 до 100 символов."); return
    await state.update_data(game=text); await state.set_state(SellForm.description)
    await m.answer("<b>Шаг 3 из 7</b>\nВведите описание товара.",reply_markup=cancel_kb())

@router.message(SellForm.description)
async def sell_description(m,state):
    if await is_blocked(m.from_user.id): await state.clear(); await m.answer("🚫 Вам запрещено выставлять товары."); return
    text=(m.text or "").strip()
    if not text or len(text)>3000: await m.answer("❌ Описание должно быть от 1 до 3000 символов."); return
    d=await state.get_data()
    if d.get("contact") and d.get("payment") and d.get("media"):
        await state.update_data(description=text)
        await _show_preview(m,state)
        return
    await state.update_data(description=text,media=[]); await state.set_state(SellForm.media)
    await m.answer("<b>Шаг 4 из 7</b>\nОтправьте фото или видео товара. Можно несколько.\n\nПосле последнего файла нажмите /done.",reply_markup=cancel_kb())

@router.message(SellForm.media,F.photo)
async def sell_photo(m,state):
    if await is_blocked(m.from_user.id): await state.clear(); await m.answer("🚫 Вам запрещено выставлять товары."); return
    d=await state.get_data(); media=d.get("media",[])
    if len(media)>=10: await m.answer("❌ Максимум 10 медиафайлов."); return
    media.append({"type":"photo","file_id":m.photo[-1].file_id}); await state.update_data(media=media)
    await m.answer(f"📸 Медиа #{len(media)} добавлено. Отправьте ещё или /done.")

@router.message(SellForm.media,F.video)
async def sell_video(m,state):
    if await is_blocked(m.from_user.id): await state.clear(); await m.answer("🚫 Вам запрещено выставлять товары."); return
    d=await state.get_data(); media=d.get("media",[])
    if len(media)>=10: await m.answer("❌ Максимум 10 медиафайлов."); return
    media.append({"type":"video","file_id":m.video.file_id}); await state.update_data(media=media)
    await m.answer(f"🎬 Медиа #{len(media)} добавлено. Отправьте ещё или /done.")

@router.message(SellForm.media,Command("done"))
async def sell_media_done(m,state):
    if await is_blocked(m.from_user.id): await state.clear(); await m.answer("🚫 Вам запрещено выставлять товары."); return
    d=await state.get_data()
    if not d.get("media"): await m.answer("⚠️ Добавьте хотя бы одно фото или видео."); return
    await state.set_state(SellForm.contact); await m.answer("<b>Шаг 5 из 7</b>\nВведите контакт для связи.",reply_markup=cancel_kb())

@router.message(SellForm.media)
async def sell_media_wrong(m): await m.answer("📸 Отправьте фото/видео или нажмите /done.")

@router.message(SellForm.contact)
async def sell_contact(m,state):
    if await is_blocked(m.from_user.id): await state.clear(); await m.answer("🚫 Вам запрещено выставлять товары."); return
    text=(m.text or "").strip()
    if not text or len(text)>300: await m.answer("❌ Введите корректный контакт."); return
    await state.update_data(contact=text); await state.set_state(SellForm.payment)
    await m.answer("<b>Шаг 6 из 7</b>\nВыберите способ оплаты:",reply_markup=payment_kb())

@router.callback_query(SellForm.payment,F.data.startswith("pay:"))
async def sell_payment(c,state):
    if await is_blocked(c.from_user.id): await state.clear(); await c.answer("🚫 Вам запрещено выставлять товары.",show_alert=True); return
    payment=c.data.split(":",1)[1]
    if payment not in PAY_NAMES: await c.answer("Неизвестный способ.",show_alert=True); return
    await state.update_data(payment=payment)
    if payment=="card":
        await state.set_state(SellForm.price_rub); await c.message.edit_text("💰 Введите цену в рублях.\nНапример: <code>357</code>",reply_markup=cancel_kb())
    elif payment=="stars":
        await state.set_state(SellForm.price_stars); await c.message.edit_text("⭐ Введите цену в Telegram Stars.\nНапример: <code>100</code>",reply_markup=cancel_kb())
    else:
        await state.set_state(SellForm.price_rub); await c.message.edit_text("💰 Введите цену в рублях.\nНапример: <code>357</code>",reply_markup=cancel_kb())
    await c.answer()

def _num(text,stars=False):
    raw=(text or "").replace(",",".").replace("₽","").replace("⭐","").strip()
    v=float(raw)
    if stars:
        v=int(v)
        if v<=0 or v>10_000_000: raise ValueError
    elif v<=0 or v>10_000_000: raise ValueError
    return v

async def _show_preview(m,state):
    d=await state.get_data()
    d["price"]=float(d.get("price_rub",0) or 0)
    text=(f"📝 <b>ПРЕДПРОСМОТР ОБЪЯВЛЕНИЯ</b>\n\n"
          f"📦 {escape(KIND_NAMES[d['kind']])}\n🎮 {escape(d['game'])}\n"
          f"📝 {escape(d['description'])}\n💰 <b>{format_prices({'price_rub':d.get('price_rub',0),'price_stars':d.get('price_stars',0),'payment':d['payment']})}</b>\n"
          f"💳 {escape(PAY_NAMES[d['payment']])}\n📸 Медиа: {len(d.get('media',[]))}\n👤 Контакт: {escape(d['contact'])}")
    await state.set_state(SellForm.preview); await m.answer(text,reply_markup=sell_preview_kb())

@router.message(SellForm.price_rub)
async def price_rub(m,state):
    if await is_blocked(m.from_user.id): await state.clear(); await m.answer("🚫 Вам запрещено выставлять товары."); return
    try: v=_num(m.text)
    except: await m.answer("❌ Введите корректную сумму в рублях."); return
    await state.update_data(price_rub=v)
    d=await state.get_data()
    if d.get("payment")=="both":
        await state.set_state(SellForm.price_stars); await m.answer("⭐ Теперь введите цену в Stars."); return
    await _show_preview(m,state)

@router.message(SellForm.price_stars)
async def price_stars(m,state):
    if await is_blocked(m.from_user.id): await state.clear(); await m.answer("🚫 Вам запрещено выставлять товары."); return
    try: v=_num(m.text,True)
    except: await m.answer("❌ Введите положительное целое число Stars."); return
    await state.update_data(price_stars=int(v)); await _show_preview(m,state)

@router.callback_query(SellForm.preview,F.data=="sell:submit")
async def submit(c,state):
    if await is_blocked(c.from_user.id): await state.clear(); await c.answer("🚫 Вам запрещено выставлять товары.",show_alert=True); return
    d=await state.get_data(); d["price"]=float(d.get("price_rub",0) or 0)
    if d["payment"]=="card" and d["price_rub"]<=0: await c.answer("Укажите цену в рублях.",show_alert=True); return
    if d["payment"]=="stars" and not d.get("price_stars"): await c.answer("Укажите цену Stars.",show_alert=True); return
    ad_id=await create_ad(d,c.from_user.id,c.from_user.username); ad=await get_ad(ad_id)
    if not ADMIN_IDS: await set_status(ad_id,"error"); await state.clear(); await c.message.edit_text("⚠️ ADMIN_IDS не настроен."); await c.answer(); return
    text=moderation_text(ad,len(d.get("media",[])))
    for admin_id in ADMIN_IDS:
        try:
            await bot_ref.send_message(admin_id,text,reply_markup=admin_kb(ad_id))
            for item in d.get("media",[]):
                if item["type"]=="photo": await bot_ref.send_photo(admin_id,item["file_id"])
                else: await bot_ref.send_video(admin_id,item["file_id"])
        except Exception: logging.exception("Не удалось отправить заявку админу %s",admin_id)
    await write_log(bot_ref,c.from_user.id,"SELL_SUBMIT",f"Заявка #{ad_id}")
    await state.clear(); await c.message.edit_text(f"✅ <b>ЗАЯВКА #{ad_id} ОТПРАВЛЕНА НА МОДЕРАЦИЮ!</b>\n\nОжидайте решения.",reply_markup=main_menu(c.from_user.id)); await c.answer()

@router.callback_query(SellForm.preview,F.data=="sell:edit:description")
async def edit_desc(c,state):
    await state.set_state(SellForm.description); await c.message.edit_text("✏️ Введите новое описание:",reply_markup=cancel_kb()); await c.answer()

@router.callback_query(SellForm.preview,F.data=="sell:edit:price")
async def edit_price(c,state):
    d=await state.get_data(); await state.set_state(SellForm.price_rub if d.get("payment")!="stars" else SellForm.price_stars)
    await c.message.edit_text("💰 Введите новую цену в рублях:" if d.get("payment")!="stars" else "⭐ Введите новую цену Stars:",reply_markup=cancel_kb()); await c.answer()

@router.callback_query(SellForm.preview,F.data=="sell:edit:media")
async def edit_media(c,state):
    await state.update_data(media=[]); await state.set_state(SellForm.media); await c.message.edit_text("📸 Отправьте новые фото/видео. После последнего — /done.",reply_markup=cancel_kb()); await c.answer()

@router.callback_query(F.data=="cancel_sell")
async def cancel_sell(c,state):
    await state.clear(); await c.message.edit_text("❌ Действие отменено.",reply_markup=main_menu(c.from_user.id)); await c.answer()

@router.message(Command("sell"))
async def sell_command(m,state):
    ok,msg=await _start(m.from_user.id)
    if not ok: await m.answer(msg); return
    await save_user(m.from_user); await state.clear(); await state.set_state(SellForm.kind); await m.answer("📦 Выберите вид товара:",reply_markup=kind_kb())

@router.message(Command("cancel"))
async def cancel_command(m,state):
    await state.clear(); await m.answer("❌ Действие отменено.",reply_markup=main_menu(m.from_user.id))
