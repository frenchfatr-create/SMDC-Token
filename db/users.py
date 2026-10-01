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

def make_referral_code(user_id: int) -> str:
    return f"u{int(user_id)}"


async def ensure_referral_code(user_id: int) -> str:
    code = make_referral_code(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET referral_code=COALESCE(referral_code, ?) WHERE user_id=?",
            (code, user_id),
        )
        await db.commit()
    return code


async def apply_referral(user_id: int, referral_code: str):
    code = (referral_code or "").strip().lower()
    if not code:
        return False, "empty"

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT user_id FROM users WHERE LOWER(referral_code)=?",
            (code,),
        )
        row = await cur.fetchone()
        if not row:
            return False, "invalid"

        referrer_id = int(row[0])
        if referrer_id == int(user_id):
            return False, "self"

        cur = await db.execute(
            "SELECT 1 FROM referrals WHERE referred_id=?",
            (user_id,),
        )
        if await cur.fetchone():
            return False, "already"

        await db.execute(
            "INSERT INTO referrals(referrer_id,referred_id) VALUES(?,?)",
            (referrer_id, user_id),
        )
        await db.execute(
            """
            UPDATE users
            SET referred_by=?
            WHERE user_id=? AND (referred_by IS NULL OR referred_by=0)
            """,
            (referrer_id, user_id),
        )
        await db.commit()

    return True, referrer_id


async def get_referral_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM referrals WHERE referrer_id=?",
            (user_id,),
        )
        return int((await cur.fetchone())[0])


async def get_all_referrals(limit: int = 500):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT
                r.referrer_id,
                r.referred_id,
                ru.username AS referrer_username,
                uu.username AS referred_username,
                r.created_at
            FROM referrals r
            LEFT JOIN users ru ON ru.user_id=r.referrer_id
            LEFT JOIN users uu ON uu.user_id=r.referred_id
            ORDER BY r.id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return await cur.fetchall()
