"""
Player Service - Player management (join, leave, statistics).
"""
from typing import Optional
from datetime import datetime, timezone

from utils.redis_game.game_models_schema import PlayerState
from utils.redis_game.repositories import game_repository, player_repository
from models.user import User, Profile


class PlayerService:
    """Player management service."""
    
    @staticmethod
    async def join_game(
        game_id: int,
        user_id: int,
        team: Optional[str] = None
    ) -> bool:
        """
        O'yinga player qo'shish.
        
        Returns:
            True - muvaffaqiyatli
            False - xatolik
        """
        # O'yin mavjudligi va waiting fazada ekanligini tekshirish
        game = await game_repository.load_game(game_id)
        if not game or game.phase != "waiting":
            return False
        
        # Player allaqachon qo'shilgan yoki yo'q
        if await player_repository.player_exists(game_id, user_id):
            return False
        
        # Player yaratish
        player_state = PlayerState(
            game_id=game_id,
            user_id=user_id,
            role="",  # Start vaqtida beriladi
            team=team,
            is_alive=True,
            is_sleep=False,
            life=100,
            joined_at=datetime.now(timezone.utc)
        )
        
        # Redis ga saqlash
        await player_repository.save_player(player_state, ttl_sec=86400)
        await player_repository.add_player_to_set(game_id, user_id)
        
        return True
    
    @staticmethod
    async def leave_game(game_id: int, user_id: int) -> bool:
        """
        O'yindan chiqish.
        
        Returns:
            True - muvaffaqiyatli
            False - xatolik
        """
        # Player mavjudligini tekshirish
        if not await player_repository.player_exists(game_id, user_id):
            return False
        
        # O'yin boshlangan bo'lsa chiqib bo'lmaydi
        game = await game_repository.load_game(game_id)
        if not game or game.phase != "waiting":
            return False
        
        # Redis dan o'chirish
        await player_repository.delete_player(game_id, user_id)
        await player_repository.remove_player_from_set(game_id, user_id)
        
        return True
    
    @staticmethod
    async def get_player(game_id: int, user_id: int) -> Optional[PlayerState]:
        """Player ma'lumotlarini olish."""
        return await player_repository.load_player(game_id, user_id)
    
    @staticmethod
    async def find_player_active_game(user_id: int) -> Optional[tuple[int, PlayerState]]:
        """
        User ning faol o'yinini topish (faqat amaldagi va tugamagan o'yinlar).
        """
        from utils.database import redis_client
        from utils.redis_game.repositories.game_repository import game_repository
        
        active_game_ids = await redis_client.smembers("global:active_games")
        
        if not active_game_ids:
            return None
        
        for game_id_str in active_game_ids:
            if isinstance(game_id_str, bytes):
                game_id_str = game_id_str.decode()
            try:
                game_id = int(game_id_str)
            except (TypeError, ValueError):
                continue
            
            game_state = await game_repository.load_game(game_id)
            if not game_state or not game_state.is_active or game_state.phase in ("end", "ended", "finished"):
                await redis_client.srem("global:active_games", game_id_str)
                continue

            player = await player_repository.load_player(game_id, user_id)
            if player and player.is_alive:
                return (game_id, player)
        
        return None

    @staticmethod
    async def find_player_dead_last_word_game(user_id: int) -> Optional[tuple[int, PlayerState]]:
        """
        User o'lgan va hali oxirgi so'zini aytmagan faol Redis o'yinini topish.
        """
        from utils.database import redis_client
        from datetime import datetime, timezone
        from utils.redis_game.game_models_crud import game_repo
        
        active_game_ids = await redis_client.smembers("global:active_games")
        if not active_game_ids:
            return None

        for game_id_str in active_game_ids:
            if isinstance(game_id_str, bytes):
                game_id_str = game_id_str.decode()
            try:
                game_id = int(game_id_str)
            except (TypeError, ValueError):
                continue
            player = await player_repository.load_player(game_id, user_id)
            if player and not player.is_alive and not player.is_sayed_last_word:
                game_state = await game_repo.load_game(game_id)
                if game_state and game_state.is_active:
                    return (game_id, player)

        return None
    
    @staticmethod
    async def get_game_statistics(game_id: int) -> dict:
        """
        O'yin statistikasini olish.
        
        Returns:
            {
                'total_players': int,
                'alive_players': int,
                'dead_players': int,
                'players': List[PlayerState]
            }
        """
        players = await player_repository.get_all_players(game_id)
        alive = await player_repository.get_alive_players(game_id)
        dead = await player_repository.get_dead_players(game_id)
        
        return {
            'total_players': len(players),
            'alive_players': len(alive),
            'dead_players': len(dead),
            'players': players
        }
    
    @staticmethod
    async def update_player_profile(
        user_id: int,
        is_winner: bool,
        is_member: bool = True,
        ball: int = 0
    ):
        """
        O'yin tugagandan keyin player profileini yangilash.
        
        Args:
            user_id: User ID
            is_winner: G'olib bo'lsa True
            is_member: Guruh a'zosi bo'lsa True
            ball: Qo'shimcha ball
        """
        user = await User.filter(user_id=user_id).first()
        if not user:
            return
        
        profile, _ = await Profile.get_or_create(
            user=user,
            defaults={
                "dollar": 0,
                "diamond": 0,
                "himoya": 0,
                "qotildan_himoya": 0,
                "osishdan_himoya": 0,
                "miltiq": 0,
                "wins": 0,
                "games_count": 0
            }
        )
        
        # Dollar qo'shish
        if is_winner:
            profile.dollar += 20 if is_member else 10
            profile.wins += 1
        else:
            profile.dollar += 5 if is_member else 0
        
        profile.games_count += 1
        await profile.save()
        
        return profile


# Global instance
player_service = PlayerService()
