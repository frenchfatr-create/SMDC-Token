from datetime import datetime,timezone
import aiosqlite
from config import DB_PATH

async def toggle_favorite(user_id,ad_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cur=await db.execute("SELECT 1 FROM favorites WHERE user_id=? AND ad_id=?",(user_id,ad_id))
        exists=await cur.fetchone()
        if exists:
            await db.execute("DELETE FROM favorites WHERE user_id=? AND ad_id=?",(user_id,ad_id)); result=False
        else:
            await db.execute("INSERT INTO favorites(user_id,ad_id,created_at) VALUES(?,?,?)",(user_id,ad_id,datetime.now(timezone.utc).isoformat())); result=True
        await db.commit(); return result

async def is_favorite(user_id,ad_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cur=await db.execute("SELECT 1 FROM favorites WHERE user_id=? AND ad_id=?",(user_id,ad_id)); return await cur.fetchone() is not None

async def get_favorites(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory=aiosqlite.Row
        cur=await db.execute("SELECT a.* FROM ads a JOIN favorites f ON f.ad_id=a.id WHERE f.user_id=? ORDER BY f.created_at DESC",(user_id,)); return await cur.fetchall()
