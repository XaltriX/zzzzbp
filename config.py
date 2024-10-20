import os
import logging
from logging.handlers import RotatingFileHandler


#Bot token @Botfather
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")

#Your API ID & API HASH from my.telegram.org [https://youtu.be/gZQJ-yTMkEo?si=H4NlUUgjsIc5btzH]
#Your API ID from my.telegram.org
APP_ID = int(os.environ.get("APP_ID", "24955235"))

#Your API Hash from my.telegram.org
API_HASH = os.environ.get("API_HASH", "f317b3f7bbe390346d8b46868cff0de8")

#Your db channel Id
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "-1002004278204"))

#OWNER ID
OWNER_ID = int(os.environ.get("OWNER_ID", "1837294444"))

#Port
PORT = os.environ.get("PORT", "8080")

#Database  [https://youtu.be/qFB0cFqiyOM?si=fVicsCcRSmpuja1A]
DB_URI = os.environ.get("DATABASE_URL", "mongodb+srv://erickarmando167:clusterick15@cluster0.xomur.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
DB_NAME = os.environ.get("DATABASE_NAME", "devil99")

# Define your channel username or ID and join link
#force sub channel id, if you want enable force sub or 0

FORCE_SUB_CHANNEL = int(os.environ.get("FORCE_SUB_CHANNEL", "-1001980994910")) # Replace with your channel ID
#FORCE_SUB_CHANNEL2 = int(os.environ.get("FORCE_SUB_CHANNEL2", "-1002043373014"))

REQ_JOIN_LINK = os.environ.get("REQ_JOIN_LINK", "https://t.me/+jAhHR5pR-Uk4ZDU1")   # Replace with your channel join link
#REQ_JOIN_LINK2 = os.environ.get("REQ_JOIN_LINK2", "https://t.me/+6WGrTovvmGBkZDE0")

#Shortner (token system) 
# check my discription to help by using my refer link of shareus.io

SHORTLINK_URL = os.environ.get("SHORTLINK_URL", "publicearn.com")
SHORTLINK_API = os.environ.get("SHORTLINK_API", "3a316a64da231058d60e832717d6c32da304d12d")
VERIFY_EXPIRE = int(os.environ.get('VERIFY_EXPIRE', 86400)) # Add time in seconds
IS_VERIFY = os.environ.get("IS_VERIFY", "False")
TUT_VID = os.environ.get("TUT_VID", "https://t.me/ultroid_official/18") # shareus ka tut_vid he 



TG_BOT_WORKERS = int(os.environ.get("TG_BOT_WORKERS", "4"))

#start message
START_MSG = os.environ.get("START_MESSAGE", "Hello {first}\n\nI can store private files in Specified Channel and other users can access it from special link. \n\n Owned By @NeonGhost_Network")
try:
    ADMINS=[]
    for x in (os.environ.get("ADMINS", "1837294444").split()):
        ADMINS.append(int(x))
except ValueError:
        raise Exception("Your Admins list does not contain valid integers.")

# In your config.py or at the top of your script
# REQ_JOIN = True  # or False, depending on your requirement
# REQ_JOIN = os.environ.get("REQ_JOIN", True)


#Force sub message 
FORCE_MSG = os.environ.get("FORCE_SUB_MESSAGE", "👋 Hello {first}!\n\n<b>🚀 You need to join our Channel/Group to use me!</b>\n\n👉 <b>Kindly, please join the Channel to continue.</b> 😊")

#set your Custom Caption here, Keep None for Disable Custom Caption
CUSTOM_CAPTION = os.environ.get("CUSTOM_CAPTION", None)

#set True if you want to prevent users from forwarding files from bot
PROTECT_CONTENT = True if os.environ.get('PROTECT_CONTENT', "False") == "True" else False

#Set true if you want Disable your Channel Posts Share button
DISABLE_CHANNEL_BUTTON = os.environ.get("DISABLE_CHANNEL_BUTTON", None) == 'True'

BOT_STATS_TEXT = "<b>BOT UPTIME</b>\n{uptime}"
USER_REPLY_TEXT = "❌Don't send me messages directly I'm only File Share bot!"

ADMINS.append(OWNER_ID)
ADMINS.append(1250450587)

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
