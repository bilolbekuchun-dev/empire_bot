"""
`/start` arbitration window.

When a group `/start` (start-the-game) arrives, the bot holds a short
arbitration window (default 500 ms). If a `/game` arrives for the same chat
during that window, `/game` wins and the `/start` is cancelled. A `/game`
arriving *after* the window can no longer cancel the already-accepted `/start`.

The window decision is based on high-resolution server-side arrival time
(``time.monotonic_ns()``), not on the physical button-press time on the
user's device.

State is kept in Redis so it is shared between the concurrent handlers:
``chat:{chat_id}:start_arb`` -> ``"{token}:{monotonic_ns_at_arrival}"``.
"""
import asyncio
import logging
import os
import time
import uuid
from typing import Optional, Tuple

from utils.database import redis_client as r

logger = logging.getLogger(__name__)

# Configurable arbitration window (milliseconds). DEFAULT = 500 ms.
DEFAULT_WINDOW_MS = 500
# Safety grace on the Redis key TTL so the window check never silently expires
# before `/start` has had a chance to inspect it.
_GRACE_MS = 2000

_NANOS_PER_MS = 1_000_000


def _window_ms() -> int:
    try:
        return int(os.getenv("START_ARBITRATION_WINDOW_MS", str(DEFAULT_WINDOW_MS)))
    except (TypeError, ValueError):
        return DEFAULT_WINDOW_MS


def _key(chat_id) -> str:
    return f"chat:{chat_id}:start_arb"


async def begin_start_window(chat_id) -> Optional[Tuple[str, int]]:
    """
    Try to open the arbitration window for a `/start`.

    Returns ``(token, arrival_ns)`` if this `/start` owns the window, or
    ``None`` if another `/start` is already pending (only one lifecycle wins).
    Uses SET NX so the decision is atomic.
    """
    token = uuid.uuid4().hex
    arrival_ns = time.monotonic_ns()
    payload = f"{token}:{arrival_ns}"
    try:
        ok = await r.set(_key(chat_id), payload, nx=True, px=_window_ms() + _GRACE_MS)
    except Exception as exc:
        # Redis unavailable -> degrade to "start allowed" rather than blocking.
        logger.warning("start arbitration open failed (chat=%s): %s", chat_id, exc)
        return (token, arrival_ns)
    if not ok:
        return None
    return (token, arrival_ns)


async def await_start_window(chat_id, token: str) -> bool:
    """
    Wait out the arbitration window.

    Returns True if `/start` may proceed, False if it was cancelled by a `/game`
    (or superseded) during the window.
    """
    await asyncio.sleep(_window_ms() / 1000.0)
    try:
        val = await r.get(_key(chat_id))
    except Exception as exc:
        logger.warning("start arbitration read failed (chat=%s): %s", chat_id, exc)
        return True
    if val is None:
        return False                      # cancelled by /game
    return val.startswith(f"{token}:")


async def finish_start(chat_id, token: str) -> None:
    """Release the arbitration window after `/start` has been decided."""
    try:
        val = await r.get(_key(chat_id))
        if val and val.startswith(f"{token}:"):
            await r.delete(_key(chat_id))
    except Exception as exc:
        logger.debug("start arbitration clear failed (chat=%s): %s", chat_id, exc)


async def cancel_pending_start(chat_id) -> bool:
    """
    Called by `/game`: cancel a `/start` whose arbitration window is still open.

    Returns True if a pending `/start` was cancelled. A `/game` that arrives
    after the window has elapsed does NOT cancel the accepted `/start`.
    """
    try:
        val = await r.get(_key(chat_id))
        if not val:
            return False
        try:
            _token, start_ns = val.split(":")
            start_ns = int(start_ns)
        except Exception:
            await r.delete(_key(chat_id))
            return True
        if time.monotonic_ns() - start_ns <= _window_ms() * _NANOS_PER_MS:
            await r.delete(_key(chat_id))
            return True
        return False
    except Exception as exc:
        logger.warning("start arbitration cancel failed (chat=%s): %s", chat_id, exc)
        return False