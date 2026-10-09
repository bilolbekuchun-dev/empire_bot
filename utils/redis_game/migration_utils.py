"""
Migration utilities for gradual Redis transition.
Provides decorators and helpers for safe feature flag rollout.
"""
from functools import wraps
from typing import Callable, Any
from aiogram.types import Message, CallbackQuery
import config


def should_use_redis(chat_id: int) -> bool:
    """
    Determine if Redis should be used for this chat.
    
    Args:
        chat_id: Telegram chat ID
        
    Returns:
        True if Redis is enabled globally
    """
    return getattr(config, "REDIS_GAME_ENABLED", True)



def redis_migration(*, 
                     redis_func: Callable, 
                     legacy_func: Callable,
                     get_chat_id: Callable[[Any], int] = None):
    """
    Decorator for gradual migration from legacy to Redis implementation.
    
    Usage:
        @redis_migration(
            redis_func=new_redis_handler,
            legacy_func=old_db_handler,
            get_chat_id=lambda msg: msg.chat.id
        )
        async def handler(message: Message, *args, **kwargs):
            # This will be replaced by redis_func or legacy_func
            pass
    
    Args:
        redis_func: New Redis-based implementation
        legacy_func: Original database implementation
        get_chat_id: Function to extract chat_id from first argument (defaults to msg.chat.id)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract chat_id from first argument (Message or CallbackQuery)
            first_arg = args[0] if args else None
            
            if get_chat_id:
                chat_id = get_chat_id(first_arg)
            elif isinstance(first_arg, Message):
                chat_id = first_arg.chat.id
            elif isinstance(first_arg, CallbackQuery):
                chat_id = first_arg.message.chat.id
            else:
                # Fallback to legacy if can't determine chat_id
                return await legacy_func(*args, **kwargs)
            
            # Route to appropriate implementation
            if should_use_redis(chat_id):
                return await redis_func(*args, **kwargs)
            else:
                return await legacy_func(*args, **kwargs)
        
        return wrapper
    return decorator


async def migrate_active_game_to_redis(chat_id: int) -> bool:
    """
    Migrate an active game from PostgreSQL to Redis.
    Used for hot migration of running games.
    
    Args:
        chat_id: Chat ID with active game
        
    Returns:
        True if migration successful, False otherwise
    """
    try:
        from models import Game, GamePlayer
        from utils.redis_game import GameService, PlayerService
        from utils.redis_game.game_models_schema import GameState, PlayerState
        
        # Get active game from PostgreSQL
        game = await Game.filter(
            chat_id=chat_id,
            status__in=["waiting", "started"]
        ).first()
        
        if not game:
            return False
        
        # Get all players
        players = await GamePlayer.filter(game=game).all()
        
        # Create GameState
        game_state = GameState(
            id=str(game.id),
            chat_id=chat_id,
            status=game.status,
            mode=game.mode,
            current_day=game.current_day or 1,
            created_at=game.created_at.isoformat(),
            started_at=game.started_at.isoformat() if game.started_at else None,
        )
        
        # Save to Redis
        from utils.redis_game.repositories import game_repo
        await game_repo.save_game(game_state)
        
        # Migrate players
        for player in players:
            player_state = PlayerState(
                game_id=str(game.id),
                user_id=player.user_id,
                username=player.user.username or "",
                first_name=player.user.first_name or "",
                role=player.role or "Villager",
                is_alive=player.is_alive,
                team=getattr(player, 'team', None),
                is_protected=False
            )
            from utils.redis_game.repositories import player_repo
            await player_repo.save_player(player_state)
        
        return True
        
    except Exception as e:
        print(f"Error migrating game to Redis: {e}")
        return False


async def validate_redis_game_state(game_id: str) -> dict:
    """
    Validate Redis game state integrity.
    Returns dict with validation results.
    
    Args:
        game_id: Game ID to validate
        
    Returns:
        Dict with validation status and errors
    """
    from utils.redis_game.repositories import game_repo, player_repo
    
    errors = []
    warnings = []
    
    # Check game exists
    game = await game_repo.load_game(game_id)
    if not game:
        errors.append(f"Game {game_id} not found in Redis")
        return {"valid": False, "errors": errors, "warnings": warnings}
    
    # Check players
    players = await player_repo.get_all_players(game_id)
    if not players:
        warnings.append("No players found in game")
    
    # Check alive vs dead count
    alive = [p for p in players if p.is_alive]
    dead = [p for p in players if not p.is_alive]
    
    if game.status == "started" and len(alive) == 0:
        errors.append("Started game has no alive players")
    
    # Check role assignments
    if game.status == "started":
        for player in players:
            if not player.role or player.role == "":
                warnings.append(f"Player {player.user_id} has no role assigned")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "total_players": len(players),
            "alive_players": len(alive),
            "dead_players": len(dead),
            "status": game.status,
            "day": game.current_day
        }
    }


def get_implementation_name() -> str:
    """Get current implementation name for logging."""
    if config.REDIS_GAME_ENABLED:
        return "Redis"
    return "Legacy PostgreSQL"
