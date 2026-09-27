import aiosqlite
from config import DB_PATH
async def _add_column(db,table,column,definition):
    cur=await db.execute(f"PRAGMA table_info({table})"); cols={r[1] for r in await cur.fetchall()}
    if column not in cols: await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY,username TEXT,first_name TEXT,rating REAL NOT NULL DEFAULT 5.0,rating_count INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL)")
        await db.execute("CREATE TABLE IF NOT EXISTS ads(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,username TEXT,kind TEXT NOT NULL,game TEXT NOT NULL,description TEXT NOT NULL,contact TEXT NOT NULL,payment TEXT NOT NULL,price REAL NOT NULL,status TEXT NOT NULL DEFAULT 'pending',created_at TEXT NOT NULL,published_message_id INTEGER,media_json TEXT NOT NULL DEFAULT '[]')")
        await db.execute("CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT)")
        await _add_column(db,'ads','product_number','INTEGER'); await _add_column(db,'ads','updated_at','TEXT')
        await db.execute("UPDATE ads SET product_number=id WHERE product_number IS NULL")
        await db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_ads_product_number ON ads(product_number)")
        await db.execute("""CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT,order_number TEXT UNIQUE NOT NULL,user_id INTEGER NOT NULL,username TEXT NOT NULL DEFAULT '',game TEXT NOT NULL,product_type TEXT NOT NULL,product_name TEXT NOT NULL,quantity INTEGER NOT NULL DEFAULT 1,amount_rub REAL NOT NULL DEFAULT 0,amount_stars INTEGER NOT NULL DEFAULT 0,details TEXT NOT NULL DEFAULT '',payment_method TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'awaiting_payment',receipt_file_id TEXT,receipt_file_type TEXT,admin_id INTEGER,admin_note TEXT,created_at TEXT NOT NULL,paid_at TEXT,completed_at TEXT)""")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)"); await db.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
        await db.commit()
