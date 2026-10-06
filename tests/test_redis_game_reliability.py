"""
Production-readiness / reliability audit tests for the Redis game engine.

These exercise the *real* production code paths (repositories, services, win
conditions, join locks, cleanup) against FakeRedis + in-memory SQLite. All
numeric values are TEST SCENARIOS ONLY and are not production limits.
"""
import asyncio

import pytest

from utils.database import redis_client
from utils.redis_game.game_models_schema import GameState
from utils.redis_game.repositories import game_repository, player_repository
from utils.redis_game.services import (
    action_service,
    phase_service,
    player_service,
    vote_service,
)
from utils.redis_game import win_conditions
from utils.redis_game import handlers as h
from models.game_data import Chat
from tests.fakes import FakeBot, FakeMessage, FakeUser, FakeChat


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
async def _new_game(chat_id=100, mode="classic", phase="waiting", creator_id=1):
    """Create a waiting game directly in Redis and register it in all indexes."""
    gid = await game_repository.generate_id()
    gs = GameState(
        game_id=gid,
        chat_id=chat_id,
        creator_id=creator_id,
        phase=phase,
        mode=mode,
        is_active=True,
        message_id=1,
    )
    await game_repository.save_game(gs, ttl_sec=86400)
    await game_repository.add_active_game(chat_id, gid)
    await redis_client.sadd("global:active_games", str(gid))
    return gid


async def _join_many(gid, uids, team=None):
    return await asyncio.gather(
        *[player_service.join_game(gid, uid, team=team) for uid in uids]
    )


# --------------------------------------------------------------------------
# PHASE 2/3 — lifecycle, joins, isolation
# --------------------------------------------------------------------------
async def test_lifecycle_join_and_transition_guard():
    gid = await _new_game(chat_id=101)

    ok = await _join_many(gid, range(1000, 1020))
    assert all(ok)
    assert await player_repository.get_players_count(gid) == 20
    assert await player_repository.get_alive_players_count(gid) == 20

    # Re-joining the same player must not create a duplicate record
    assert await player_service.join_game(gid, 1000) is False
    assert await player_repository.get_players_count(gid) == 20

    # Joining after start (phase != waiting) must be rejected
    await game_repository.update_game_field(gid, "phase", "night")
    assert await player_service.join_game(gid, 9999) is False
    assert await player_repository.player_exists(gid, 9999) is False


async def test_join_stress_no_duplicate_or_missing_players():
    gid = await _new_game(chat_id=102)
    n = 300
    await _join_many(gid, range(2000, 2000 + n))

    ids = await player_repository.get_player_ids(gid)
    assert len(ids) == n
    assert len(set(ids)) == n  # no duplicates
    assert set(ids) == set(range(2000, 2000 + n))  # none missing


async def test_same_user_concurrent_join_single_record():
    gid = await _new_game(chat_id=103)
    # 50 simultaneous clicks from the *same* user
    await asyncio.gather(*[player_service.join_game(gid, 55555) for _ in range(50)])
    ids = await player_repository.get_player_ids(gid)
    assert ids == [55555]
    assert await player_repository.get_players_count(gid) == 1


async def test_multi_game_isolation():
    g1 = await _new_game(chat_id=111)
    g2 = await _new_game(chat_id=222)

    await _join_many(g1, range(100, 110))
    await _join_many(g2, range(200, 210))

    # no cross membership
    for uid in range(100, 110):
        assert await player_repository.player_exists(g1, uid)
        assert not await player_repository.player_exists(g2, uid)
    for uid in range(200, 210):
        assert await player_repository.player_exists(g2, uid)
        assert not await player_repository.player_exists(g1, uid)

    # votes are phase/game scoped
    await vote_service.save_vote(g1, 1, 100, 101)
    await vote_service.save_vote(g2, 1, 200, 201)
    assert await vote_service.get_all_votes(g1, 1) == {100: 101}
    assert await vote_service.get_all_votes(g2, 1) == {200: 201}

    # cleaning up g1 must not touch g2
    await win_conditions.cleanup_game_redis(g1)
    assert await player_repository.get_players_count(g2) == 10
    assert await game_repository.load_game(g2) is not None
    assert await game_repository.load_game(g1) is not None  # state kept (with TTL)
    # g1 removed from indexes, g2 still active
    assert await redis_client.sismember("global:active_games", str(g1)) == 0
    assert await redis_client.sismember("global:active_games", str(g2)) == 1


# --------------------------------------------------------------------------
# PHASE 5/17 — votes, actions, callbacks
# --------------------------------------------------------------------------
async def test_vote_stress_and_duplicate_idempotency():
    gid = await _new_game(chat_id=120)
    voters = list(range(300, 400))

    # 100 voters each voting once, all concurrently
    await asyncio.gather(*[vote_service.save_vote(gid, 1, v, 999) for v in voters])
    assert len(await vote_service.get_all_votes(gid, 1)) == 100
    assert await vote_service.get_winner(gid, 1) == 999

    # same voter votes again many times -> still one entry (hash overwrite)
    await asyncio.gather(*[vote_service.save_vote(gid, 1, voters[0], 888) for _ in range(30)])
    votes = await vote_service.get_all_votes(gid, 1)
    assert len(votes) == 100
    assert votes[voters[0]] == 888

    # tie -> no winner
    await vote_service.save_vote(gid, 2, 1, 10)
    await vote_service.save_vote(gid, 2, 2, 20)
    assert await vote_service.get_winner(gid, 2) is None


async def test_stale_votes_do_not_affect_current_phase():
    gid = await _new_game(chat_id=121)
    await vote_service.save_vote(gid, 1, 10, 20)      # phase 1
    await vote_service.save_vote(gid, 2, 10, 30)      # phase 2 (player changed mind)
    assert await vote_service.get_all_votes(gid, 1) == {10: 20}
    assert await vote_service.get_all_votes(gid, 2) == {10: 30}


async def test_night_action_stress_single_action_per_actor():
    gid = await _new_game(chat_id=130)
    actors = list(range(400, 460))

    # each actor selects several targets simultaneously -> one logical action each
    await asyncio.gather(*[
        action_service.save_action(gid, 1, a, 500 + i, "kill")
        for i, a in enumerate(actors)
    ])
    await asyncio.gather(*[
        action_service.save_action(gid, 1, a, 600, "kill") for a in actors
    ])

    actions = await action_service.get_phase_actions(gid, 1)
    per_actor = {}
    for act in actions:
        per_actor.setdefault(act["actor_id"], []).append(act)
    assert len(per_actor) == len(actors)
    for a in actors:
        assert len(per_actor[a]) == 1  # no duplicate actions for one actor
        assert per_actor[a][0]["target_id"] == 600  # latest selection wins


async def test_duplicate_callback_actions_idempotent():
    gid = await _new_game(chat_id=131)
    # simulate the same button pressed 20 times
    for _ in range(20):
        await action_service.save_action(gid, 1, 77, 88, "heal")
    actions = await action_service.get_phase_actions(gid, 1)
    assert [a for a in actions if a["actor_id"] == 77] == [
        {"actor_id": 77, "target_id": 88, "action_type": "heal"}
    ]


# --------------------------------------------------------------------------
# PHASE 10/17 — cleanup
# --------------------------------------------------------------------------
async def test_cleanup_is_idempotent_and_scoped():
    gid = await _new_game(chat_id=140)
    other = await _new_game(chat_id=141)
    await _join_many(gid, range(700, 710))
    await _join_many(other, range(800, 810))

    await win_conditions.cleanup_game_redis(gid)
    await win_conditions.cleanup_game_redis(gid)  # second run must be safe

    # players of gid marked dead, indexes cleared
    alive = await player_repository.get_alive_players(gid)
    assert alive == []
    assert await redis_client.sismember("global:active_games", str(gid)) == 0
    assert await redis_client.sismember(f"chat:140:active_games", str(gid)) == 0

    # other game untouched
    assert await player_repository.get_alive_players_count(other) == 10
    assert await redis_client.sismember("global:active_games", str(other)) == 1


# --------------------------------------------------------------------------
# PHASE 17 — redis_join_locks stress
# --------------------------------------------------------------------------
async def test_join_lock_identity_under_pressure():
    h._redis_join_locks.clear()
    uid = 111111
    lock_a = h._get_join_lock(uid)
    async with lock_a:
        assert lock_a.locked()
        # heavy pressure: thousands of *other* users request locks while A is held
        for other in range(5000):
            h._get_join_lock(9_000_000 + other)
        # A must resolve to the very same lock object (no duplicate lock)
        assert h._get_join_lock(uid) is lock_a
        assert lock_a.locked()

    # after release, the structure must stay bounded (LRU enforced)
    assert len(h._redis_join_locks) <= h._MAX_JOIN_LOCKS + 1


async def test_join_lock_ttl_eviction(monkeypatch):
    h._redis_join_locks.clear()
    clock = {"t": 1000.0}
    monkeypatch.setattr(h, "monotonic", lambda: clock["t"])

    h._get_join_lock(42)
    assert 42 in h._redis_join_locks

    # move the clock past the TTL and trigger a lookup
    clock["t"] += h._LOCK_TTL + 1
    h._get_join_lock(43)
    assert 42 not in h._redis_join_locks  # expired unused lock removed


# --------------------------------------------------------------------------
# PHASE 11/12/18 — failure injection
# --------------------------------------------------------------------------
async def test_telegram_failure_does_not_corrupt_game_state():
    bot = FakeBot(fail_send=True)
    gid = await _new_game(chat_id=150)
    await _join_many(gid, range(900, 905))
    chat = await Chat.create(chat_id=150, title="t", type="supergroup")

    with pytest.raises(RuntimeError):
        await win_conditions.announce_game_result_redis(
            gid, bot, chat, winner_roles=["FUQARO"]
        )

    # state mutation happened *before* the UI call -> still consistent
    gs = await game_repository.load_game(gid)
    assert gs.phase == "end"
    assert gs.is_active is False
    # index cleanup also already happened
    assert await redis_client.sismember("global:active_games", str(gid)) == 0


async def test_redis_failure_join_does_not_partially_mutate(monkeypatch):
    gid = await _new_game(chat_id=160)

    async def boom(*args, **kwargs):
        raise RuntimeError("simulated redis outage")

    monkeypatch.setattr(player_repository, "save_player", boom)

    with pytest.raises(RuntimeError):
        await player_service.join_game(gid, 12345)

    # no half-written player / membership
    assert await redis_client.sismember(f"game:{gid}:players", "12345") == 0
    assert await game_repository.load_game(gid) is not None


# --------------------------------------------------------------------------
# PHASE 3/21 — create_game index registration (global:active_games)
# --------------------------------------------------------------------------
async def test_create_game_registers_all_active_indexes():
    from utils.redis_game.services import game_service

    bot = FakeBot()
    chat = FakeChat(chat_id=170)
    user = FakeUser(1)
    msg = FakeMessage("/game", user, chat, bot)

    game = await game_service.create_game(msg, bot, is_vs_game=False)
    assert game is not None
    assert game.phase == "waiting"

    assert await redis_client.sismember(f"chat:170:active_games", str(game.game_id)) == 1
    assert await redis_client.sismember("global:active_games", str(game.game_id)) == 1
    assert await player_service.find_player_active_game(1) is None  # creator not a player yet


# --------------------------------------------------------------------------
# PHASE 6/19 — resource observation: ended games must not leak forever
# --------------------------------------------------------------------------
async def test_ended_games_expire_and_leave_indexes():
    bot = FakeBot()
    for i in range(25):
        cid = 6000 + i
        gid = await _new_game(chat_id=cid)
        await _join_many(gid, range(10000 + i * 10, 10000 + i * 10 + 5))
        chat = await Chat.create(chat_id=cid, title="g", type="supergroup")
        await win_conditions.announce_game_result_redis(gid, bot, chat, winner_roles=["FUQARO"])
        await win_conditions.cleanup_game_redis(gid)

        # the finished game state still exists but now has a TTL (bounded growth)
        ttl = await redis_client.ttl(f"game:{gid}:state")
        assert ttl > 0

    # every finished game left the process-wide active index
    assert await redis_client.scard("global:active_games") == 0


# --------------------------------------------------------------------------
# PHASE 10/20 — full Redis cleanup completeness + idempotency
# --------------------------------------------------------------------------
async def test_full_cleanup_removes_all_game_keys():
    from utils.redis_game.services.game_service import GameService

    gid = await _new_game(chat_id=180)
    await _join_many(gid, range(50, 55))
    await vote_service.save_vote(gid, 1, 50, 51)

    await GameService._cleanup_redis(gid)
    await GameService._cleanup_redis(gid)  # idempotent

    _cursor, keys = await redis_client.scan(0, match=f"game:{gid}:*", count=100)
    assert keys == []


# --------------------------------------------------------------------------
# PHASE 4/20 — migration SQL must match the ORM model (regression guard)
# --------------------------------------------------------------------------
async def test_gameplayer_migration_columns_match_model():
    import pathlib

    from models.game_data import GamePlayer

    model_fields = set(GamePlayer._meta.fields_map.keys())
    for col in ("qm_portlat_used", "qm_tiriltir_used", "qm_xazina_used"):
        assert col in model_fields

    src = pathlib.Path("utils/database.py").read_text(encoding="utf-8")
    # the renamed (nonexistent) columns must not come back
    assert "kom_portlat_used" not in src
    assert "kom_tiriltir_used" not in src
    assert "kom_xazina_used" not in src


# --------------------------------------------------------------------------
# PHASE 2/20 — role assignment completes for every player
# --------------------------------------------------------------------------
async def test_role_assignment_completes_for_all_players():
    from models.user import User, Profile
    from utils.redis_game.role_assignment import rol_taqsimlash_redis

    cid = 7000
    gid = await _new_game(chat_id=cid, mode="classic")
    await Chat.create(chat_id=cid, title="g", type="supergroup")

    uids = list(range(20000, 20012))
    for uid in uids:
        await User.create(user_id=uid, full_name=f"U{uid}", mention="")
        u = await User.get(user_id=uid)
        await Profile.create(user=u)

    await _join_many(gid, uids)
    players = await player_repository.get_all_players(gid)
    await rol_taqsimlash_redis(players, FakeBot(), cid, "classic")

    reloaded = await player_repository.get_all_players(gid)
    assert len(reloaded) == len(uids)
    for p in reloaded:
        assert p.role, "every player must receive a role"
        assert p.maxsus_raqam is not None


# --------------------------------------------------------------------------
# PHASE 3/17 — many independent games running at once
# --------------------------------------------------------------------------
async def test_multi_game_concurrent_stress():
    games = [await _new_game(chat_id=3000 + i) for i in range(25)]

    async def populate(gid, base):
        await _join_many(gid, range(base, base + 10))
        await vote_service.save_vote(gid, 1, base, base + 1)

    await asyncio.gather(*[populate(g, 40000 + i * 100) for i, g in enumerate(games)])

    for i, gid in enumerate(games):
        base = 40000 + i * 100
        assert await player_repository.get_players_count(gid) == 10
        assert await vote_service.get_all_votes(gid, 1) == {base: base + 1}
        # no player from another game leaked in
        for j, other in enumerate(games):
            if j == i:
                continue
            assert not await player_repository.player_exists(gid, 40000 + j * 100)
    assert await redis_client.scard("global:active_games") == 25


# --------------------------------------------------------------------------
# PHASE 10/17 — cleanup of one game must not break another active game
# --------------------------------------------------------------------------
async def test_concurrent_cleanup_does_not_delete_other_game():
    a = await _new_game(chat_id=4001)
    b = await _new_game(chat_id=4002)
    await _join_many(a, range(60, 70))
    await _join_many(b, range(70, 80))

    async def cleanup_a():
        await win_conditions.cleanup_game_redis(a)

    async def keep_b_busy():
        for _ in range(20):
            await vote_service.save_vote(b, 1, 70, 71)

    await asyncio.gather(cleanup_a(), keep_b_busy())

    assert await player_repository.get_alive_players_count(b) == 10
    assert await vote_service.get_all_votes(b, 1) == {70: 71}
    assert await game_repository.load_game(b) is not None
    assert await redis_client.sismember("global:active_games", str(b)) == 1


# --------------------------------------------------------------------------
# PHASE 17 — night action resolution is deterministic
# --------------------------------------------------------------------------
async def test_night_actions_deterministic_resolution():
    gid = await _new_game(chat_id=5001)
    await _join_many(gid, [2, 3, 4])

    await action_service.save_action(gid, 1, 10, 2, "kill")
    await action_service.save_action(gid, 1, 11, 2, "heal")      # heal 2
    await action_service.save_action(gid, 1, 12, 3, "kill")
    await action_service.save_action(gid, 1, 13, 3, "protect")   # protect 3
    await action_service.save_action(gid, 1, 14, 4, "kill")      # unguarded

    result = await action_service.process_night_actions(gid, 1)
    assert 4 in result["kills"]
    assert 2 in result["survived"]
    assert 3 in result["survived"]

    p2 = await player_repository.load_player(gid, 2)
    p3 = await player_repository.load_player(gid, 3)
    p4 = await player_repository.load_player(gid, 4)
    assert p4.is_alive is False
    assert p2.is_alive is True
    assert p3.is_alive is True


# --------------------------------------------------------------------------
# PHASE 19 — measured resource observation: full lifecycle leaves no growth
# --------------------------------------------------------------------------
async def test_full_lifecycle_leaves_no_redis_growth():
    from utils.redis_game.services.game_service import GameService

    base = await redis_client.dbsize()

    for i in range(50):
        cid = 8000 + i
        gid = await _new_game(chat_id=cid)
        await _join_many(gid, range(30000 + i * 5, 30000 + i * 5 + 5))
        await GameService._cleanup_redis(gid)
        await win_conditions._clear_active_indexes(gid, cid)

    after = await redis_client.dbsize()
    # Only the persistent id counter may remain — no per-game accumulation.
    assert after - base <= 1, f"redis keys grew by {after - base}"




