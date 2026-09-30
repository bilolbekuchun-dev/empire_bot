from .database import redis_client
import json
from datetime import datetime, timezone

participation_locks = set()
stopping_changes = set()
giveaway_amounts = {}
giveaway_collected = {}  # {giveaway_id: [user_id, ...]}

def set_giveaway_amount(giveaway_id, amount):
    giveaway_amounts[giveaway_id] = amount

def minus_giveaway_amount(giveaway_id):
    if giveaway_amounts.get(giveaway_id):
        if giveaway_amounts[giveaway_id] > 0:
            giveaway_amounts[giveaway_id] -= 1
            return True
    return False

def remove_giveaway_amount(giveaway_id):
    if giveaway_amounts.get(giveaway_id):
        del giveaway_amounts[giveaway_id]

def init_giveaway_collected(giveaway_id, collected_users):
    giveaway_collected[giveaway_id] = list(collected_users)

def add_collected_user(giveaway_id, user_id):
    giveaway_collected.setdefault(giveaway_id, []).append(user_id)

def is_collected_user(giveaway_id, user_id):
    return user_id in giveaway_collected.get(giveaway_id, [])

def get_collected_users(giveaway_id):
    return list(giveaway_collected.get(giveaway_id, []))

def remove_collected_users(giveaway_id):
    giveaway_collected.pop(giveaway_id, None)

def is_processing(giveaway_id: int, user_id: int) -> bool:
    """Check if a user is currently being processed for a giveaway."""
    return f"{giveaway_id}:{user_id}" in participation_locks

def is_processing_change(giveaway_id: int, user_id: int) -> bool:
    """Check if a user is currently being processed for a giveaway."""
    return f"{giveaway_id}:{user_id}" in participation_locks

def mark_as_processing(giveaway_id: int, user_id: int):
    """Mark a user as being processed for a giveaway."""
    participation_locks.add(f"{giveaway_id}:{user_id}")

def mark_as_processing_change(giveaway_id: int, user_id: int):
    """Mark a user as being processed for a giveaway."""
    participation_locks.add(f"{giveaway_id}:{user_id}")

def unmark_as_processing(giveaway_id: int, user_id: int):
    """Unmark a user as being processed for a giveaway."""
    lock_key = f"{giveaway_id}:{user_id}"
    if lock_key in participation_locks:
        participation_locks.remove(lock_key)

def unmark_as_processing_change(giveaway_id: int, user_id: int):
    """Unmark a user as being processed for a giveaway."""
    lock_key = f"{giveaway_id}:{user_id}"
    if lock_key in participation_locks:
        participation_locks.remove(lock_key)







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

