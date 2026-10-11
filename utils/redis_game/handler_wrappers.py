"""
Game handler wrappers with feature flag routing.
Routes between legacy PostgreSQL and new Redis implementations.
"""
from aiogram import Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
import config
from utils.redis_game.migration_utils import should_use_redis


async def create_game_handler_wrapper(message: Message, bot: Bot):
    """
    Wrapper for create_game_handler with feature flag routing.
    """
    if should_use_redis(message.chat.id):
        from utils.redis_game import create_game_handler_redis
        return await create_game_handler_redis(message, bot)
    else:
        from utils.game_logic import create_game_handler
        return await create_game_handler(message, bot)


async def create_vs_game_handler_wrapper(message: Message, bot: Bot):
    """
    Wrapper for create_vs_game_handler with feature flag routing.
    """
    if should_use_redis(message.chat.id):
        from utils.redis_game import create_vs_game_handler_redis
        return await create_vs_game_handler_redis(message, bot)
    else:
        from utils.game_logic import create_vs_game_handler
        return await create_vs_game_handler(message, bot)


async def join_game_handler_wrapper(message: Message, bot: Bot, state: FSMContext):
    """
    Wrapper for join_game_handler with feature flag routing.
    Note: Need to extract chat_id from game_id in message.
    """
    game_id = message.text.split("_")[1]
    
    # Check if this is a Redis game
    # For Redis games, game_id is string UUID format
    # For PostgreSQL games, game_id is integer
    if should_use_redis(message.chat.id) or not game_id.isdigit():
        # Likely Redis game (UUID format)
        from utils.redis_game import join_game_handler_redis
        return await join_game_handler_redis(message, bot, state)
    else:
        # PostgreSQL game (integer ID)
        from utils.game_logic import join_game_handler
        return await join_game_handler(message, bot, state)


async def kick_player_wrapper(message: Message, bot: Bot):
    """
    Wrapper for kick_player with feature flag routing.
    """
    if should_use_redis(message.chat.id):
        from utils.redis_game import kick_player_redis
        return await kick_player_redis(message, bot)
    else:
        from utils.game_logic import kick_player
        return await kick_player(message, bot)


async def leave_game_wrapper(message: Message, bot: Bot):
    """
    Wrapper for leave_game with feature flag routing.
    Note: User might be in Redis or PostgreSQL game.
    Need to check both.
    """
    # Try Redis first if enabled
    if config.REDIS_GAME_ENABLED:
        from utils.redis_game import leave_game_redis
        try:
            # Try Redis version
            await leave_game_redis(message, bot)
            return
        except:
            pass
    
    # Fallback to legacy
    from utils.game_logic import leave_game
    return await leave_game(message, bot)


async def stop_game_handler_wrapper(message: Message, bot: Bot):
    """
    Wrapper for stop_game_handler with feature flag routing.
    """
    if should_use_redis(message.chat.id):
        from utils.redis_game import stop_game_handler_redis
        return await stop_game_handler_redis(message, bot)
    else:
        from utils.game_logic import stop_game_handler
        return await stop_game_handler(message, bot)


async def start_game_handler_wrapper(message: Message, bot: Bot, state):
    """
    Wrapper for start_game_handler with feature flag routing.
    """
    if should_use_redis(message.chat.id):
        from utils.redis_game import start_game_handler_redis
        return await start_game_handler_redis(message, bot, state)
    else:
        from utils.game_logic import start_game_handler
        return await start_game_handler(message, bot, state)
