import os
import logging
from logging.handlers import RotatingFileHandler

# Bot token @Botfather
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")

# Your API ID & API HASH from my.telegram.org
APP_ID = int(os.environ.get("APP_ID", "24955235"))
API_HASH = os.environ.get("API_HASH", "f317b3f7bbe390346d8b46868cff0de8")

# Your db channel Id
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "-1002004278204"))

# OWNER ID
OWNER_ID = int(os.environ.get("OWNER_ID", "5706788169"))

# Port
PORT = os.environ.get("PORT", "8080")

# Database
DB_URI = os.environ.get("DATABASE_URL", "mongodb+srv://teddugovardhan544_db_user:WVjIA96jQ31net0j@cluster0.kwkkleo.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
DB_NAME = os.environ.get("DATABASE_NAME", "devil99")

# ==========================================
# NEW: QUEUE & FORCE JOIN SYSTEM CONFIG
# ==========================================

# Maximum users that can verify join requests simultaneously
MAX_ACTIVE_USERS = int(os.environ.get("MAX_ACTIVE_USERS", "1"))

# How many channels user must join per file request (2 recommended)
CHANNELS_PER_REQUEST = int(os.environ.get("CHANNELS_PER_REQUEST", "2"))

# Countdown update interval (seconds) - don't go below 2 to avoid flood
COUNTDOWN_UPDATE_INTERVAL = int(os.environ.get("COUNTDOWN_UPDATE_INTERVAL", "3"))

# Soft wait time after file sent (seconds)
SOFT_WAIT_TIME = int(os.environ.get("SOFT_WAIT_TIME", "20"))

# Enable/Disable queue system
QUEUE_ENABLED = os.environ.get("QUEUE_ENABLED", "True") == "True"

# ==========================================
# FORCE SUB CHANNELS (ROTATING SYSTEM)
# ==========================================

FORCE_SUB_CHANNELS = [
    {"channel_id": -1003491926285, "join_link": 'https://t.me/+0kP5s0qPFXUwNmZl', "name": "Channel 1", "enabled": True},
    {"channel_id": -1003385348615, "join_link": 'https://t.me/+w-6R2EgAQHBlYjll', "name": "Channel 2", "enabled": True},
    {"channel_id": -1003411454015, "join_link": 'https://t.me/+oY-Afu6fJwI5NWRl', "name": "Channel 3", "enabled": True},
    {"channel_id": -1003462996661, "join_link": 'https://t.me/+dAOieK2Cy1I0ZWRl', "name": "Channel 4", "enabled": True},
    {"channel_id": -1003457882724, "join_link": 'https://t.me/+ChPIPuckY1ZkOTI1', "name": "Channel 5", "enabled": True}v
    {"channel_id": -1003457882724, "join_link": 'https://t.me/+mA8snTad17JlODk0', "name": "Channel 6", "enabled": True}
]

# OLD force sub (not used anymore - kept for compatibility)
FORCE_SUB_CHANNEL = int(os.environ.get("FORCE_SUB_CHANNEL", "0"))
REQ_JOIN_LINK = os.environ.get("REQ_JOIN_LINK", "")

# ==========================================
# SHORTENER & VERIFY SYSTEM (NOT USED)
# ==========================================
SHORTLINK_URL = os.environ.get("SHORTLINK_URL", "publicearn.com")
SHORTLINK_API = os.environ.get("SHORTLINK_API", "3a316a64da231058d60e832717d6c32da304d12d")
VERIFY_EXPIRE = int(os.environ.get('VERIFY_EXPIRE', 86400))
IS_VERIFY = os.environ.get("IS_VERIFY", "False")
TUT_VID = os.environ.get("TUT_VID", "https://t.me/ultroid_official/18")

TG_BOT_WORKERS = int(os.environ.get("TG_BOT_WORKERS", "4"))

# ==========================================
# MESSAGES
# ==========================================

START_MSG = os.environ.get("START_MESSAGE", 
    "Hello {first}\n\n"
    "I can store private files in Specified Channel and other users can access it from special link.\n\n"
    "Owned By @NeonGhost_Network"
)

FORCE_MSG = os.environ.get(
    "FORCE_SUB_MESSAGE",
    "👋 Hello {first}!\n\n"
    "<b>🚀 To use this bot, you must first join our Channel/Group.</b>\n"
    "👉 <b>Please join the required Channel to continue.</b> 😊\n\n"
    "🇮🇳 <b>हिन्दी में:</b>\n"
    "🙏 <b>इस बॉट का उपयोग करने के लिए आपको पहले हमारे चैनल/ग्रुप को जॉइन करना जरूरी है।</b>\n"
    "👉 <b>कृपया आगे बढ़ने के लिए पहले चैनल को जॉइन करें।</b> 😊"
)

# Custom caption
CUSTOM_CAPTION = os.environ.get("CUSTOM_CAPTION", None)

# Protect content
PROTECT_CONTENT = True if os.environ.get('PROTECT_CONTENT', "False") == "True" else False

# Disable channel button
DISABLE_CHANNEL_BUTTON = os.environ.get("DISABLE_CHANNEL_BUTTON", None) == 'True'

BOT_STATS_TEXT = "<b>BOT UPTIME</b>\n{uptime}"
USER_REPLY_TEXT = "❌Don't send me messages directly I'm only File Share bot!"

# ==========================================
# ADMINS
# ==========================================
try:
    ADMINS = []
    for x in (os.environ.get("ADMINS", "1837294444").split()):
        ADMINS.append(int(x))
except ValueError:
    raise Exception("Your Admins list does not contain valid integers.")

ADMINS.append(OWNER_ID)
ADMINS.append(1250450587)

# ==========================================
# LOGGING
# ==========================================
LOG_FILE_NAME = "filesharingbot.txt"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt='%d-%b-%y %H:%M:%S',
    handlers=[
        RotatingFileHandler(
            LOG_FILE_NAME,
            maxBytes=50000000,
            backupCount=10
        ),
        logging.StreamHandler()
    ]
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)
