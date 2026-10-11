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
        redis_url = os.getenv("REDIS_URL") or os.getenv("REDIS_PRIVATE_URL")
        host = os.getenv("REDIS_HOST", os.getenv("REDISHOST", "localhost"))
        port = int(os.getenv("REDIS_PORT", os.getenv("REDISPORT", 6379)))
        password = os.getenv("REDIS_PASSWORD") or os.getenv("REDISPASSWORD") or None

        self._real = None
        try:
            if redis_url:
                if password and "@" not in redis_url:
                    self._real = Redis.from_url(redis_url, password=password, decode_responses=True)
                else:
                    self._real = Redis.from_url(redis_url, decode_responses=True)
            else:
                self._real = Redis(host=host, port=port, password=password, db=0, decode_responses=True)
        except Exception as e:
            logger.warning(f"Redis initialization error: {e}")

        self._active = None

    def _get_fake_redis(self):
        global _fake_redis
        if _fake_redis is None:
            try:
                import fakeredis.aioredis
                _fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
            except Exception as e:
                logger.error(f"Failed to initialize FakeRedis fallback: {e}")
        return _fake_redis

    async def _get_client(self):
        if self._active is not None:
            return self._active

        if self._real is not None:
            try:
                await self._real.ping()
                self._active = self._real
                return self._active
            except Exception as e:
                logger.warning(f"Real Redis ping/auth failed ({e}). Falling back to FakeRedis.")

        fake = self._get_fake_redis()
        if fake is not None:
            self._active = fake
        else:
            self._active = self._real
        return self._active

    def __getattr__(self, name):
        async def method(*args, **kwargs):
            client = await self._get_client()
            if client is None:
                fake = self._get_fake_redis()
                if fake is not None:
                    client = fake
                    self._active = fake

            try:
                fn = getattr(client, name)
                return await fn(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Redis method '{name}' failed with {type(e).__name__}: {e}. Switching to FakeRedis.")
                fake = self._get_fake_redis()
                if fake and client != fake:
                    self._active = fake
                    fn = getattr(fake, name)
                    return await fn(*args, **kwargs)
                raise e
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
            "models": ["models.game_data", 'models.user', "models.game_set", "models.airdrop"]
        },
    )
    await Tortoise.generate_schemas(safe=True)
    
    # Migrations - only run if migration tracking table doesn't exist
    try:
        conn = Tortoise.get_connection("default")
        # Transfers table
        # Migratsiyalar (SQLite va Postgres mosligi uchun safe-try)
        queries = [
            "ALTER TABLE transfers ADD COLUMN caption VARCHAR(100) DEFAULT '';",
            "ALTER TABLE groupbalance ADD COLUMN real_money INT DEFAULT 0;",
            "ALTER TABLE game_sets_time ADD COLUMN reg_time BIGINT DEFAULT 120;",
            "ALTER TABLE commandpermissionschat ADD COLUMN extend_cmd VARCHAR(10) DEFAULT 'admin';",
            "ALTER TABLE command_permissions_chat ADD COLUMN extend_cmd VARCHAR(10) DEFAULT 'admin';",
            "ALTER TABLE vipuser ADD COLUMN duration_days INT DEFAULT 30;",
            'ALTER TABLE "user" ADD COLUMN username VARCHAR(64);',
            "ALTER TABLE gameplayer ADD COLUMN kom_success_checks INT DEFAULT 0;",
            "ALTER TABLE gameplayer ADD COLUMN kom_is_upgraded BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE gameplayer ADD COLUMN kom_wire_uses INT DEFAULT 2;",
            "ALTER TABLE gameplayer ADD COLUMN kom_wire_target_pid BIGINT;",
            "ALTER TABLE gameplayer ADD COLUMN kom_profile_used BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE gameplayer ADD COLUMN kom_qosh_used BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE gameplayer ADD COLUMN kom_arrest_pid BIGINT;",
            "ALTER TABLE gameplayer ADD COLUMN kom_arrest_used BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE gameplayer ADD COLUMN kom_himoya_target_pid BIGINT;",
            "ALTER TABLE gameplayer ADD COLUMN kom_himoya_nights INT DEFAULT 0;",
            "ALTER TABLE gameplayer ADD COLUMN kom_signal_used BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE gameplayer ADD COLUMN kom_himoya_protected BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE game ADD COLUMN qm_portlat_active BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE gameplayer ADD COLUMN qm_active BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE gameplayer ADD COLUMN qm_void_swap_role VARCHAR(70);",
            "ALTER TABLE gameplayer ADD COLUMN qm_void_swap_days INT DEFAULT 0;",
            "ALTER TABLE gameplayer ADD COLUMN qm_original_role VARCHAR(70);",
            "ALTER TABLE gameplayer ADD COLUMN qm_portlat_used BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE gameplayer ADD COLUMN qm_tiriltir_used BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE gameplayer ADD COLUMN qm_xazina_used BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE geroymarket ADD COLUMN status VARCHAR(10) DEFAULT 'active';",
            "ALTER TABLE geroymarket ADD COLUMN channel_message_id BIGINT;",
            "ALTER TABLE geroymarket ADD COLUMN updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP;",
            "CREATE UNIQUE INDEX IF NOT EXISTS geroys_user_id_unique ON geroys(user_id);",
            "ALTER TABLE tournament ADD COLUMN birthday_date VARCHAR(5);",
            "ALTER TABLE tournament ADD COLUMN gift_diamond INT DEFAULT 0;",
            "ALTER TABLE tournament ADD COLUMN gift_dollar INT DEFAULT 0;",
            "ALTER TABLE tournament ADD COLUMN gift_last_year INT;",
        ]
        for q in queries:
            try:
                await conn.execute_query(q)
            except Exception:
                pass


        # User.user_id (Telegram ID) bazada haqiqiy UNIQUE bo'lishi kerak — model unique=True deb
        # e'lon qilingan, lekin profil almashish funksiyasidagi nosoz holatlar buni buzishi mumkin edi.
        try: await conn.execute_query('CREATE UNIQUE INDEX IF NOT EXISTS user_user_id_unique ON "user"(user_id);')
        except Exception as e: print(f"ℹ️ Migration (user.user_id unique index): {e}")

        print("✅ Database migrations completed.")
    except Exception as e:
        print(f"ℹ️ Migration error: {e}")

    # WebApp uchun qo'shilgan yangi ustunlar (alohida try/except — biri ishlamasa qolganlari to'xtamasin)
    webapp_migrations = [
        ('user', 'created_at', "TIMESTAMPTZ DEFAULT NOW()"),
        ('user', 'lang', "VARCHAR(5) DEFAULT 'uz'"),
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
    for table, column, definition in webapp_migrations:
        try:
            conn = Tortoise.get_connection("default")
            table_quoted = f'"{table}"' if table == "user" else table
            await conn.execute_query(f'ALTER TABLE {table_quoted} ADD COLUMN IF NOT EXISTS {column} {definition};')
        except Exception as e:
            print(f"ℹ️ WebApp migration ({table}.{column}): {e}")

    # Turnir - banner_text uzunroq matnlarga (masalan reklama e'lonlari) moslashishi uchun
    # VARCHAR(300) dan TEXT (cheksiz)ga o'tkazamiz.
    try:
        conn = Tortoise.get_connection("default")
        await conn.execute_query("ALTER TABLE tournament ALTER COLUMN banner_text TYPE TEXT;")
    except Exception as e:
        print(f"ℹ️ Migration (tournament.banner_text -> TEXT): {e}")

    await Tortoise.generate_schemas()
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
            "models": ["models.game_data", "models.user", "models.game_set", "aerich.models"],  # model fayllaringiz nomi
            "default_connection": "default",
        }
    }
}
