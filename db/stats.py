import aiosqlite
from config import DB_PATH


async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        async def one(sql):
            cur = await db.execute(sql)
            row = await cur.fetchone()
            return int(row[0] or 0)

        return {
            "users": await one("SELECT COUNT(*) FROM users"),
            "ads": await one("SELECT COUNT(*) FROM ads"),
            "pending": await one("SELECT COUNT(*) FROM ads WHERE status='pending'"),
            "published": await one("SELECT COUNT(*) FROM ads WHERE status='published'"),
            "sold": await one("SELECT COUNT(*) FROM ads WHERE status='sold'"),
            "removed": await one("SELECT COUNT(*) FROM ads WHERE status='removed'"),
            "orders": await one("SELECT COUNT(*) FROM orders"),
            "complaints": await one("SELECT COUNT(*) FROM complaints WHERE status='open'"),
        }
