"""Redis rejim tugagan o'yinlari /stats hisobiga to'g'ri tushishini tekshiradi.

Root cause: Redis-mode o'yinlar faqat Redisda yashaydi va hech qachon
`Game` jadvaliga yozilmaydi — shuning uchun /stats dagi "Jami o'yinlar"
muzlab qolgan (84), "Faol o'yinlar" esa 0 ko'rsatgan edi.

Bu testlar:
1) tugagan Redis o'yini bitta yengil `Game` qatori yaratishini,
2) qayta cleanup dublikat qator yaratmasligini,
3) tugallanmagan (timeout/tozalash) o'yin sanalmasligini,
4) /stats "Faol o'yinlar" = DB(active) + Redis SCARD ekanini.
"""
from types import SimpleNamespace

from utils.database import redis_client
from utils.redis_game.game_models_schema import GameState
from utils.redis_game.repositories import game_repository
from utils.redis_game import win_conditions
from models.game_data import Chat, Game
from models.user import User
from utils.statistika import bozor_statistikasi


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
async def _mk_chat_and_creator(chat_id=5501, creator_id=777):
    chat = await Chat.create(chat_id=chat_id, title="t", type="supergroup")
    user = await User.create(user_id=creator_id, mention="test_creator")
    return chat, user


async def _mk_redis_game(chat_id, creator_id, phase="waiting"):
    """Create a Redis-mode game registered in every active-game index."""
    gid = await game_repository.generate_id()
    gs = GameState(
        game_id=gid,
        chat_id=chat_id,
        creator_id=creator_id,
        phase=phase,
        mode="classic",
        is_active=True,
        message_id=1,
    )
    await game_repository.save_game(gs, ttl_sec=86400)
    await game_repository.add_active_game(chat_id, gid)
    await redis_client.sadd("global:active_games", str(gid))
    return gid


# --------------------------------------------------------------------------
# 1) tugagan o'yin -> 1 ta yengil Game qatori
# --------------------------------------------------------------------------
async def test_finished_redis_game_creates_single_light_game_row():
    chat, creator = await _mk_chat_and_creator()
    gid = await _mk_redis_game(chat.chat_id, creator.user_id, phase="waiting")

    # o'yin "tugadi" deb belgilanib, cleanup chaqiriladi (haqiqiy yo'l:
    # announce -> phase="end" -> cleanup_game_redis)
    await game_repository.update_game_field(gid, "phase", "end")
    await win_conditions.cleanup_game_redis(gid)

    assert await Game.all().count() == 1
    row = await Game.first()
    assert row.is_active is False
    assert row.phase == "end"
    assert row.chat_id == chat.id  # Tortoise FK -> ichki Chat PK (5501 emas)

    # o'yin global active setdan ham olib tashlangan
    assert await redis_client.sismember("global:active_games", str(gid)) == 0

    # qayta cleanup (test reliability suite shunday qiladi) -> dublikat YO'Q
    await win_conditions.cleanup_game_redis(gid)
    assert await Game.all().count() == 1


# --------------------------------------------------------------------------
# 2) tugallanmagan / save_to_db=False -> qator yaratilmaydi
# --------------------------------------------------------------------------
async def test_unfinished_or_disabled_cleanup_writes_no_row():
    chat, creator = await _mk_chat_and_creator(chat_id=5502, creator_id=778)

    # timeout/tozalash: phase != "end" -> sanalmaydi
    g1 = await _mk_redis_game(chat.chat_id, creator.user_id, phase="night")
    await win_conditions.cleanup_game_redis(g1)
    assert await Game.all().count() == 0

    # aniq o'tkazib yuborish
    g2 = await _mk_redis_game(chat.chat_id, creator.user_id, phase="end")
    await win_conditions.cleanup_game_redis(g2, save_to_db=False)
    assert await Game.all().count() == 0


# --------------------------------------------------------------------------
# 3) /stats: Jami o'yinlar = Game.count(), Faol = DB(active) + Redis SCARD
# --------------------------------------------------------------------------
async def test_stats_counts_active_db_plus_redis():
    from config import ADMINS

    chat, creator = await _mk_chat_and_creator(chat_id=5503, creator_id=779)

    # legacy: DB da aktiv o'yin (Redis migrationdan oldingi qatorlar)
    await Game.create(chat=chat, creator=creator, is_active=True, message_id=11)
    # redis: 1 ta hozir aktiv o'yin (faqat Redisda yashaydi)
    await _mk_redis_game(chat.chat_id, creator.user_id)

    class _Msg:
        def __init__(self):
            self.from_user = SimpleNamespace(id=ADMINS[0])
            self.out = []

        async def answer(self, text, **kwargs):
            self.out.append(text)

    msg = _Msg()
    await bozor_statistikasi(msg)
    assert msg.out, "bozor_statistikasi javob yubormadi"
    text = msg.out[0]

    assert "Faol o'yinlar: 2 ta" in text   # DB(1) + Redis(1)
    assert "Jami o'yinlar: 1 ta" in text   # faqat DB qatorlari


# --------------------------------------------------------------------------
# 4) tugagan o'yin -> keyingi /stats da "Jami o'yinlar" o'sadi
# --------------------------------------------------------------------------
async def test_stats_total_grows_after_finished_redis_game():
    from config import ADMINS

    chat, creator = await _mk_chat_and_creator(chat_id=5504, creator_id=780)
    gid = await _mk_redis_game(chat.chat_id, creator.user_id)
    await game_repository.update_game_field(gid, "phase", "end")

    class _Msg:
        def __init__(self):
            self.from_user = SimpleNamespace(id=ADMINS[0])
            self.out = []

        async def answer(self, text, **kwargs):
            self.out.append(text)

    before = _Msg()
    await bozor_statistikasi(before)
    assert "Jami o'yinlar: 0 ta" in before.out[0]

    await win_conditions.cleanup_game_redis(gid)

    after = _Msg()
    await bozor_statistikasi(after)
    assert "Jami o'yinlar: 1 ta" in after.out[0]
    assert "Faol o'yinlar: 0 ta" in after.out[0]  # end -> active emas
