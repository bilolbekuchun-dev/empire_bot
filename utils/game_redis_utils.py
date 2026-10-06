from utils.database import redis_client as r

async def create_or_get_game_redis(chat_id: int) -> dict:
    game_key = f"game:{chat_id}"
    game_data = await r.hgetall(game_key)
    if not game_data:
        # Initialize default game data
        default_data = {
            "status": "waiting",
            "players": "0",
            "mode": "classic",
            # Add other default fields as necessary
        }
        for key, value in default_data.items():
            await r.hset(game_key, key, value)
        return False
    return True

async def remove_game_redis(chat_id: int):
    game_key = f"game:{chat_id}"
    await r.delete(game_key)