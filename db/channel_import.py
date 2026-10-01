from datetime import datetime, timezone

import aiosqlite

from config import DB_PATH


def now():
    return datetime.now(timezone.utc).isoformat()


async def imported_ad_id(channel_id, message_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """
            SELECT ad_id
            FROM channel_imports
            WHERE channel_id=? AND message_id=?
            """,
            (channel_id, message_id),
        )
        row = await cur.fetchone()
        return row[0] if row else None


async def save_imported_ad(channel_id, message_id, ad_id):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                """
                INSERT INTO channel_imports(
                    channel_id,
                    message_id,
                    ad_id,
                    imported_at
                )
                VALUES(?,?,?,?)
                """,
                (
                    channel_id,
                    message_id,
                    ad_id,
                    now(),
                ),
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            await db.rollback()
            return False
