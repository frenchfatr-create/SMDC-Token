from datetime import datetime,timezone
import aiosqlite
from config import DB_PATH

async def create_complaint(ad_id,user_id,reason):
    async with aiosqlite.connect(DB_PATH) as db:
        cur=await db.execute("INSERT INTO complaints(ad_id,user_id,reason,created_at) VALUES(?,?,?,?)",(ad_id,user_id,reason,datetime.now(timezone.utc).isoformat())); await db.commit(); return cur.lastrowid

async def get_open_complaints(limit=30):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory=aiosqlite.Row
        cur=await db.execute("SELECT c.*,a.product_number,a.user_id AS seller_id FROM complaints c JOIN ads a ON a.id=c.ad_id WHERE c.status='open' ORDER BY c.id DESC LIMIT ?",(limit,)); return await cur.fetchall()

async def close_complaint(cid):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE complaints SET status='closed' WHERE id=?",(cid,)); await db.commit()
