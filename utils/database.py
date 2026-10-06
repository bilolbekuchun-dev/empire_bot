from datetime import datetime, timedelta
from tortoise import Tortoise
import json
import logging
import os
from dotenv import load_dotenv
from models.user import User, Profile
from models.game_data import Game, GamePlayer, Chat, GamePhase, Action, Vote, VoteLike, GazabdorPick
from redis.asyncio import Redis
from config import DATABASE_URL
from models.game_data import Geroys

load_dotenv()

from logging.handlers import RotatingFileHandler

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('cleanup.log', maxBytes=10*1024*1024, backupCount=3, encoding='utf-8'),
        logging.StreamHandler()
    ]       
)
logger = logging.getLogger(__name__)

try:
    import fakeredis.aioredis
    _fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
except Exception:
    _fake_redis = None

class LazyRedis:
    def __init__(self):
        self._real = Redis(host='localhost', port=6379, db=0, decode_responses=True)
        self._active = None

    async def _get_client(self):
        if self._active is None:
            try:
                await self._real.ping()
                self._active = self._real
            except Exception:
                if _fake_redis:
                    self._active = _fake_redis
                else:
                    self._active = self._real
        return self._active

    def __getattr__(self, name):
        async def method(*args, **kwargs):
            client = await self._get_client()
            fn = getattr(client, name)
            return await fn(*args, **kwargs)
        return method

redis_client = LazyRedis()



async def init():
    if "postgres" in DATABASE_URL:
        sep = "&" if "?" in DATABASE_URL else "?"
        pooled_db_url = f"{DATABASE_URL}{sep}minsize=5&maxsize=30"
    else:
        pooled_db_url = DATABASE_URL

    await Tortoise.init(
        db_url=pooled_db_url,
        modules={
            "models": ["models.game_data", "models.user", "models.game_set", "models.airdrop"]
        },
    )
    
    # Migrations
    try:
        conn = Tortoise.get_connection("default")

        async def safe_add_column(table: str, column: str, definition: str):
            table_quoted = f'"{table}"' if table in ("user", "group") else table
            is_sqlite = "sqlite" in DATABASE_URL.lower()
            if is_sqlite:
                sql = f"ALTER TABLE {table_quoted} ADD COLUMN {column} {definition};"
            else:
                sql = f"ALTER TABLE {table_quoted} ADD COLUMN IF NOT EXISTS {column} {definition};"
            try:
                await conn.execute_query(sql)
            except Exception as e:
                err = str(e).lower()
                if "duplicate column" in err or "already exists" in err or "near" in err:
                    pass

        # Transfers table
        await safe_add_column("transfers", "caption", "VARCHAR(100) DEFAULT ''")
        # GroupBalance table — real_money ($)
        await safe_add_column("groupbalance", "real_money", "INT DEFAULT 0")
        # GameSetTime table
        await safe_add_column("game_sets_time", "reg_time", "BIGINT DEFAULT 120")
        # CommandPermissionsChat table
        await safe_add_column("commandpermissionschat", "extend_cmd", "VARCHAR(10) DEFAULT 'admin'")
        await safe_add_column("command_permissions_chat", "extend_cmd", "VARCHAR(10) DEFAULT 'admin'")
        # VipUser table
        await safe_add_column("vipuser", "duration_days", "INT DEFAULT 30")
        # User table
        await safe_add_column("user", "username", "VARCHAR(64)")

        # Bosh Komissar tizimi
        await safe_add_column("gameplayer", "kom_success_checks", "INT DEFAULT 0")
        await safe_add_column("gameplayer", "kom_is_upgraded", "BOOLEAN DEFAULT FALSE")
        await safe_add_column("gameplayer", "kom_wire_uses", "INT DEFAULT 2")
        await safe_add_column("gameplayer", "kom_wire_target_pid", "BIGINT")
        await safe_add_column("gameplayer", "kom_profile_used", "BOOLEAN DEFAULT FALSE")
        await safe_add_column("gameplayer", "kom_qosh_used", "BOOLEAN DEFAULT FALSE")
        await safe_add_column("gameplayer", "kom_arrest_pid", "BIGINT")
        await safe_add_column("gameplayer", "kom_arrest_used", "BOOLEAN DEFAULT FALSE")
        await safe_add_column("gameplayer", "kom_himoya_target_pid", "BIGINT")
        await safe_add_column("gameplayer", "kom_himoya_nights", "INT DEFAULT 0")
        await safe_add_column("gameplayer", "kom_signal_used", "BOOLEAN DEFAULT FALSE")
        await safe_add_column("gameplayer", "kom_himoya_protected", "BOOLEAN DEFAULT FALSE")

        # Qora Materiya
        await safe_add_column("game", "qm_portlat_active", "BOOLEAN DEFAULT FALSE")
        await safe_add_column("gameplayer", "qm_active", "BOOLEAN DEFAULT FALSE")
        await safe_add_column("gameplayer", "qm_void_swap_role", "VARCHAR(70)")
        await safe_add_column("gameplayer", "qm_void_swap_days", "INT DEFAULT 0")
        await safe_add_column("gameplayer", "qm_original_role", "VARCHAR(70)")
        await safe_add_column("gameplayer", "qm_portlat_used", "BOOLEAN DEFAULT FALSE")
        await safe_add_column("gameplayer", "qm_tiriltir_used", "BOOLEAN DEFAULT FALSE")
        await safe_add_column("gameplayer", "qm_xazina_used", "BOOLEAN DEFAULT FALSE")

        # Geroy Market
        await safe_add_column("geroymarket", "status", "VARCHAR(10) DEFAULT 'active'")
        await safe_add_column("geroymarket", "channel_message_id", "BIGINT")
        await safe_add_column("geroymarket", "updated_at", "TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP")

        try: await conn.execute_query("CREATE UNIQUE INDEX IF NOT EXISTS geroys_user_id_unique ON geroys(user_id);")
        except Exception: pass

        # Tournament
        await safe_add_column("tournament", "birthday_date", "VARCHAR(5)")
        await safe_add_column("tournament", "gift_diamond", "INT DEFAULT 0")
        await safe_add_column("tournament", "gift_dollar", "INT DEFAULT 0")
        await safe_add_column("tournament", "gift_last_year", "INT")

        try: await conn.execute_query('CREATE UNIQUE INDEX IF NOT EXISTS user_user_id_unique ON "user"(user_id);')
        except Exception: pass

        # WebApp migrations
        webapp_migrations = [
            ('user', 'created_at', "TIMESTAMPTZ DEFAULT NOW()"),
            ('user', 'lang', "VARCHAR(5) DEFAULT 'uz'"),
            ('chat', 'lang', "VARCHAR(5) DEFAULT 'uz'"),
            ('tournament', 'lang', "VARCHAR(5) DEFAULT ''"),
            ('profile', 'daily_streak', "INT DEFAULT 0"),
            ('profile', 'last_claim_date', "DATE"),
            ('geroys', 'photo_url', "VARCHAR(500) DEFAULT ''"),
            ('tournament', 'contact_button_text', "VARCHAR(50) DEFAULT ''"),
            ('diamondbuystars', 'kind', "VARCHAR(10) DEFAULT 'diamond'"),
            ('diamondbuystars', 'source', "VARCHAR(10) DEFAULT 'bot'"),
            ('user', 'last_seen', "TIMESTAMPTZ"),
            ('user', 'support_cleared_at', "TIMESTAMPTZ"),
            ('supportmessage', 'image_url', "VARCHAR(300)"),
            ('supportmessage', 'is_read', "BOOLEAN DEFAULT FALSE"),
            ('tournament', 'created_by_user_id', "BIGINT"),
            ('tournament', 'contact_clicks', "INT DEFAULT 0"),
            ('tournament', 'target_user_id', "BIGINT"),
            ('tournament', 'kind', "VARCHAR(20) DEFAULT 'ad'"),
            ('user', 'tournament_manager_lang', "VARCHAR(5)"),
            ('profile', 'birth_date', "VARCHAR(5)"),
            ('profile', 'last_birthday_greeted_year', "INT"),
            ('nftpurchaselog', 'stars_price', "INT"),
            ('nftmarketsettings', 'spent_baseline', "INT DEFAULT 0"),
        ]
        for tbl, col, dfn in webapp_migrations:
            await safe_add_column(tbl, col, dfn)

        print("✅ Database migrations completed.")
    except Exception as e:
        print(f"ℹ️ Migration error: {e}")

    # Turnir - banner_text uzunroq matnlarga (masalan reklama e'lonlari) moslashishi uchun
    # VARCHAR(300) dan TEXT (cheksiz)ga o'tkazamiz.
    try:
        conn = Tortoise.get_connection("default")
        try:
            await conn.execute_query("ALTER TABLE tournament ALTER COLUMN banner_text TYPE TEXT;")
        except Exception:
            pass
    except Exception as e:
        print(f"ℹ️ Migration (tournament.banner_text -> TEXT): {e}")

    await Tortoise.generate_schemas()
    # Dublikat geroylarni tozalash (bitta egaga bir necha Geroys bo'lsa)
    geroys = await Geroys.all().prefetch_related('user')
    user_geroys = {}
    
    for geroy in geroys:
        user_id = geroy.user.user_id if geroy.user else None
        if user_id:
            if user_id not in user_geroys:
                user_geroys[user_id] = []
            user_geroys[user_id].append(geroy)
    
    # Har bir foydalanuvchi uchun eng ko'p ballga ega geroy qoldiriladi
    for user_id, geroy_list in user_geroys.items():
        if len(geroy_list) > 1:
            # Ball bo'yicha tartiblash (eng ko'p ball birinchi)
            geroy_list.sort(key=lambda x: x.ball, reverse=True)
            # Birinchisidan tashqari hammasini o'chirish
            for geroy in geroy_list[1:]:
                await geroy.delete()
            print(f"✅ User {user_id} uchun {len(geroy_list)-1} ta dublikat geroy o'chirildi.")

    print("🎉 Database initialization muvaffaqiyatli tugadi!")


# Faol bo'lmagan foydalanuvchilarni tozalash uchun alohida chaqirish


    # await Tortoise.get_connection("default").execute_script("""
    #     DROP TABLE groupmoreset;
    # """)
    # conn = Tortoise.get_connection("default")
    # await conn.execute_script("""
    #     ALTER TABLE action ADD COLUMN with_miltiq BOOLEAN NOT NULL DEFAULT 0;
    # """)

    # profiles = await Profile.all()

    # for profile in profiles:
    #     profile.dollar = 0
    #     profile.diamond = 0
    #     profile.himoya = 0
    #     profile.hujjat = 0
    #     profile.qotildan_himoya = 0
    #     profile.osishdan_himoya = 0
    #     profile.miltiq = 0
    #     profile.doridan_himoya = 0
    #     profile.maska = 0
    #     profile.wins = 0
    #     profile.games_count = 0
    #     await profile.save()

    # print(f"✅ {len(profiles)} ta profil hisoblari muvaffaqiyatli tozalandi.")
    # games = await Game.all()
    # for game in games:
    #     await game.delete()
    # print(f"✅ {len(games)} ta o'yin muvaffaqiyatli o'chirildi.")
    
async def clean_duplicates():
    # User modelidagi dublikatlar
    seen_user_ids = set()
    users = await User.all()
    for user in users:
        if user.user_id in seen_user_ids:
            await user.delete()
        else:
            seen_user_ids.add(user.user_id)

    # Chat modelidagi dublikatlar
    seen_chat_ids = set()
    chats = await Chat.all()
    for chat in chats:
        if chat.chat_id in seen_chat_ids:
            await chat.delete()
        else:
            seen_chat_ids.add(chat.chat_id)

    print("✅ Dublikatlar tozalandi.")

import json
from models.user import User
from tortoise import Tortoise

async def load_users():
    with open("users.json", "r", encoding="utf-8") as f:
        users = json.load(f)

    for user_data in users:
        await User.get_or_create(
            id=user_data["id"],
            user_id=user_data["user_id"],
            full_name=user_data.get("full_name", ""),
            is_bot=user_data.get("is_bot", False),
            mention=user_data.get("mention", "")
        )

    print(f"{len(users)} ta foydalanuvchi yuklandi.")

import asyncio
import json
from models.user import Profile, User
from tortoise import Tortoise

async def load_profiles():
    with open("profile.json", "r", encoding="utf-8") as f:
        profiles = json.load(f)

    for profile_data in profiles:
        user = await User.filter(user_id=profile_data["user_id"]).first()
        if not user: continue
        await Profile.get_or_create(
            user=user,
            dollar=profile_data.get("dollar", 0),
            diamond=profile_data.get("diamond", 0),
            himoya=profile_data.get("himoya", 0),
            hujjat=profile_data.get("hujjat", 0),
            qotildan_himoya=profile_data.get("qotildan_himoya", 0),
            osishdan_himoya=profile_data.get("osishdan_himoya", 0),
            miltiq=profile_data.get("miltiq", 0),
            doridan_himoya=profile_data.get("doridan_himoya", 0),
            maska=profile_data.get("maska", 0),
            wins=profile_data.get("wins", 0),
            games_count=profile_data.get("games_count", 0),
        )

    print(f"{len(profiles)} ta profil yuklandi.")

TORTOISE_ORM = {
    "connections": {"default": "sqlite://db.sqlite3"},  # Bazangiz qanday bo‘lsa shunga qarab yoziladi
    "apps": {
        "models": {
            "models": ["models.game_data", "models.user", "models.game_set", "models.airdrop", "aerich.models"],  # model fayllaringiz nomi
            "default_connection": "default",
        }
    }
}
