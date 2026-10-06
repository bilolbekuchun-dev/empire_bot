"""
Vote Service - Ovoz berish tizimi (day vote, mafia vote, vote likes).
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import Counter

from utils.redis_game.game_models_schema import VoteState, VoteLikeState
from utils.redis_game.game_models_crud import game_repo
from utils.database import redis_client as r


class VoteService:
    """Vote management - ovoz berish tizimi."""
    
    @staticmethod
    async def save_vote(
        game_id: int,
        phase_id: int,
        voter_id: int,
        target_id: int
    ) -> bool:
        """
        Ovoz berish.
        
        Returns:
            True - muvaffaqiyatli
            False - xatolik
        """
        # Vote hash da saqlash: voter_id -> target_id
        await r.hset(
            f"game:{game_id}:phase:{phase_id}:votes",
            str(voter_id),
            str(target_id)
        )
        
        return True
    
    @staticmethod
    async def get_vote(
        game_id: int,
        phase_id: int,
        voter_id: int
    ) -> Optional[int]:
        """Ma'lum player ning ovozini olish."""
        target_str = await r.hget(
            f"game:{game_id}:phase:{phase_id}:votes",
            str(voter_id)
        )
        
        return int(target_str) if target_str else None
    
    @staticmethod
    async def get_all_votes(
        game_id: int,
        phase_id: int
    ) -> Dict[int, int]:
        """
        Barcha ovozlarni olish.
        
        Returns:
            {voter_id: target_id, ...}
        """
        votes = await r.hgetall(f"game:{game_id}:phase:{phase_id}:votes")
        
        return {
            int(voter_id): int(target_id)
            for voter_id, target_id in votes.items()
        }
    
    @staticmethod
    async def get_vote_results(
        game_id: int,
        phase_id: int
    ) -> List[Tuple[int, int]]:
        """
        Ovoz natijalarini olish (tartiblangan).
        
        Returns:
            [(target_id, vote_count), ...] - ko'p ovoz olganlar birinchi
        """
        votes = await VoteService.get_all_votes(game_id, phase_id)
        
        # Vote count
        vote_counts = Counter(votes.values())
        
        # Tartiblash (ko'pdan kamga)
        sorted_results = sorted(
            vote_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_results
    
    @staticmethod
    async def get_winner(
        game_id: int,
        phase_id: int
    ) -> Optional[int]:
        """
        Eng ko'p ovoz olgan player ID ni qaytarish.
        
        Returns:
            target_id yoki None (agar ikkita barobar bo'lsa)
        """
        results = await VoteService.get_vote_results(game_id, phase_id)
        
        if not results:
            return None
        
        # Birinchi va ikkinchi
        if len(results) == 1:
            return results[0][0]
        
        # Agar birinchi va ikkinchi barobar bo'lsa
        if results[0][1] == results[1][1]:
            return None  # Draw
        
        return results[0][0]
    
    @staticmethod
    async def get_votes_count(game_id: int, phase_id: int) -> int:
        """Ovoz berganlar sonini olish."""
        votes = await VoteService.get_all_votes(game_id, phase_id)
        return len(votes)
    
    @staticmethod
    async def has_voted(
        game_id: int,
        phase_id: int,
        voter_id: int
    ) -> bool:
        """Player ovoz bergan yoki yo'qligini tekshirish."""
        return await r.hexists(
            f"game:{game_id}:phase:{phase_id}:votes",
            str(voter_id)
        )
    
    @staticmethod
    async def clear_votes(game_id: int, phase_id: int):
        """Barcha ovozlarni tozalash."""
        await r.delete(f"game:{game_id}:phase:{phase_id}:votes")
    
    # ============ VOTE LIKES ============
    
    @staticmethod
    async def save_vote_like(
        game_id: int,
        phase_id: int,
        voter_id: int,
        target_id: int,
        is_like: bool
    ) -> bool:
        """
        Vote like/dislike saqlash.
        
        Args:
            is_like: True - like, False - dislike
        """
        # Hash: liker_id -> "target_id:is_like"
        value = f"{target_id}:{'1' if is_like else '0'}"
        await r.hset(
            f"game:{game_id}:phase:{phase_id}:vote_likes",
            str(voter_id),
            value
        )
        
        return True
    
    @staticmethod
    async def get_vote_like(
        game_id: int,
        phase_id: int,
        voter_id: int
    ) -> Optional[Tuple[int, bool]]:
        """
        Ma'lum player ning vote like ni olish.
        
        Returns:
            (target_id, is_like) yoki None
        """
        value = await r.hget(
            f"game:{game_id}:phase:{phase_id}:vote_likes",
            str(voter_id)
        )
        
        if not value:
            return None
        
        parts = value.split(":")
        if len(parts) == 2:
            target_id = int(parts[0])
            is_like = parts[1] == '1'
            return (target_id, is_like)
        
        return None
    
    @staticmethod
    async def get_all_vote_likes(
        game_id: int,
        phase_id: int
    ) -> Dict[int, Tuple[int, bool]]:
        """
        Barcha vote like'larni olish.
        
        Returns:
            {voter_id: (target_id, is_like), ...}
        """
        likes = await r.hgetall(f"game:{game_id}:phase:{phase_id}:vote_likes")
        
        result = {}
        for voter_id, value in likes.items():
            parts = value.split(":")
            if len(parts) == 2:
                target_id = int(parts[0])
                is_like = parts[1] == '1'
                result[int(voter_id)] = (target_id, is_like)
        
        return result
    
    @staticmethod
    async def get_vote_like_results(
        game_id: int,
        phase_id: int,
        target_id: int
    ) -> Dict[str, int]:
        """
        Ma'lum target uchun like/dislike statistikasi.
        
        Returns:
            {'likes': int, 'dislikes': int}
        """
        all_likes = await VoteService.get_all_vote_likes(game_id, phase_id)
        
        likes = 0
        dislikes = 0
        
        for tid, is_like in all_likes.values():
            if tid == target_id:
                if is_like:
                    likes += 1
                else:
                    dislikes += 1
        
        return {'likes': likes, 'dislikes': dislikes}
    
    @staticmethod
    async def should_execute(
        game_id: int,
        phase_id: int,
        target_id: int,
        threshold: float = 0.5
    ) -> bool:
        """
        Player osilishi kerakmi yoki yo'qligini aniqlash (like/dislike asosida).
        
        Args:
            threshold: Minimal like foizi (default 0.5 = 50%)
        
        Returns:
            True - osilishi kerak
            False - qutuldi
        """
        results = await VoteService.get_vote_like_results(game_id, phase_id, target_id)
        
        total = results['likes'] + results['dislikes']
        if total == 0:
            return False
        
        like_ratio = results['likes'] / total
        return like_ratio >= threshold
    
    @staticmethod
    async def clear_vote_likes(game_id: int, phase_id: int):
        """Barcha vote like'larni tozalash."""
        await r.delete(f"game:{game_id}:phase:{phase_id}:vote_likes")


# Global instance
vote_service = VoteService()
