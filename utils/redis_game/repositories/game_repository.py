"""
Game Repository - Redis da game bilan bog'liq operatsiyalar.
"""
from typing import Optional
from utils.redis_game.game_models_schema import GameState
from utils.redis_game.game_models_crud import game_repo
from utils.database import redis_client as r


class GameRepository:
    """Game bilan bog'liq barcha Redis operatsiyalari."""
    
    @staticmethod
    async def generate_id() -> int:
        """Yangi unique game ID yaratish."""
        return await r.incr("game:id_counter")
    
    @staticmethod
    async def get_active_game(chat_id: int) -> Optional[int]:
        """Chat da aktiv o'yin ID sini topish. Returns game_id yoki None."""
        game_ids_str = await r.smembers(f"chat:{chat_id}:active_games")
        
        if not game_ids_str:
            return None
        
        for game_id_str in game_ids_str:
            game_id = int(game_id_str)
            game = await game_repo.load_game(game_id)
            if game and game.is_active:
                return game_id  # Return ID, not GameState
        
        return None
    
    @staticmethod
    async def add_active_game(chat_id: int, game_id: int):
        """Chat ga active game qo'shish."""
        await r.sadd(f"chat:{chat_id}:active_games", str(game_id))
    
    @staticmethod
    async def remove_active_game(chat_id: int, game_id: int):
        """Chat dan active game olib tashlash."""
        await r.srem(f"chat:{chat_id}:active_games", str(game_id))
    
    @staticmethod
    async def save_game(game: GameState, ttl_sec: Optional[int] = None):
        """Game state ni saqlash."""
        await game_repo.save_game(game, ttl_sec)
    
    @staticmethod
    async def load_game(game_id: int) -> Optional[GameState]:
        """Game state ni yuklash."""
        return await game_repo.load_game(game_id)
    
    @staticmethod
    async def update_game_field(game_id: int, field: str, value) -> bool:
        """Game ning bitta fieldini yangilash."""
        return await game_repo.update_game_field(game_id, field, value)
    
    @staticmethod
    async def update_game_fields(game_id: int, **fields) -> bool:
        """Game ning bir nechta fieldlarini yangilash."""
        return await game_repo.update_game_fields(game_id, **fields)
    
    @staticmethod
    async def delete_game(game_id: int):
        """Game ni o'chirish."""
        await game_repo.delete_game(game_id)
    
    @staticmethod
    async def game_exists(game_id: int) -> bool:
        """Game mavjudligini tekshirish."""
        return await game_repo.game_exists(game_id)
    
    @staticmethod
    async def cleanup_game_data(game_id: int):
        """
        Game bilan bog'liq barcha ma'lumotlarni Redis dan tozalash.
        Pattern scan qilib barcha key'larni topadi va o'chiradi.
        """
        keys_to_delete = []
        cursor = 0
        pattern = f"game:{game_id}:*"
        
        while True:
            cursor, keys = await r.scan(cursor, match=pattern, count=100)
            keys_to_delete.extend(keys)
            if cursor == 0:
                break
        
        if keys_to_delete:
            await r.delete(*keys_to_delete)


# Global instance
game_repository = GameRepository()
