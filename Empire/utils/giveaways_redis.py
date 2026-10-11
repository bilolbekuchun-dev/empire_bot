from .database import redis_client
import json
import time
import asyncio
from datetime import datetime, timezone
from collections import defaultdict

# TTL for giveaway locks (30 seconds)
_LOCK_TTL = 30
# TTL for giveaway data (7 days)
_GIVEAWAY_TTL = 604800

# Batch settings
_BATCH_SIZE = 2  # Har 2 claimdan keyin flush
_BATCH_TIMEOUT = 1.0  # Yoki 1 sekund timeout

# In-memory buffers for batching
_collected_buffers = defaultdict(list)  # {giveaway_id: [user_ids]}
_winner_buffers = defaultdict(list)  # {giveaway_id: [(user_id, full_name, reward)]}
_buffer_locks = defaultdict(asyncio.Lock)
_flush_tasks = {}  # {giveaway_id: task}


def _lock_key(giveaway_id: int, user_id: int) -> str:
    return f"giveaway_lock:{giveaway_id}:{user_id}"


def _collected_set_key(giveaway_id: int) -> str:
    return f"giveaway_collected:{giveaway_id}"


def _winner_list_key(giveaway_id: int) -> str:
    return f"giveaway_winners:{giveaway_id}"


async def is_processing(giveaway_id: int, user_id: int) -> bool:
    """Check if a user is currently being processed for a giveaway (Redis-based)."""
    try:
        return await redis_client.exists(_lock_key(giveaway_id, user_id)) > 0
    except Exception:
        return False


async def is_processing_change(giveaway_id: int, user_id: int) -> bool:
    """Check if a user is currently being processed for a giveaway (alias)."""
    return await is_processing(giveaway_id, user_id)


async def mark_as_processing(giveaway_id: int, user_id: int) -> bool:
    """Mark a user as being processed for a giveaway (Redis SET NX with TTL)."""
    try:
        key = _lock_key(giveaway_id, user_id)
        # SET NX: only set if not exists (atomic)
        result = await redis_client.set(key, "1", nx=True, ex=_LOCK_TTL)
        return result is not None
    except Exception:
        return False


async def mark_as_processing_change(giveaway_id: int, user_id: int) -> bool:
    """Mark a user as being processed for a giveaway (alias)."""
    return await mark_as_processing(giveaway_id, user_id)


async def unmark_as_processing(giveaway_id: int, user_id: int):
    """Unmark a user as being processed for a giveaway (Redis DELETE)."""
    try:
        await redis_client.delete(_lock_key(giveaway_id, user_id))
    except Exception:
        pass


async def unmark_as_processing_change(giveaway_id: int, user_id: int):
    """Unmark a user as being processed for a giveaway (alias)."""
    await unmark_as_processing(giveaway_id, user_id)


async def add_collected_user(giveaway_id: int, user_id: int):
    """Add a user to the collected set (Redis SET)."""
    try:
        await redis_client.sadd(_collected_set_key(giveaway_id), str(user_id))
        await redis_client.expire(_collected_set_key(giveaway_id), _GIVEAWAY_TTL)
    except Exception:
        pass


async def batch_add_collected_users(giveaway_id: int, user_ids: list):
    """Add multiple users to the collected set in one Redis SADD call."""
    if not user_ids:
        return
    try:
        await redis_client.sadd(_collected_set_key(giveaway_id), *[str(uid) for uid in user_ids])
        await redis_client.expire(_collected_set_key(giveaway_id), _GIVEAWAY_TTL)
    except Exception:
        pass


async def queue_collected_user(giveaway_id: int, user_id: int):
    """Queue user for batch write to Redis."""
    lock = _buffer_locks[giveaway_id]
    async with lock:
        _collected_buffers[giveaway_id].append(user_id)
        
        # Flush if buffer size reached
        if len(_collected_buffers[giveaway_id]) >= _BATCH_SIZE:
            await _flush_collected_buffer(giveaway_id)
        else:
            # Schedule delayed flush if not already scheduled
            if giveaway_id not in _flush_tasks or _flush_tasks[giveaway_id].done():
                _flush_tasks[giveaway_id] = asyncio.create_task(
                    _delayed_flush_collected(giveaway_id)
                )


async def _delayed_flush_collected(giveaway_id: int):
    """Flush buffer after timeout."""
    await asyncio.sleep(_BATCH_TIMEOUT)
    await _flush_collected_buffer(giveaway_id)


async def _flush_collected_buffer(giveaway_id: int):
    """Flush collected users buffer to Redis."""
    lock = _buffer_locks[giveaway_id]
    async with lock:
        if not _collected_buffers[giveaway_id]:
            return
        
        user_ids = _collected_buffers[giveaway_id]
        _collected_buffers[giveaway_id] = []
        
        if user_ids:
            await batch_add_collected_users(giveaway_id, user_ids)


async def is_collected_user(giveaway_id: int, user_id: int) -> bool:
    """Check if a user has already collected from this giveaway (checks both buffer and Redis)."""
    # First check in-memory buffer (for recent claims not yet flushed)
    lock = _buffer_locks[giveaway_id]
    async with lock:
        if user_id in _collected_buffers[giveaway_id]:
            return True
    
    # Then check Redis
    try:
        return await redis_client.sismember(_collected_set_key(giveaway_id), str(user_id))
    except Exception:
        return False


async def get_collected_users(giveaway_id: int) -> list:
    """Get all collected users for this giveaway (Redis SMEMBERS)."""
    try:
        members = await redis_client.smembers(_collected_set_key(giveaway_id))
        return [int(uid) for uid in members if uid.isdigit()]
    except Exception:
        return []


async def remove_collected_users(giveaway_id: int):
    """Remove the collected set for this giveaway (Redis DELETE)."""
    try:
        await redis_client.delete(_collected_set_key(giveaway_id))
    except Exception:
        pass


async def add_winner_detail(giveaway_id: int, user_id: int, full_name: str, reward: int):
    """Add winner detail to the winner list (Redis LIST)."""
    try:
        winner_data = json.dumps({"user_id": user_id, "full_name": full_name, "reward": reward})
        await redis_client.rpush(_winner_list_key(giveaway_id), winner_data)
        await redis_client.expire(_winner_list_key(giveaway_id), _GIVEAWAY_TTL)
    except Exception:
        pass


async def batch_add_winner_details(giveaway_id: int, winners: list):
    """Add multiple winner details in one Redis Pipeline."""
    if not winners:
        return
    try:
        async with redis_client.pipeline() as pipe:
            for user_id, full_name, reward in winners:
                winner_data = json.dumps({"user_id": user_id, "full_name": full_name, "reward": reward})
                pipe.rpush(_winner_list_key(giveaway_id), winner_data)
            pipe.expire(_winner_list_key(giveaway_id), _GIVEAWAY_TTL)
            await pipe.execute()
    except Exception:
        pass


async def queue_winner_detail(giveaway_id: int, user_id: int, full_name: str, reward: int):
    """Queue winner detail for batch write to Redis."""
    lock = _buffer_locks[giveaway_id]
    async with lock:
        _winner_buffers[giveaway_id].append((user_id, full_name, reward))
        
        # Flush if buffer size reached
        if len(_winner_buffers[giveaway_id]) >= _BATCH_SIZE:
            await _flush_winner_buffer(giveaway_id)
        else:
            # Schedule delayed flush if not already scheduled
            if giveaway_id not in _flush_tasks or _flush_tasks[giveaway_id].done():
                _flush_tasks[giveaway_id] = asyncio.create_task(
                    _delayed_flush_winner(giveaway_id)
                )


async def _delayed_flush_winner(giveaway_id: int):
    """Flush buffer after timeout."""
    await asyncio.sleep(_BATCH_TIMEOUT)
    await _flush_winner_buffer(giveaway_id)


async def _flush_winner_buffer(giveaway_id: int):
    """Flush winner details buffer to Redis."""
    lock = _buffer_locks[giveaway_id]
    async with lock:
        if not _winner_buffers[giveaway_id]:
            return
        
        winners = _winner_buffers[giveaway_id]
        _winner_buffers[giveaway_id] = []
        
        if winners:
            await batch_add_winner_details(giveaway_id, winners)


async def flush_all_giveaway_buffers(giveaway_id: int):
    """Force flush all buffers for a giveaway (call when giveaway ends)."""
    await _flush_collected_buffer(giveaway_id)
    await _flush_winner_buffer(giveaway_id)


async def get_winner_details(giveaway_id: int) -> list:
    """Get all winner details for this giveaway (Redis LRANGE)."""
    try:
        raw_list = await redis_client.lrange(_winner_list_key(giveaway_id), 0, -1)
        winners = []
        for item in raw_list:
            try:
                data = json.loads(item)
                winners.append((data["user_id"], data["full_name"], data["reward"]))
            except Exception:
                continue
        return winners
    except Exception:
        return []


async def remove_winner_details(giveaway_id: int):
    """Remove the winner list for this giveaway (Redis DELETE)."""
    try:
        await redis_client.delete(_winner_list_key(giveaway_id))
    except Exception:
        pass







async def save_giveaway(giveaway):
    giveaway_key = f"giveaway:{giveaway['id']}"
    # Ma'lumotlarni Hash sifatida saqlash
    data = {
        "id": str(giveaway["id"]),
        "creator_id": str(giveaway["creator_id"]),  # ForeignKey sifatida user ID
        "chat_id": str(giveaway["chat_id"]),
        "message_id": str(giveaway["message_id"]),
        "total_amount": str(giveaway["total_amount"]),
        "remaining_amount": str(giveaway["remaining_amount"]),
        "collected_users": json.dumps(giveaway["collected_users"]),  # JSON sifatida
        "created_at": giveaway["created_at"].isoformat()  # ISO formatida
    }
    for field, value in data.items():
        await redis_client.hset(giveaway_key, field, value)

async def get_giveaway(giveaway_id):
    giveaway_key = f"giveaway:{giveaway_id}"
    data = await redis_client.hgetall(giveaway_key)
    if not data:
        return None
    return {
        "id": int(data["id"]),
        "creator_id": int(data["creator_id"]),
        "chat_id": int(data["chat_id"]),
        "message_id": int(data["message_id"]),
        "total_amount": int(data["total_amount"]),
        "remaining_amount": int(data["remaining_amount"]),
        "collected_users": json.loads(data["collected_users"]),
        "created_at": datetime.fromisoformat(data["created_at"])
    }

async def create_giveaway(creator_id, chat_id, message_id, total_amount):
    # ID generatsiya qilish uchun INCR ishlatamiz
    new_id = await redis_client.incr("giveaway:counter")
    giveaway = {
        "id": new_id,
        "creator_id": creator_id,
        "chat_id": chat_id,
        "message_id": message_id,
        "total_amount": total_amount,
        "remaining_amount": total_amount,
        "collected_users": [],
        "created_at": datetime.now(timezone.utc)
    }
    await save_giveaway(giveaway)
    return giveaway

async def update_giveaway(giveaway_id, updates):
    giveaway_key = f"giveaway:{giveaway_id}"
    if await redis_client.exists(giveaway_key):
        # Faqat yangilanadigan maydonlarni konvertatsiya qilish
        if "collected_users" in updates:
            updates["collected_users"] = json.dumps(updates["collected_users"])
        if "created_at" in updates:
            updates["created_at"] = updates["created_at"].isoformat()
        for field, value in updates.items():
            await redis_client.hset(giveaway_key, field, value)
        return True
    return False

async def delete_giveaway(giveaway_id):
    giveaway_key = f"giveaway:{giveaway_id}"
    if await redis_client.exists(giveaway_key):
        await redis_client.delete(giveaway_key)
        return True
    return False

