from datetime import datetime,timezone
import aiosqlite
from config import DB_PATH

async def is_blocked(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cur=await db.execute("SELECT 1 FROM blocked_users WHERE user_id=?",(user_id,))
        return await cur.fetchone() is not None

async def block_user(user_id, reason="", blocked_by=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO blocked_users(user_id,reason,blocked_by,created_at) VALUES(?,?,?,?)",(user_id,reason,blocked_by,datetime.now(timezone.utc).isoformat())); await db.commit()

async def unblock_user(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM blocked_users WHERE user_id=?",(user_id,)); await db.commit()

async def get_blocked():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory=aiosqlite.Row
        cur=await db.execute("SELECT * FROM blocked_users ORDER BY created_at DESC"); return await cur.fetchall()
