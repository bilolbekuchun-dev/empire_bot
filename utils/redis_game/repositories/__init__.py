"""
Repositories __init__ - export qilish uchun.
"""
from .game_repository import game_repository, GameRepository
from .player_repository import player_repository, PlayerRepository

__all__ = [
    'game_repository',
    'GameRepository',
    'player_repository', 
    'PlayerRepository',
]
