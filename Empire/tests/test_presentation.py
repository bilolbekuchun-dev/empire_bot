"""
Day/Night presentation layer tests.

Verifies the presentation contract end-to-end against FakeRedis + in-memory
SQLite with virtual actors:

* one phase transition => exactly one intended presentation (idempotency)
* presentation delivery is fully decoupled from game-state correctness
* Telegram media/text failures never raise into, or corrupt, the game
* correct day/night numbers and localization (uz/ru/en/tr)
* multiple games transitioning simultaneously stay isolated
"""
import asyncio
from types import SimpleNamespace

import pytest

from utils.database import redis_client
from utils.redis_game.game_models_schema import GameState
from utils.redis_game.repositories import game_repository, player_repository
from utils.redis_game import presentation as pres
from utils.redis_game import game_phases
from models.game_data import Chat
from models.user import User
from tests.fakes import FakeBot


async def _new_game(chat_id=9001, creator_id=1, phase="waiting", mode="classic"):
    gid = await game_repository.generate_id()
    gs = GameState(game_id=gid, chat_id=chat_id, creator_id=creator_id, phase=phase,
                   mode=mode, is_active=True, message_id=1)
    await game_repository.save_game(gs, ttl_sec=86400)
    await game_repository.add_active_game(chat_id, gid)
    await redis_client.sadd("global:active_games", str(gid))
    return gid


# --------------------------------------------------------------------------
# 1. Game start presentation
# --------------------------------------------------------------------------
async def test_game_start_presentation_sent_once_with_phase():
    gid = await _new_game(chat_id=9001, phase="night")
    bot = FakeBot()

    r1 = await pres.send_game_start_presentation(bot, 9001, gid, phase="night", number=1)
    assert r1["status"] == pres.STATUS_SENT
    assert len(bot.sent_media) == 1
    caption = bot.sent_media[0]["caption"]
    assert "O'yin boshlandi" in caption          # game started
    assert "TUN 1" in caption                    # current phase

    # repeated trigger must NOT resend
    r2 = await pres.send_game_start_presentation(bot, 9001, gid, phase="night", number=1)
    assert r2["status"] == pres.STATUS_SKIPPED
    assert len(bot.sent_media) == 1


# --------------------------------------------------------------------------
# 9. Correct day / night number
# --------------------------------------------------------------------------
async def test_night_presentation_number_and_media():
    gid = await _new_game(chat_id=9002)
    bot = FakeBot()
    await pres.send_night_presentation(bot, 9002, gid, 3)
    assert len(bot.sent_media) == 1
    m = bot.sent_media[0]
    assert "TUN 3" in m["caption"]
    assert m["kind"] == "photo"
    assert str(m["value"]).endswith("night.jpg")


async def test_day_presentation_number_and_media():
    gid = await _new_game(chat_id=9003)
    bot = FakeBot()
    await pres.send_day_presentation(bot, 9003, gid, 2)
    assert len(bot.sent_media) == 1
    m = bot.sent_media[0]
    assert "KUN 2" in m["caption"]
    assert m["kind"] == "photo"
    assert str(m["value"]).endswith("day.jpg")


# --------------------------------------------------------------------------
# 2/3/4. Day<->Night transitions, consecutive
# --------------------------------------------------------------------------
async def test_consecutive_day_night_transitions():
    gid = await _new_game(chat_id=9004)
    bot = FakeBot()

    await pres.send_night_presentation(bot, 9004, gid, 1)
    await pres.send_day_presentation(bot, 9004, gid, 1)
    await pres.send_night_presentation(bot, 9004, gid, 2)
    await pres.send_day_presentation(bot, 9004, gid, 2)

    assert len(bot.sent_media) == 4
    captions = [m["caption"] for m in bot.sent_media]
    assert "TUN 1" in captions[0]
    assert "KUN 1" in captions[1]
    assert "TUN 2" in captions[2]
    assert "KUN 2" in captions[3]

    # re-running the same transitions changes nothing (idempotent)
    await pres.send_night_presentation(bot, 9004, gid, 1)
    await pres.send_day_presentation(bot, 9004, gid, 2)
    assert len(bot.sent_media) == 4


# --------------------------------------------------------------------------
# 5/6. Duplicate transition + duplicate callback
# --------------------------------------------------------------------------
async def test_duplicate_transition_event_single_presentation():
    gid = await _new_game(chat_id=9005)
    bot = FakeBot()
    for _ in range(10):
        await pres.send_night_presentation(bot, 9005, gid, 1)
    assert len(bot.sent_media) == 1


async def test_duplicate_callback_concurrent_single_presentation():
    gid = await _new_game(chat_id=9006)
    bot = FakeBot()
    # many handlers process the same transition at once
    results = await asyncio.gather(
        *[pres.send_night_presentation(bot, 9006, gid, 1) for _ in range(25)]
    )
    sent = [r for r in results if r["status"] == pres.STATUS_SENT]
    assert len(sent) == 1
    assert len(bot.sent_media) == 1


# --------------------------------------------------------------------------
# 7. Media send failure -> text fallback, game continues
# --------------------------------------------------------------------------
async def test_media_failure_falls_back_to_text():
    gid = await _new_game(chat_id=9007)
    bot = FakeBot(fail_media=True)

    result = await pres.send_night_presentation(bot, 9007, gid, 1)
    assert result["status"] == pres.STATUS_SENT      # delivered (text-only)
    assert result["media"] is False
    assert bot.sent_media == []                       # no media got through
    assert len(bot.sent) == 1                         # but the text did
    assert "TUN 1" in bot.sent[0][1]


# --------------------------------------------------------------------------
# 8. Text send failure -> failed status, never raises
# --------------------------------------------------------------------------
async def test_text_failure_returns_failed_without_raising():
    gid = await _new_game(chat_id=9008)
    bot = FakeBot(fail_send=True)   # also fails media

    result = await pres.send_night_presentation(bot, 9008, gid, 1)
    assert result["status"] == pres.STATUS_FAILED
    assert result["error"]
    assert bot.sent_media == [] and bot.sent == []


# --------------------------------------------------------------------------
# 10. Localization
# --------------------------------------------------------------------------
async def test_localization_all_languages():
    seen = {}
    for lang, needle in [("uz", "TUN"), ("ru", "НОЧЬ"), ("en", "NIGHT"), ("tr", "GECE")]:
        gid = await _new_game(chat_id=9100 + len(seen))     # distinct game per language
        bot = FakeBot()
        r = await pres.send_presentation(bot, 9100 + len(seen), pres.EVENT_NIGHT, 5, gid,
                                         lang=lang, phase="night")
        assert r["status"] == pres.STATUS_SENT
        assert needle in bot.sent_media[0]["caption"]
        assert "5" in bot.sent_media[0]["caption"]
        seen[lang] = bot.sent_media[0]["caption"]

    assert len(set(seen.values())) == 4
    # unknown language falls back to the default (uz)
    assert pres.build_text(pres.EVENT_DAY, 2, lang="de") == pres.build_text(pres.EVENT_DAY, 2, lang="uz")


async def test_resolve_game_lang_uses_creator_language():
    await User.create(user_id=4242, full_name="Ru Creator", mention="", lang="ru")
    gid = await _new_game(chat_id=9010, creator_id=4242)
    bot = FakeBot()
    await pres.send_day_presentation(bot, 9010, gid, 1)
    assert "ДЕНЬ 1" in bot.sent_media[0]["caption"]


# --------------------------------------------------------------------------
# 11. Multiple games transitioning simultaneously
# --------------------------------------------------------------------------
async def test_multiple_games_simultaneous_isolation():
    games = [await _new_game(chat_id=9500 + i) for i in range(12)]
    bots = [FakeBot() for _ in games]

    await asyncio.gather(*[
        pres.send_night_presentation(bots[i], 9500 + i, gid, 1)
        for i, gid in enumerate(games)
    ])

    assert all(len(b.sent_media) == 1 for b in bots)
    assert sum(len(b.sent_media) for b in bots) == len(games)


# --------------------------------------------------------------------------
# 12. Game state must be independent of Telegram media success
# --------------------------------------------------------------------------
async def test_state_transition_independent_of_media_failure():
    gid = await _new_game(chat_id=9011, phase="waiting")

    # safe order: transition -> persist -> (presentation may fail) -> state intact
    gs = await game_repository.load_game(gid)
    gs.phase = "night"
    await game_repository.save_game(gs, ttl_sec=86400)

    bot = FakeBot(fail_send=True)  # total Telegram outage
    await pres.send_night_presentation(bot, 9011, gid, 1)   # must not raise

    reloaded = await game_repository.load_game(gid)
    assert reloaded is not None
    assert reloaded.phase == "night"
    assert reloaded.is_active is True


# --------------------------------------------------------------------------
# Media configuration mechanism
# --------------------------------------------------------------------------
async def test_media_config_env_override(monkeypatch):
    monkeypatch.setenv("MAFIA_DAY_MEDIA", "FILEID_DAY_123")
    monkeypatch.setenv("MAFIA_DAY_MEDIA_TYPE", "animation")
    m = pres.resolve_media(pres.EVENT_DAY)
    assert m.kind == "animation" and m.value == "FILEID_DAY_123"


async def test_media_config_bundled_defaults():
    assert str(pres.resolve_media(pres.EVENT_DAY).value).endswith("day.jpg")
    assert str(pres.resolve_media(pres.EVENT_NIGHT).value).endswith("night.jpg")
    # start falls back to the current phase's media
    assert str(pres.resolve_media(pres.EVENT_START, phase="night").value).endswith("night.jpg")


# --------------------------------------------------------------------------
# Integration: the real phase functions emit the presentation
# --------------------------------------------------------------------------
async def test_execute_night_phase_emits_presentation_once():
    cid = 9012
    gid = await _new_game(chat_id=cid, phase="night")
    chat = await Chat.create(chat_id=cid, title="g", type="supergroup")
    bot = FakeBot()
    times = SimpleNamespace(night_time=0, day_time=0, vote_time=0)

    await game_phases.execute_night_phase_redis(gid, 1, [], bot, chat, None, times)
    night_msgs = [m for m in bot.sent_media if "TUN 1" in (m["caption"] or "")]
    assert len(night_msgs) == 1

    # a repeated call for the same night cannot duplicate the presentation
    await game_phases.execute_night_phase_redis(gid, 1, [], bot, chat, None, times)
    night_msgs = [m for m in bot.sent_media if "TUN 1" in (m["caption"] or "")]
    assert len(night_msgs) == 1


async def test_execute_day_phase_emits_presentation_once():
    cid = 9013
    gid = await _new_game(chat_id=cid, phase="day")
    chat = await Chat.create(chat_id=cid, title="g", type="supergroup")
    bot = FakeBot()
    times = SimpleNamespace(night_time=0, day_time=0, vote_time=0)

    await game_phases.execute_day_phase_redis(gid, 1, [], bot, chat, None, times)
    day_msgs = [m for m in bot.sent_media if "KUN 1" in (m["caption"] or "")]
    assert len(day_msgs) == 1

    await game_phases.execute_day_phase_redis(gid, 1, [], bot, chat, None, times)
    day_msgs = [m for m in bot.sent_media if "KUN 1" in (m["caption"] or "")]
    assert len(day_msgs) == 1

