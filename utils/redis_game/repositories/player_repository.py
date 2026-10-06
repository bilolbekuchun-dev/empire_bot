"""
Player Repository - Redis da player bilan bog'liq operatsiyalar.
"""
from typing import Optional, List
from datetime import datetime
from utils.redis_game.game_models_schema import PlayerState
from utils.redis_game.game_models_crud import game_repo
from utils.database import redis_client as r


class PlayerRepository:
    """Player bilan bog'liq barcha Redis operatsiyalari."""
    
    @staticmethod
    async def save_player(player: PlayerState, ttl_sec: Optional[int] = None):
        """Player state ni saqlash."""
        await game_repo.save_player(player, ttl_sec)
    
    @staticmethod
    async def load_player(game_id: int, user_id: int) -> Optional[PlayerState]:
        """Player state ni yuklash."""
        return await game_repo.load_player(game_id, user_id)
    
    @staticmethod
    async def delete_player(game_id: int, user_id: int):
        """Player ni o'chirish."""
        await game_repo.delete_player(game_id, user_id)
    
    @staticmethod
    async def player_exists(game_id: int, user_id: int) -> bool:
        """Player mavjudligini tekshirish."""
        return await game_repo.player_exists(game_id, user_id)
    
    @staticmethod
    async def update_player_field(game_id: int, user_id: int, field: str, value) -> bool:
        """Player ning bitta fieldini yangilash."""
        return await game_repo.update_player_field(game_id, user_id, field, value)
    
    @staticmethod
    async def update_player_fields(game_id: int, user_id: int, **fields) -> bool:
        """Player ning bir nechta fieldlarini yangilash."""
        return await game_repo.update_player_fields(game_id, user_id, **fields)
    
    @staticmethod
    async def add_player_to_set(game_id: int, user_id: int):
        """Player ni game players set ga qo'shish."""
        await r.sadd(f"game:{game_id}:players", str(user_id))
    
    @staticmethod
    async def remove_player_from_set(game_id: int, user_id: int):
        """Player ni game players set dan olib tashlash."""
        await r.srem(f"game:{game_id}:players", str(user_id))
    
    @staticmethod
    async def get_player_ids(game_id: int) -> List[int]:
        """O'yindagi barcha player ID larini olish."""
        player_ids_str = await r.smembers(f"game:{game_id}:players")
        return [int(pid) for pid in player_ids_str]
    
    @staticmethod
    async def get_players_count(game_id: int) -> int:
        """O'yindagi playerlar sonini olish."""
        return await r.scard(f"game:{game_id}:players")
    
    @staticmethod
    async def get_all_players(game_id: int) -> List[PlayerState]:
        """O'yindagi barcha playerlarni olish."""
        player_ids = await PlayerRepository.get_player_ids(game_id)
        
        players = []
        for player_id in player_ids:
            player = await game_repo.load_player(game_id, player_id)
            if player:
                players.append(player)
        
        return players
    
    @staticmethod
    async def get_alive_players(game_id: int) -> List[PlayerState]:
        """O'yindagi tirik playerlarni olish."""
        all_players = await PlayerRepository.get_all_players(game_id)
        return [p for p in all_players if p.is_alive]
    
    @staticmethod
    async def get_dead_players(game_id: int) -> List[PlayerState]:
        """O'yindagi o'lgan playerlarni olish."""
        all_players = await PlayerRepository.get_all_players(game_id)
        return [p for p in all_players if not p.is_alive]
    
    @staticmethod
    async def set_ball(game_id: int, user_id: int, ball: int):
        """Player uchun ball saqlash."""
        await r.set(f"game:{game_id}:player:{user_id}:ball", str(ball))
    
    @staticmethod
    async def get_ball(game_id: int, user_id: int) -> int:
        """Player ning ball ini olish."""
        ball = await r.get(f"game:{game_id}:player:{user_id}:ball")
        return int(ball) if ball else 0
    
    @staticmethod
    async def increment_ball(game_id: int, user_id: int, amount: int = 1):
        """Player ball ini oshirish."""
        await r.incrby(f"game:{game_id}:player:{user_id}:ball", amount)
    
    @staticmethod
    async def delete_ball(game_id: int, user_id: int):
        """Player ball ma'lumotini o'chirish."""
        await r.delete(f"game:{game_id}:player:{user_id}:ball")


# Global instance
player_repository = PlayerRepository()
