import aiosqlite
from config import DB_PATH


async def _add_column(db, table, column, definition):
    cur = await db.execute(f"PRAGMA table_info({table})")
    cols = {row[1] for row in await cur.fetchall()}

    if column not in cols:
        await db.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:

        # =========================
        # USERS
        # =========================

        await db.execute("""
            CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                rating REAL NOT NULL DEFAULT 3.5,
                rating_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)

        # Реферальные поля.
        # Для старой базы добавятся автоматически.
        await _add_column(
            db,
            "users",
            "referral_code",
            "TEXT"
        )

        await _add_column(
            db,
            "users",
            "referred_by",
            "INTEGER"
        )

        await db.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_referral_code
            ON users(referral_code)
        """)

        # =========================
        # REFERRALS
        # =========================

        await db.execute("""
            CREATE TABLE IF NOT EXISTS referrals(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                referred_id INTEGER NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_referrals_referrer
            ON referrals(referrer_id)
        """)

        # Перенос старых реферальных связей
        # из users.referred_by в новую таблицу referrals.
        #
        # Благодаря INSERT OR IGNORE существующие записи
        # повторно не создаются.
        await db.execute("""
            INSERT OR IGNORE INTO referrals(
                referrer_id,
                referred_id
            )
            SELECT
                referred_by,
                user_id
            FROM users
            WHERE referred_by IS NOT NULL
              AND referred_by != 0
        """)

        # =========================
        # ADS
        # =========================

        await db.execute("""
            CREATE TABLE IF NOT EXISTS ads(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                kind TEXT NOT NULL,
                game TEXT NOT NULL,
                description TEXT NOT NULL,
                contact TEXT NOT NULL,
                payment TEXT NOT NULL,
                price REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                published_message_id INTEGER,
                media_json TEXT NOT NULL DEFAULT '[]'
            )
        """)

        await _add_column(
            db,
            "ads",
            "product_number",
            "INTEGER"
        )

        await _add_column(
            db,
            "ads",
            "updated_at",
            "TEXT"
        )

        await _add_column(
            db,
            "ads",
            "price_rub",
            "REAL NOT NULL DEFAULT 0"
        )

        await _add_column(
            db,
            "ads",
            "price_stars",
            "INTEGER NOT NULL DEFAULT 0"
        )

        await _add_column(
            db,
            "ads",
            "published_at",
            "TEXT"
        )

        await _add_column(
            db,
            "ads",
            "expires_at",
            "TEXT"
        )

        await _add_column(
            db,
            "ads",
            "tokens",
            "INTEGER NOT NULL DEFAULT 0"
        )

        await db.execute("""
            UPDATE ads
            SET product_number = id
            WHERE product_number IS NULL
        """)

        await db.execute("""
            UPDATE ads
            SET price_rub = price
            WHERE price_rub = 0
              AND price > 0
        """)

        await db.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_ads_product_number
            ON ads(product_number)
        """)

        # =========================
        # SETTINGS
        # =========================

        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings(
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # =========================
        # ORDERS
        # =========================

        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL DEFAULT '',
                game TEXT NOT NULL,
                product_type TEXT NOT NULL,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                amount_rub REAL NOT NULL DEFAULT 0,
                amount_stars INTEGER NOT NULL DEFAULT 0,
                details TEXT NOT NULL DEFAULT '',
                payment_method TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'awaiting_payment',
                receipt_file_id TEXT,
                receipt_file_type TEXT,
                admin_id INTEGER,
                admin_note TEXT,
                created_at TEXT NOT NULL,
                paid_at TEXT,
                completed_at TEXT
            )
        """)

        # =========================
        # BLOCKED USERS
        # =========================

        await db.execute("""
            CREATE TABLE IF NOT EXISTS blocked_users(
                user_id INTEGER PRIMARY KEY,
                reason TEXT NOT NULL DEFAULT '',
                blocked_by INTEGER,
                created_at TEXT NOT NULL
            )
        """)

        # =========================
        # LOGS
        # =========================

        await db.execute("""
            CREATE TABLE IF NOT EXISTS logs(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                user_id INTEGER,
                event TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT ''
            )
        """)

        # =========================
        # FAVORITES
        # =========================

        await db.execute("""
            CREATE TABLE IF NOT EXISTS favorites(
                user_id INTEGER NOT NULL,
                ad_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY(user_id, ad_id)
            )
        """)

        # =========================
        # COMPLAINTS
        # =========================

        await db.execute("""
            CREATE TABLE IF NOT EXISTS complaints(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open'
            )
        """)

        # =========================
        # INDEXES
        # =========================

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_orders_user
            ON orders(user_id)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_orders_status
            ON orders(status)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_logs_created
            ON logs(created_at)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_complaints_status
            ON complaints(status)
        """)

        # =========================
        # CHANNEL IMPORTS
        # =========================

        await db.execute("""
            CREATE TABLE IF NOT EXISTS channel_imports(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                ad_id INTEGER NOT NULL,
                imported_at TEXT NOT NULL,
                UNIQUE(channel_id, message_id)
            )
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_channel_imports_ad
            ON channel_imports(ad_id)
        """)

        # =========================
        # SAVE
        # =========================

        await db.commit()