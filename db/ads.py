import json
from datetime import datetime, timezone, timedelta
import aiosqlite
from config import DB_PATH, AD_EXPIRY_DAYS

def now(): return datetime.now(timezone.utc).isoformat()

async def create_ad(data, user_id, username):
    rub = float(data.get("price_rub", data.get("price", 0)) or 0)
    stars = int(data.get("price_stars", 0) or 0)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("""INSERT INTO ads(user_id,username,kind,game,description,contact,payment,price,price_rub,price_stars,status,created_at,media_json,product_number,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (user_id,username or "",data["kind"],data["game"],data["description"],data["contact"],data["payment"],rub,rub,stars,"pending",now(),json.dumps(data.get("media",[]),ensure_ascii=False),None,now()))
        i = cur.lastrowid
        await db.execute("UPDATE ads SET product_number=? WHERE id=?", (i,i))
        await db.commit()
        return i

async def get_ad(i):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory=aiosqlite.Row
        cur=await db.execute("SELECT * FROM ads WHERE id=?",(i,))
        return await cur.fetchone()

async def get_ad_by_product_number(n):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory=aiosqlite.Row
        cur=await db.execute("SELECT * FROM ads WHERE product_number=?",(n,))
        return await cur.fetchone()

async def claim_pending(i):
    async with aiosqlite.connect(DB_PATH) as db:
        cur=await db.execute("UPDATE ads SET status='publishing',updated_at=? WHERE id=? AND status='pending'",(now(),i))
        await db.commit(); return cur.rowcount==1

async def set_status(i,status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE ads SET status=?,updated_at=? WHERE id=?",(status,now(),i)); await db.commit()

async def set_published(i,message_id):
    published=now()
    expires=None
    if AD_EXPIRY_DAYS>0:
        expires=(datetime.now(timezone.utc)+timedelta(days=AD_EXPIRY_DAYS)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE ads SET status='published',published_message_id=?,published_at=?,expires_at=?,updated_at=? WHERE id=?",(message_id,published,expires,published,i)); await db.commit()

async def update_ad_media(i,media):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE ads SET media_json=?,updated_at=? WHERE id=?",(json.dumps(media,ensure_ascii=False),now(),i)); await db.commit()

async def update_ad_price(i,price):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE ads SET price=?,price_rub=?,updated_at=? WHERE id=?",(price,price,now(),i)); await db.commit()

async def update_ad_prices(i, rub=None, stars=None, payment=None):
    async with aiosqlite.connect(DB_PATH) as db:
        if rub is not None:
            await db.execute("UPDATE ads SET price=?,price_rub=?,updated_at=? WHERE id=?",(rub,rub,now(),i))
        if stars is not None:
            await db.execute("UPDATE ads SET price_stars=?,updated_at=? WHERE id=?",(stars,now(),i))
        if payment:
            await db.execute("UPDATE ads SET payment=?,updated_at=? WHERE id=?",(payment,now(),i))
        await db.commit()

async def update_product_number(i,n):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("UPDATE ads SET product_number=?,updated_at=? WHERE id=?",(n,now(),i)); await db.commit(); return True
        except aiosqlite.IntegrityError:
            await db.rollback(); return False

async def get_published_ads(kind=None,search=None,limit=10,offset=0):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory=aiosqlite.Row
        where=["status='published'"]; args=[]
        if kind and kind!='all': where.append("kind=?"); args.append(kind)
        if search:
            p=f"%{search}%"; where.append("(game LIKE ? OR description LIKE ? OR username LIKE ? OR CAST(product_number AS TEXT) LIKE ?)"); args += [p,p,p,p]
        args += [limit,offset]
        cur=await db.execute(f"SELECT * FROM ads WHERE {' AND '.join(where)} ORDER BY product_number DESC LIMIT ? OFFSET ?",args)
        return await cur.fetchall()

async def count_published_ads(kind=None,search=None):
    async with aiosqlite.connect(DB_PATH) as db:
        where=["status='published'"]; args=[]
        if kind and kind!='all': where.append("kind=?"); args.append(kind)
        if search:
            p=f"%{search}%"; where.append("(game LIKE ? OR description LIKE ? OR username LIKE ? OR CAST(product_number AS TEXT) LIKE ?)"); args += [p,p,p,p]
        cur=await db.execute(f"SELECT COUNT(*) FROM ads WHERE {' AND '.join(where)}",args)
        return (await cur.fetchone())[0]

async def get_user_ads_count(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cur=await db.execute("SELECT COUNT(*) FROM ads WHERE user_id=?",(user_id,)); return (await cur.fetchone())[0]

async def get_user_ads(user_id,limit=30):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory=aiosqlite.Row
        cur=await db.execute("SELECT product_number,id,kind,game,price,price_rub,price_stars,payment,status FROM ads WHERE user_id=? ORDER BY id DESC LIMIT ?",(user_id,limit)); return await cur.fetchall()

async def get_recent_ads(limit=30):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory=aiosqlite.Row
        cur=await db.execute("SELECT product_number,id,kind,game,price,price_rub,price_stars,payment,status FROM ads ORDER BY id DESC LIMIT ?",(limit,)); return await cur.fetchall()

async def expire_old_ads():
    if AD_EXPIRY_DAYS<=0: return []
    cutoff=(datetime.now(timezone.utc)-timedelta(days=AD_EXPIRY_DAYS)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cur=await db.execute("SELECT id FROM ads WHERE status='published' AND published_at IS NOT NULL AND published_at<?",(cutoff,))
        ids=[r[0] for r in await cur.fetchall()]
        if ids:
            await db.execute("UPDATE ads SET status='removed',updated_at=? WHERE status='published' AND published_at<?",(now(),cutoff))
            await db.commit()
        return ids

async def get_published_user_ads(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory=aiosqlite.Row
        cur=await db.execute("SELECT * FROM ads WHERE user_id=? AND status='published'",(user_id,))
        return await cur.fetchall()
