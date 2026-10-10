from dotenv import load_dotenv
import os
from utils.role_names import RoleNames

load_dotenv()

TOKEN = os.getenv("TOKEN")
POSTGRES_URL = os.getenv("POSTGRES_URL")

TELEGRAM_USERBOT_API_ID = int(os.getenv("TELEGRAM_USERBOT_API_ID", "0"))
TELEGRAM_USERBOT_API_HASH = os.getenv("TELEGRAM_USERBOT_API_HASH")
TELEGRAM_USERBOT_SESSION = os.path.join(os.path.dirname(__file__), "userbot_session", "nft_userbot")

# BOT_URL = "https://t.me/xonmafiabot"

# BOT_URL = "https://t.me/unvmafiabetabot"
# BOT_URL=https://t.me/UnvMafiaBot
# BOT_URL=https://t.me/UnvMafia2Bot
# BOT_URL=https://t.me/UnvMafia3Bot
# BOT_URL=https://t.me/UnvMafia4Bot
# BOT_URL=https://t.me/UnvMafiaSpeedBot

BOT_URL = os.getenv("BOT_URL", "https://t.me/test_empire_bot")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://empiremafiaweb.netlify.app")
IS_WEBAPP_ACTIVE = False  # WebApp vaqtincha o'chirilgan
PORT = os.getenv("PORT")

MAX_PLAYERS = 45
DATABASE_URL = os.getenv("DATABASE_URL")

# Faqat ushbu 2 ta ID egalariga to'liq admin huquqlari va admin panelga kirish ruxsati berilgan:
PRIMARY_ADMIN_IDS = {8765051736, 6913838682}

env_admins = os.getenv("ADMINS")
if env_admins:
    parsed_admins = [int(x.strip()) for x in env_admins.split(",") if x.strip() and x.strip().isdigit()]
    ADMINS = [uid for uid in parsed_admins if uid in PRIMARY_ADMIN_IDS]
    if not ADMINS:
        ADMINS = [8765051736, 6913838682]
else:
    ADMINS = [8765051736, 6913838682]

PRIMARY_ADMIN_ID = 6913838682

mini_admins = os.getenv("MINI_ADMINS_GROUP_IDS")
MINI_ADMINS_GROUP_IDS = int(mini_admins.strip()) if mini_admins and mini_admins.strip() else 0

# CHANNEL_ID=-1003211567265
# CHANNEL_USERNAME=@xonmafiabotnews
# DIAMOND_SHOP_USERNAME=@willager_developer
# SUPPORT_ADMIN=https://T.me/willager_developer
# INFO_GROUP=1003284474449

"""
CHANNEL_ID=-1002509619806
CHANNEL_USERNAME=@UniversalMafiaOfficial
DIAMOND_SHOP_USERNAME=@xusanov_kibr
SUPPORT_ADMIN=https://T.me/xusanov_kibr
INFO_GROUP=-1002719900933
"""
CHANNEL_ID = int(os.getenv("CHANNEL_ID", None)) if os.getenv("CHANNEL_ID") else None
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "")
DIAMOND_SHOP_USERNAME = os.getenv("DIAMOND_SHOP_USERNAME", "")
SUPPORT_ADMIN = os.getenv("SUPPORT_ADMIN", "")
INFO_GROUP = int(os.getenv("INFO_GROUP", None)) if os.getenv("INFO_GROUP") else None    

GEROY_MARKET_CHANNEL_ID = int(os.getenv("GEROY_MARKET_CHANNEL_ID", "-1003547333095"))
GEROY_MARKET_CHANNEL_URL = os.getenv("GEROY_MARKET_CHANNEL_URL", "https://t.me/geroy_savdo")

# Admin tomonidan yaratiladigan "do'kon" geroylari shu rezerv (haqiqiy bo'lmagan) foydalanuvchiga tegishli bo'ladi —
# real Telegram chatga ega emas, shuning uchun unga xabar yuborilmaydi (ADMINS ga yo'naltiriladi).
GEROY_SHOP_SYSTEM_USER_ID = int(os.getenv("GEROY_SHOP_SYSTEM_USER_ID", "777000000001"))

# Redis Game Migration Feature Flag
REDIS_GAME_ENABLED = True


# Rollarni o'yinga qo'shish / arxivlash sozlamasi (True = faol, False = arxivda / nofaol)
ROLE_TOGGLES = {
    # Hozirda nofaol (arxivlangan) rollar:
    "Xoyin": False,
    "Ayg'oqchi": False,
    "Reverser": False,
    "Hamshira": False,
    "Jurnalist": False,
    "Sotqin": False,
    "Joker": False,
    "Admiral": False,
    "Kimyogar": False,
    "Rais": False,
    "Minior": False,
    "Robin Gud": False,
    "Fotoparatchi": False,
    "Zombi": False,
    "Labarant": False,
    "Koldun": False,
    "Qorbobo": False,
    "Tulki": False,
    "Savdogar": False,
}

def is_role_enabled(role_name: str) -> bool:
    """Rolning faollik holatini tekshirish. Config faylida False qilinsa arxivda turadi va o'yinga chiqmaydi."""
    if not role_name:
        return False
    clean = str(role_name).strip()
    for prefix in ["🤵🏻", "🤵🏼", "🕵🏼", "👨🏼‍⚕️", "👮🏼", "👨🏼", "🧙‍♂️", "💃", "👨🏼‍💼", "🤦🏼", "🤞🏼", "🎖", "🐺", "🔪", "🥷", "🧨", "🤹🏻", "🧌", "🧙‍", "👩🏼‍💻", "🤓", "🛡", "👺", "⛓", "🎭", "🧞", "👷🏻‍♂️", "🦇", "⚔️", "👩🏻‍⚕️", "🤡", "🧑🏻‍✈️", "👨‍🔬", "💰", "☠️", "🏹", "📸", "🧟", "👩‍⚕️", "⚡️", "🎅🏻", "🦊", "🏪", "🔄"]:
        clean = clean.replace(prefix, "").strip()
    
    return ROLE_TOGGLES.get(clean, True)


tinch_rollar = [
    RoleNames.KOMISSAR, RoleNames.SERJANT, RoleNames.DAYDI,
    RoleNames.DOKTOR, RoleNames.KEZUVCHI, RoleNames.FUQARO,
    RoleNames.JANOB, RoleNames.OMADLI, RoleNames.QORIQCHI,
    RoleNames.ZANJIR, RoleNames.QASOSKOR
]

mafia_rollar = [
    RoleNames.DON, RoleNames.MAFIA, RoleNames.ADVOKAT,
    RoleNames.OVCHI
]

yakka_rollar = [
    RoleNames.AFERIST, RoleNames.BORI, RoleNames.GAZABDOR,
    RoleNames.QOTIL, RoleNames.SEHRGAR, RoleNames.SUIDSID,
    RoleNames.QAROQCHI, RoleNames.AKTYOR, RoleNames.JIN, RoleNames.KONCHI,
    RoleNames.TAQLIDCHI
]