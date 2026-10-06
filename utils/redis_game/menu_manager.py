"""
Canonical per-chat `/game` menu message lifecycle.

Guarantees **exactly one** canonical game-menu message per chat even when
several `/game` handlers run concurrently:

    acquire per-chat lock
      read canonical message id
      delete old canonical message   (already-gone == success)
      send the new menu message
      store the new id as canonical  (only after a successful send)
    release lock

Reading the canonical id *inside* the critical section is what makes stale
message ids impossible.

The canonical id lives in Redis (``chat:{chat_id}:game_menu_message_id``) so it
survives across handlers and process restarts. The lock is process-local
(``asyncio.Lock``) which is correct for the current single-process asyncio bot.
"""
import asyncio
import logging
from collections import OrderedDict
from typing import Awaitable, Callable, Optional

from utils.database import redis_client as r

logger = logging.getLogger(__name__)

# Bounded LRU of per-chat locks (never unbounded; held locks are never evicted).
_MAX_CHAT_LOCKS = 5000
_chat_locks: "OrderedDict[int, asyncio.Lock]" = OrderedDict()

# Canonical menu id is kept for the typical game lifetime.
_MENU_TTL = 86400


def get_chat_lock(chat_id: int) -> asyncio.Lock:
    """Return the (process-local) lock serializing menu operations for a chat."""
    lock = _chat_locks.get(chat_id)
    if lock is None:
        lock = asyncio.Lock()
        _chat_locks[chat_id] = lock
    _chat_locks.move_to_end(chat_id)

    # Evict least-recently-used *unlocked* entries; never evict a held lock.
    while len(_chat_locks) > _MAX_CHAT_LOCKS:
        oldest_id, oldest = next(iter(_chat_locks.items()))
        if oldest.locked():
            break
        _chat_locks.popitem(last=False)
    return lock


def _menu_key(chat_id) -> str:
    return f"chat:{chat_id}:game_menu_message_id"


async def get_canonical_message_id(chat_id) -> Optional[int]:
    try:
        val = await r.get(_menu_key(chat_id))
        return int(val) if val else None
    except Exception as exc:
        logger.warning("canonical menu read failed (chat=%s): %s", chat_id, exc)
        return None


async def set_canonical_message_id(chat_id, message_id) -> None:
    try:
        await r.set(_menu_key(chat_id), str(int(message_id)), ex=_MENU_TTL)
    except Exception as exc:
        logger.warning("canonical menu write failed (chat=%s): %s", chat_id, exc)


async def clear_canonical_message_id(chat_id) -> None:
    try:
        await r.delete(_menu_key(chat_id))
    except Exception as exc:
        logger.warning("canonical menu clear failed (chat=%s): %s", chat_id, exc)


async def delete_canonical_message(chat_id, bot) -> bool:
    """
    Best-effort delete of the current canonical message.

    A message that is already gone / inaccessible is treated as success so an
    already-deleted message can never abort `/game`.
    """
    mid = await get_canonical_message_id(chat_id)
    if not mid:
        return True
    try:
        await bot.delete_message(chat_id=chat_id, message_id=mid)
        return True
    except Exception as exc:
        # Idempotent: message may have been deleted by an admin/manually.
        logger.info("canonical menu delete skipped (chat=%s msg=%s): %s", chat_id, mid, exc)
        return False


async def replace_menu_locked(
    chat_id: int,
    bot,
    send: Callable[[], Awaitable],
    *,
    game_id=None,
):
    """
    Replace the canonical menu message.

    The caller MUST already hold ``get_chat_lock(chat_id)``.

    ``send`` is an async callable that sends the new menu and returns the sent
    message (or None). The canonical id is only overwritten after ``send``
    succeeds, so a failed send can never store an invalid id.
    """
    await delete_canonical_message(chat_id, bot)

    try:
        msg = await send()
    except Exception as exc:
        logger.error("menu send failed (chat=%s): %s", chat_id, exc)
        return None

    new_id = getattr(msg, "message_id", None) if msg is not None else None
    if not new_id:
        logger.error("menu send returned no message id (chat=%s)", chat_id)
        return None

    await set_canonical_message_id(chat_id, new_id)

    if game_id is not None:
        try:
            from utils.redis_game.repositories.game_repository import game_repository as game_repo
            await game_repo.update_game_field(game_id, "message_id", new_id)
        except Exception as exc:
            logger.warning("game.message_id sync failed (game=%s): %s", game_id, exc)

    return msg


async def replace_menu(chat_id: int, bot, send: Callable[[], Awaitable], *, game_id=None):
    """Acquire the chat lock and replace the canonical menu message."""
    lock = get_chat_lock(chat_id)
    async with lock:
        return await replace_menu_locked(chat_id, bot, send, game_id=game_id)