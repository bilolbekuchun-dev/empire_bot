"""
Game handler wrappers.
Route game commands to the Redis implementation if Redis is active, or fallback.
"""
from aiogram import Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from config import REDIS_GAME_ENABLED


async def _is_redis_alive() -> bool:
    if not REDIS_GAME_ENABLED:
        return False
    try:
        from utils.database import redis_client
        if hasattr(redis_client, "_real"):
            await redis_client._real.ping()
            return True
        await redis_client.ping()
        return True
    except Exception:
        return False


async def create_game_handler_wrapper(message: Message, bot: Bot):
    if await _is_redis_alive():
        from utils.redis_game import create_game_handler_redis
        return await create_game_handler_redis(message, bot)
    else:
        from utils.game_logic import create_game_handler
        return await create_game_handler(message, bot)


async def create_vs_game_handler_wrapper(message: Message, bot: Bot):
    if await _is_redis_alive():
        from utils.redis_game import create_vs_game_handler_redis
        return await create_vs_game_handler_redis(message, bot)
    else:
        from utils.game_logic import create_vs_game_handler
        return await create_vs_game_handler(message, bot)


async def join_game_handler_wrapper(message: Message, bot: Bot, state: FSMContext):
    if await _is_redis_alive():
        from utils.redis_game import join_game_handler_redis
        return await join_game_handler_redis(message, bot, state)
    else:
        from utils.game_logic import join_game_handler
        return await join_game_handler(message, bot, state)


async def kick_player_wrapper(message: Message, bot: Bot):
    if await _is_redis_alive():
        from utils.redis_game import kick_player_redis
        return await kick_player_redis(message, bot)
    else:
        from utils.game_logic import kick_player
        return await kick_player(message, bot)


async def leave_game_wrapper(message: Message, bot: Bot):
    if await _is_redis_alive():
        from utils.redis_game import leave_game_redis
        return await leave_game_redis(message, bot)
    else:
        from utils.game_logic import leave_game
        return await leave_game(message, bot)


async def stop_game_handler_wrapper(message: Message, bot: Bot):
    if await _is_redis_alive():
        from utils.redis_game import stop_game_handler_redis
        return await stop_game_handler_redis(message, bot)
    else:
        from utils.game_logic import stop_game_handler
        return await stop_game_handler(message, bot)


async def start_game_handler_wrapper(message: Message, bot: Bot, state):
    if await _is_redis_alive():
        from utils.redis_game import start_game_handler_redis
        return await start_game_handler_redis(message, bot, state)
    else:
        from utils.game_logic import start_game_handler
        return await start_game_handler(message, bot, state)
