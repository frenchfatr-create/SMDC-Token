from datetime import datetime, timezone
import aiosqlite
from config import DB_PATH


async def save_user(user):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users(user_id, username, first_name, created_at)
            VALUES(?,?,?,?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name
            """,
            (
                user.id,
                user.username or "",
                user.first_name or "",
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        await db.commit()


async def get_user_rating(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT rating, rating_count FROM users WHERE user_id=?",
            (user_id,),
        )
        row = await cur.fetchone()
    if not row:
        return 3.5, 0
    return float(row[0]), int(row[1])


async def set_user_rating(user_id: int, rating: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users(user_id, username, first_name, rating, rating_count, created_at)
            VALUES(?, '', '', ?, 1, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                rating=excluded.rating,
                rating_count=1
            """,
            (user_id, rating, datetime.now(timezone.utc).isoformat()),
        )
        await db.commit()