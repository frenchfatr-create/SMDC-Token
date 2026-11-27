
import os
import time
import json
import hmac
import hashlib
import logging

from pathlib import Path
from urllib.parse import parse_qsl

import aiosqlite
from aiohttp import web
from config import BOT_TOKEN

logger = logging.getLogger(__name__)

# -----------------------------
# НАСТРОЙКИ
# -----------------------------

DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "webapp_market.db"

ADMIN_IDS = {
    int(value.strip())
    for value in os.getenv("ADMIN_IDS", "").split(",")
    if value.strip().isdigit()
}

# -----------------------------
# БАЗА ДАННЫХ
# -----------------------------

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                price REAL NOT NULL,
                currency TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at INTEGER NOT NULL
            )
        """)

        await db.commit()

    logger.info("WebApp database initialized")


# -----------------------------
# TELEGRAM AUTH
# -----------------------------

def verify_telegram_data(init_data):
    if not init_data or not BOT_TOKEN:
        return None

    try:
        values = dict(
            parse_qsl(init_data, keep_blank_values=True)
        )

        received_hash = values.pop("hash", None)

        if not received_hash:
            return None

        auth_date = int(values.get("auth_date", "0"))

        if time.time() - auth_date > 86400:
            return None

        if auth_date > time.time() + 60:
            return None

        data_check_string = "\n".join(
            f"{key}={value}"
            for key, value in sorted(values.items())
        )

        secret_key = hmac.new(
            b"WebAppData",
            BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(
            calculated_hash,
            received_hash
        ):
            return None

        user = json.loads(values.get("user", "{}"))

        if not isinstance(user.get("id"), int):
            return None

        return user

    except (ValueError, TypeError, json.JSONDecodeError):
        return None


@web.middleware
async def telegram_auth(request, handler):
    if request.path == "/health":
        return await handler(request)

    if not request.path.startswith("/api/"):
        return await handler(request)

    init_data = request.headers.get(
        "X-Telegram-Init-Data", ""
    )

    user = verify_telegram_data(init_data)

    if not user:
        return web.json_response(
            {"error": "Ошибка авторизации Telegram"},
            status=401
        )

    request["tg_user"] = user

    return await handler(request)


# -----------------------------
# АДМИНИСТРАТОР
# -----------------------------

def is_admin(request):
    return request["tg_user"]["id"] in ADMIN_IDS


async def admin_status(request):
    return web.json_response({
        "is_admin": is_admin(request),
        "telegram_id": request["tg_user"]["id"]
    })


# -----------------------------
# ФОРМАТИРОВАНИЕ
# -----------------------------

def row_to_dict(row):
    return {
        "id": row[0],
        "user_id": row[1],
        "username": row[2],
        "title": row[3],
        "description": row[4],
        "price": row[5],
        "currency": row[6],
        "status": row[7],
        "created_at": row[8]
    }


# -----------------------------
# ПУБЛИЧНЫЕ ОБЪЯВЛЕНИЯ
# -----------------------------

async def get_listings(request):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT * FROM listings
            WHERE status = 'approved'
            ORDER BY id DESC
        """)

        rows = await cursor.fetchall()

    return web.json_response([
        row_to_dict(row) for row in rows
    ])


# -----------------------------
# МОИ ОБЪЯВЛЕНИЯ
# -----------------------------

async def get_my_listings(request):
    user_id = request["tg_user"]["id"]

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT * FROM listings
            WHERE user_id = ?
            ORDER BY id DESC
        """, (user_id,))

        rows = await cursor.fetchall()

    return web.json_response([
        row_to_dict(row) for row in rows
    ])


# -----------------------------
# СОЗДАНИЕ ОБЪЯВЛЕНИЯ
# -----------------------------

async def create_listing(request):
    user = request["tg_user"]

    try:
        data = await request.json()

        title = str(
            data.get("title", "")
        ).strip()

        description = str(
            data.get("description", "")
        ).strip()

        price = float(data.get("price", 0))

        currency = str(
            data.get("currency", "₽")
        )

        if not title or len(title) > 80:
            return web.json_response(
                {"error": "Название должно содержать от 1 до 80 символов"},
                status=400
            )

        if len(description) > 2000:
            return web.json_response(
                {"error": "Описание слишком длинное"},
                status=400
            )

        if not 0 < price <= 100000000:
            return web.json_response(
                {"error": "Некорректная цена"},
                status=400
            )

        if currency not in ["₽", "€", "$"]:
            return web.json_response(
                {"error": "Некорректная валюта"},
                status=400
            )

    except (ValueError, TypeError):
        return web.json_response(
            {"error": "Проверь данные объявления"},
            status=400
        )

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("""
                INSERT INTO listings (
                    user_id,
                    username,
                    title,
                    description,
                    price,
                    currency,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """, (
                user["id"],
                user.get("username"),
                title,
                description,
                price,
                currency,
                int(time.time())
            ))

            await db.commit()

            listing_id = cursor.lastrowid

        logger.info(
            "Listing %s created by user %s",
            listing_id,
            user["id"]
        )

        return web.json_response({
            "success": True,
            "id": listing_id,
            "status": "pending",
            "message": "Объявление отправлено на проверку"
        })

    except Exception:
        logger.exception("Failed to create listing")

        return web.json_response(
            {"error": "Не удалось сохранить объявление"},
            status=500
        )


# -----------------------------
# ОЧЕРЕДЬ МОДЕРАЦИИ
# -----------------------------

async def admin_queue(request):
    if not is_admin(request):
        return web.json_response(
            {"error": "Нет доступа"},
            status=403
        )

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT * FROM listings
            WHERE status = 'pending'
            ORDER BY id ASC
        """)

        rows = await cursor.fetchall()

    return web.json_response([
        row_to_dict(row) for row in rows
    ])


# -----------------------------
# ОДОБРЕНИЕ И ОТКЛОНЕНИЕ
# -----------------------------

async def moderate_listing(request):
    if not is_admin(request):
        return web.json_response(
            {"error": "Нет доступа"},
            status=403
        )

    try:
        listing_id = int(
            request.match_info["listing_id"]
        )

        data = await request.json()

        status = data.get("status")

        if status not in ["approved", "rejected"]:
            return web.json_response(
                {"error": "Некорректный статус"},
                status=400
            )

    except (ValueError, TypeError):
        return web.json_response(
            {"error": "Некорректные данные"},
            status=400
        )

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            UPDATE listings
            SET status = ?
            WHERE id = ? AND status = 'pending'
        """, (status, listing_id))

        await db.commit()

        if cursor.rowcount == 0:
            return web.json_response(
                {"error": "Объявление не найдено или уже проверено"},
                status=404
            )

    logger.info(
        "Listing %s moderated: %s",
        listing_id,
        status
    )

    return web.json_response({
        "success": True,
        "status": status
    })


# -----------------------------
# ПОДКЛЮЧЕНИЕ API
# -----------------------------

def setup_api(app):
    app.middlewares.append(telegram_auth)

    app.router.add_get(
        "/api/listings",
        get_listings
    )

    app.router.add_get(
        "/api/my-listings",
        get_my_listings
    )

    app.router.add_post(
        "/api/listings",
        create_listing
    )

    app.router.add_get(
        "/api/admin/status",
        admin_status
    )

    app.router.add_get(
        "/api/admin/queue",
        admin_queue
    )

    app.router.add_post(
        "/api/admin/listings/{listing_id}/moderate",
        moderate_listing
    )

    logger.info("WebApp API routes registered")
