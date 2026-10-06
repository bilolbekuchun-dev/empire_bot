"""
Standalone stress + resource observation runner (no pytest required).

Usage (from the ``Empire`` directory):
    python tests/stress_observe.py

Runs several increasing scenarios of virtual games/players and reports wall
time, asyncio task count, traced Python memory, and Redis key growth.
All numbers are TEST SCENARIOS ONLY — not production limits.
"""
import asyncio
import os
import sys
import time
import tracemalloc
from pathlib import Path

EMPIRE_DIR = Path(__file__).resolve().parents[1]
if str(EMPIRE_DIR) not in sys.path:
    sys.path.insert(0, str(EMPIRE_DIR))

os.environ["REDIS_HOST"] = "127.0.0.1"
os.environ["REDIS_PORT"] = "1"
os.environ["DATABASE_URL"] = "sqlite://:memory:"

from tortoise import Tortoise  # noqa: E402

from utils.database import redis_client  # noqa: E402
from utils.redis_game.game_models_schema import GameState  # noqa: E402
from utils.redis_game.repositories import game_repository, player_repository  # noqa: E402
from utils.redis_game.services import (  # noqa: E402
    action_service,
    player_service,
    vote_service,
)
from utils.redis_game.services.game_service import GameService  # noqa: E402
from utils.redis_game import win_conditions  # noqa: E402

MODELS = {
    "models": ["models.game_data", "models.user", "models.game_set", "models.airdrop"]
}


async def _game(chat_id):
    gid = await game_repository.generate_id()
    gs = GameState(game_id=gid, chat_id=chat_id, creator_id=1, phase="waiting",
                   mode="classic", is_active=True, message_id=1)
    await game_repository.save_game(gs, ttl_sec=86400)
    await game_repository.add_active_game(chat_id, gid)
    await redis_client.sadd("global:active_games", str(gid))
    return gid


async def scenario(name, n_games, players_per_game, base_uid):
    await redis_client.flushall()
    tracemalloc.start()
    t0 = time.perf_counter()

    games = [await _game(10000 + i) for i in range(n_games)]

    async def run_game(i, gid):
        uids = range(base_uid + i * players_per_game, base_uid + (i + 1) * players_per_game)
        await asyncio.gather(*[player_service.join_game(gid, u) for u in uids])
        # everyone votes, plus night actions from half of them
        await asyncio.gather(*[vote_service.save_vote(gid, 1, u, base_uid + i * players_per_game)
                               for u in uids])
        await asyncio.gather(*[action_service.save_action(gid, 1, u, base_uid + i * players_per_game + 1, "kill")
                               for u in list(uids)[: max(1, players_per_game // 2)]])

    await asyncio.gather(*[run_game(i, g) for i, g in enumerate(games)])

    created_players = n_games * players_per_game
    mid_keys = await redis_client.dbsize()

    # end + clean up every game
    for i, gid in enumerate(games):
        await GameService._cleanup_redis(gid)
        await win_conditions._clear_active_indexes(gid, 10000 + i)

    elapsed = time.perf_counter() - t0
    cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    after_keys = await redis_client.dbsize()
    tasks = len([t for t in asyncio.all_tasks() if not t.done()])

    print(f"{name:<28} games={n_games:<4} players={created_players:<5} "
          f"time={elapsed:6.2f}s  peak_mem={peak/1024/1024:6.2f}MB  "
          f"keys_peak={mid_keys:<5} keys_after_cleanup={after_keys:<4} tasks={tasks}")
    return after_keys


async def main():
    await Tortoise.init(db_url="sqlite://:memory:", modules=MODELS)
    await Tortoise.generate_schemas()

    print("=" * 110)
    print("STRESS / RESOURCE OBSERVATION  (FakeRedis + in-memory SQLite)")
    print("=" * 110)

    base = 1_000_000
    await scenario("small", 5, 10, base)
    await scenario("medium", 25, 20, base + 10_000)
    await scenario("high-concurrency", 60, 30, base + 100_000)
    await scenario("extreme-stress", 120, 40, base + 500_000)

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
