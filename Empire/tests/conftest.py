"""
Pytest bootstrap for the reliability audit suite.

Sets up a deterministic, isolated environment *before* the application modules
are imported:

* Redis is pointed at an unreachable host so ``utils.database.LazyRedis``
  falls back to its built-in FakeRedis (no external server required).
* The database is a throw-away in-memory SQLite instance.
"""
import os
import sys
from pathlib import Path

EMPIRE_DIR = Path(__file__).resolve().parents[1]
if str(EMPIRE_DIR) not in sys.path:
    sys.path.insert(0, str(EMPIRE_DIR))

# --- environment must be set before importing the app -----------------------
os.environ["REDIS_HOST"] = "127.0.0.1"
os.environ["REDIS_PORT"] = "1"          # unreachable -> FakeRedis fallback
os.environ["DATABASE_URL"] = "sqlite://:memory:"
os.environ.setdefault("ADMINS", "1")
os.environ.setdefault("TOKEN", "123456:TEST")
os.environ.setdefault("BOT_URL", "https://t.me/test_empire_bot")

import pytest_asyncio  # noqa: E402
from tortoise import Tortoise  # noqa: E402

MODELS = {
    "models": [
        "models.game_data",
        "models.user",
        "models.game_set",
        "models.airdrop",
    ]
}


@pytest_asyncio.fixture(autouse=True)
async def isolated_env():
    """Fresh SQLite schema + fresh Redis keys for every test."""
    await Tortoise.init(db_url="sqlite://:memory:", modules=MODELS)
    await Tortoise.generate_schemas()

    from utils.database import redis_client
    try:
        await redis_client.flushall()
    except Exception:
        pass

    # reset the in-process presentation duplicate guard
    try:
        from utils.redis_game.presentation import reset_presentation_cache
        reset_presentation_cache()
    except Exception:
        pass

    yield

    await Tortoise.close_connections()
