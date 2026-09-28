from datetime import datetime,timezone
import aiosqlite
from config import DB_PATH, LOG_CHAT_ID

async def logs_enabled():
    async with aiosqlite.connect(DB_PATH) as db:
        cur=await db.execute("SELECT value FROM settings WHERE key='logs_enabled'")
        row=await cur.fetchone()
        return bool(row and row[0]=="1")

async def set_logs_enabled(value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('logs_enabled',?)",("1" if value else "0",)); await db.commit()

async def add_log(user_id,event,details=""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO logs(created_at,user_id,event,details) VALUES(?,?,?,?)",(datetime.now(timezone.utc).isoformat(),user_id,event,details)); await db.commit()

async def get_recent_logs(limit=30):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory=aiosqlite.Row
        cur=await db.execute("SELECT * FROM logs ORDER BY id DESC LIMIT ?",(limit,)); return await cur.fetchall()

async def write_log(bot,user_id,event,details=""):
    if not await logs_enabled():
        return
    await add_log(user_id,event,details)
    if bot and LOG_CHAT_ID:
        try:
            await bot.send_message(LOG_CHAT_ID,f"📜 <b>{event}</b>\n👤 ID: <code>{user_id}</code>\n{details}")
        except Exception:
            pass
