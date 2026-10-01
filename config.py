import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DB_PATH = os.getenv("DATABASE_PATH", "market.db").strip()
PUBLIC_CHANNEL = os.getenv("PUBLIC_CHANNEL", "").strip()
PUBLIC_CHANNEL_URL = os.getenv("PUBLIC_CHANNEL_URL", "").strip()
RECEIPT_CHAT_ID_RAW = os.getenv("RECEIPT_CHAT_ID", "").strip()
LOG_CHAT_ID_RAW = os.getenv("LOG_CHAT_ID", "").strip()
PAYMENT_DETAILS = os.getenv("PAYMENT_DETAILS", "Не настроено").strip()
SUPPORT_CONTACT = os.getenv("SUPPORT_CONTACT", "@QuietFrench").strip()
AD_EXPIRY_DAYS = int(os.getenv("AD_EXPIRY_DAYS", "0") or 0)
SELL_COOLDOWN_SECONDS = int(os.getenv("SELL_COOLDOWN_SECONDS", "30") or 30)
IMPORT_CHANNELS = os.getenv("IMPORT_CHANNELS", PUBLIC_CHANNEL).strip()

try:
    ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}
except ValueError:
    ADMIN_IDS = set()

try:
    RECEIPT_CHAT_ID = int(RECEIPT_CHAT_ID_RAW) if RECEIPT_CHAT_ID_RAW else None
except ValueError:
    RECEIPT_CHAT_ID = None

try:
    LOG_CHAT_ID = int(LOG_CHAT_ID_RAW) if LOG_CHAT_ID_RAW else None
except ValueError:
    LOG_CHAT_ID = None

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не указан в .env")
