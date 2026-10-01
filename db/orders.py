from datetime import datetime, timezone

import aiosqlite

from config import DB_PATH


def now():
    return datetime.now(timezone.utc).isoformat()


def make_number(i):
    return f"SM-{datetime.now(timezone.utc):%Y%m%d}-{i:05d}"


async def create_order(
    *,
    user_id,
    username,
    game,
    product_type,
    product_name,
    quantity,
    amount_rub=0,
    amount_stars=0,
    details="",
    payment_method="card",
):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            INSERT INTO orders(
                order_number,
                user_id,
                username,
                game,
                product_type,
                product_name,
                quantity,
                amount_rub,
                amount_stars,
                details,
                payment_method,
                status,
                created_at
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                "TEMP",
                user_id,
                username or "",
                game,
                product_type,
                product_name,
                quantity,
                float(amount_rub or 0),
                int(amount_stars or 0),
                details,
                payment_method,
                "awaiting_payment",
                now(),
            ),
        )

        order_id = cur.lastrowid
        number = make_number(order_id)

        await db.execute(
            "UPDATE orders SET order_number=? WHERE id=?",
            (number, order_id),
        )

        await db.commit()

        return number


async def get_order(number):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cur = await db.execute(
            "SELECT * FROM orders WHERE order_number=?",
            (number,),
        )

        return await cur.fetchone()


async def set_receipt(number, file_id, file_type):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE orders
            SET
                receipt_file_id=?,
                receipt_file_type=?,
                status='receipt_sent'
            WHERE order_number=?
            """,
            (
                file_id,
                file_type,
                number,
            ),
        )

        await db.commit()


async def set_order_status(
    number,
    status,
    admin_id=None,
    note=None,
):
    async with aiosqlite.connect(DB_PATH) as db:
        if status == "paid":
            await db.execute(
                """
                UPDATE orders
                SET
                    status=?,
                    admin_id=?,
                    admin_note=?,
                    paid_at=?
                WHERE order_number=?
                """,
                (
                    status,
                    admin_id,
                    note or "",
                    now(),
                    number,
                ),
            )

        elif status == "completed":
            await db.execute(
                """
                UPDATE orders
                SET
                    status=?,
                    admin_id=?,
                    admin_note=?,
                    completed_at=?
                WHERE order_number=?
                """,
                (
                    status,
                    admin_id,
                    note or "",
                    now(),
                    number,
                ),
            )

        else:
            await db.execute(
                """
                UPDATE orders
                SET
                    status=?,
                    admin_id=?,
                    admin_note=?
                WHERE order_number=?
                """,
                (
                    status,
                    admin_id,
                    note or "",
                    number,
                ),
            )

        await db.commit()


async def get_user_orders(user_id, limit=20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cur = await db.execute(
            """
            SELECT *
            FROM orders
            WHERE user_id=?
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                user_id,
                limit,
            ),
        )

        return await cur.fetchall()


async def get_recent_orders(limit=30):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cur = await db.execute(
            """
            SELECT *
            FROM orders
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )

        return await cur.fetchall()


async def set_payment_method(number, method):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE orders
            SET payment_method=?
            WHERE order_number=?
            """,
            (
                method,
                number,
            ),
        )

        await db.commit()