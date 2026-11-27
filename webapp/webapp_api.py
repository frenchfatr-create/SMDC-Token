
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

import aiosqlite
from aiohttp import web
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import BOT_TOKEN, ADMIN_IDS, PUBLIC_CHANNEL, DB_PATH
from db.ads import (
    create_ad,
    get_ad,
    claim_pending,
    set_status,
    set_published,
)
from db.logs import write_log
from handlers.admin import moderation


def verify_init_data(init_data):
    if not init_data:
        return None

    try:
        data = dict(parse_qsl(init_data))
        received_hash = data.pop("hash", None)

        if not received_hash:
            return None

        auth_date = int(data.get("auth_date", 0))

        if abs(time.time() - auth_date) > 86400:
            return None

        check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(data.items())
        )

        secret = hmac.new(
            b"WebAppData",
            BOT_TOKEN.encode(),
            hashlib.sha256,
        ).digest()

        calculated = hmac.new(
            secret,
            check_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(calculated, received_hash):
            return None

        return json.loads(data["user"])

    except (ValueError, KeyError, TypeError):
        return None


@web.middleware
async def auth_middleware(request, handler):
    if request.path in ("/", "/health"):
        return await handler(request)

    init_data = request.headers.get("X-Telegram-Init-Data", "")
    user = verify_init_data(init_data)

    if not user:
        return web.json_response(
            {"error": "Unauthorized"},
            status=401,
        )

    request["user"] = user
    return await handler(request)


def is_admin(request):
    return int(request["user"]["id"]) in ADMIN_IDS


async def health(request):
    return web.json_response({"status": "ok"})


async def me(request):
    user = request["user"]

    return web.json_response({
        "id": user["id"],
        "name": user.get("first_name", ""),
        "username": user.get("username", ""),
        "is_admin": is_admin(request),
    })


async def my_ads(request):
    user_id = int(request["user"]["id"])

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cur = await db.execute(
            """
            SELECT id, product_number, game, description,
                   price_rub, status, created_at
            FROM ads
            WHERE user_id=?
            ORDER BY id DESC
            LIMIT 100
            """,
            (user_id,),
        )

        rows = await cur.fetchall()

    return web.json_response([
        dict(row) for row in rows
    ])


async def create_listing(request):
    user = request["user"]

    try:
        data = await request.json()

        title = str(data.get("title", "")).strip()
        description = str(data.get("description", "")).strip()
        price = float(data.get("price", 0))

        if not title or not description:
            raise ValueError("Заполни название и описание")

        if len(title) > 70 or len(description) > 1200:
            raise ValueError("Слишком длинный текст")

        if price <= 0 or price > 100000000:
            raise ValueError("Некорректная цена")

        if data.get("currency", "₽") != "₽":
            raise ValueError("Пока поддерживается только рубль")

    except (ValueError, TypeError):
        return web.json_response(
            {"error": "Проверь название, описание и цену"},
            status=400,
        )

    username = user.get("username", "")

    ad_id = await create_ad(
        {
            "kind": "account",
            "game": title,
            "description": description,
            "contact": (
                f"@{username}" if username else str(user["id"])
            ),
            "payment": "manual",
            "price_rub": price,
            "price_stars": 0,
            "tokens": 0,
            "media": [],
        },
        int(user["id"]),
        username,
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="✅ Принять",
                callback_data=f"approve:{ad_id}",
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=f"reject:{ad_id}",
            ),
        ]]
    )

    for admin_id in ADMIN_IDS:
        try:
            await request.app["bot"].send_message(
                admin_id,
                (
                    f"🆕 <b>Новое объявление #{ad_id}</b>\n\n"
                    f"Название: {title}\n"
                    f"Цена: {price} ₽\n"
                    f"Продавец: {user['id']}\n\n"
                    f"{description}"
                ),
                reply_markup=keyboard,
            )
        except Exception:
            pass

    return web.json_response({
        "success": True,
        "id": ad_id,
        "status": "pending",
    })


async def pending_ads(request):
    if not is_admin(request):
        return web.json_response(
            {"error": "Forbidden"},
            status=403,
        )

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cur = await db.execute(
            """
            SELECT *
            FROM ads
            WHERE status='pending'
            ORDER BY id ASC
            LIMIT 100
            """
        )

        rows = await cur.fetchall()

    result = []

    for row in rows:
        item = dict(row)
        try:
            item["media"] = json.loads(item.get("media_json") or "[]")
        except (ValueError, TypeError):
            item["media"] = []

        result.append(item)

    return web.json_response(result)


async def approve_listing(request):
    if not is_admin(request):
        return web.json_response(
            {"error": "Forbidden"},
            status=403,
        )

    ad_id = int(request.match_info["ad_id"])
    bot = request.app["bot"]

    ad = await get_ad(ad_id)

    if not ad or ad["status"] != "pending":
        return web.json_response(
            {"error": "Заявка уже обработана"},
            status=409,
        )

    if not PUBLIC_CHANNEL:
        return web.json_response(
            {"error": "PUBLIC_CHANNEL не настроен"},
            status=500,
        )

    if not await claim_pending(ad_id):
        return web.json_response(
            {"error": "Заявку уже обрабатывают"},
            status=409,
        )

    try:
        sent = await moderation.send_channel_ad(ad)

        await set_published(ad_id, sent.message_id)

        await write_log(
            bot,
            int(request["user"]["id"]),
            "APPROVE",
            f"Товар #{ad['product_number']} опубликован",
        )

        try:
            await bot.send_message(
                ad["user_id"],
                f"✅ Ваше объявление #{ad['product_number']} одобрено!",
            )
        except Exception:
            pass

        return web.json_response({"success": True})

    except Exception:
        await set_status(ad_id, "pending")

        return web.json_response(
            {"error": "Ошибка публикации. Заявка возвращена в очередь"},
            status=500,
        )


async def reject_listing(request):
    if not is_admin(request):
        return web.json_response(
            {"error": "Forbidden"},
            status=403,
        )

    ad_id = int(request.match_info["ad_id"])
    bot = request.app["bot"]

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            UPDATE ads
            SET status='rejected', updated_at=datetime('now')
            WHERE id=? AND status='pending'
            """,
            (ad_id,),
        )
        await db.commit()

        if cur.rowcount != 1:
            return web.json_response(
                {"error": "Заявка уже обработана"},
                status=409,
            )

    ad = await get_ad(ad_id)

    await write_log(
        bot,
        int(request["user"]["id"]),
        "REJECT",
        f"Товар #{ad['product_number']}",
    )

    try:
        await bot.send_message(
            ad["user_id"],
            f"❌ Ваше объявление #{ad['product_number']} отклонено.",
        )
    except Exception:
        pass

    return web.json_response({"success": True})


def setup_api(bot):
    app = web.Application(
        middlewares=[auth_middleware]
    )

    app["bot"] = bot

    app.router.add_get("/health", health)
    app.router.add_get("/api/me", me)
    app.router.add_get("/api/my-ads", my_ads)
    app.router.add_post("/api/listings", create_listing)
    app.router.add_get("/api/admin/pending", pending_ads)
    app.router.add_post(
        "/api/admin/approve/{ad_id}",
        approve_listing,
    )
    app.router.add_post(
        "/api/admin/reject/{ad_id}",
        reject_listing,
    )

    return app
