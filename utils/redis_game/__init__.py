"""
Redis Game Package - O'yin jarayonlarini Redis bilan boshqarish.

Public API:
- game_service: O'yin lifecycle (yaratish, boshlash, tugatish)
- player_service: Player management (join, leave, statistics)
- phase_service: Phase management (night/day transitions)
- action_service: Action management (kill, heal, protect, investigate)
- vote_service: Vote management (day vote, mafia vote, vote likes)
- game_repository: Game Redis CRUD
- player_repository: Player Redis CRUD
- check_user_permission: Permission tekshirish
"""

# Services (business logic)
from .services import (
    game_service,
    player_service,
    phase_service,
    action_service,
    vote_service
)

# Repositories (data access)
from .repositories import game_repository, player_repository

# Utils
from .utils import check_user_permission
from .migration_utils import (
    should_use_redis,
    redis_migration,
    migrate_active_game_to_redis,
    validate_redis_game_state,
    get_implementation_name
)

# Handlers (Redis-based implementations)
from .handlers import (
    create_game_handler_redis,
    create_vs_game_handler_redis,
    join_game_handler_redis,
    kick_player_redis,
    leave_game_redis,
    stop_game_handler_redis,
    start_game_handler_redis,
    starting_game_redis,
    update_players_list_redis
)

# Legacy support (backward compatibility)
from .game_models_crud import game_repo
from . import game_models_schema, game_frame

__all__ = [
    # Services
    'game_service',
    'player_service',
    'phase_service',
    'action_service',
    'vote_service',
    
    # Repositories
    'game_repository',
    'player_repository',
    
    # Utils
    'check_user_permission',
    
    # Migration utilities
    'should_use_redis',
    'redis_migration',
    'migrate_active_game_to_redis',
    'validate_redis_game_state',
    'get_implementation_name',
    
    # Handlers
    'create_game_handler_redis',
    'create_vs_game_handler_redis',
    'join_game_handler_redis',
    'kick_player_redis',
    'leave_game_redis',
    'stop_game_handler_redis',
    'start_game_handler_redis',
    'starting_game_redis',
    'update_players_list_redis',
    
    # Legacy
    'game_repo',
    'game_models_schema',
    'game_frame',
]