"""
Phase Service - O'yin fazalari (night/day) boshqaruvi.
"""
from typing import Optional
from datetime import datetime, timezone

from utils.redis_game.game_models_schema import GamePhaseState
from utils.redis_game.game_models_crud import game_repo
from utils.redis_game.repositories import game_repository
from utils.database import redis_client as r


class PhaseService:
    """Phase management - kecha/kunduz o'tishlarini boshqarish."""
    
    @staticmethod
    async def create_phase(
        game_id: int,
        phase_num: int,
        phase_type: str
    ) -> Optional[GamePhaseState]:
        """
        Yangi phase yaratish.
        
        Args:
            game_id: O'yin ID
            phase_num: Phase raqami (1, 2, 3...)
            phase_type: Phase turi (night/day/morning/afternoon)
        
        Returns:
            GamePhaseState yoki None
        """
        phase = GamePhaseState(
            game_id=game_id,
            phase_num=phase_num,
            phase_type=phase_type,
            started_at=datetime.now(timezone.utc),
            is_end=False
        )
        
        await game_repo.save_phase(phase, ttl_sec=86400)
        
        # Current phase ni yangilash
        await r.set(f"game:{game_id}:current_phase", str(phase_num))
        
        return phase
    
    @staticmethod
    async def get_current_phase(game_id: int) -> Optional[GamePhaseState]:
        """
        Joriy phase ni olish.
        
        Returns:
            GamePhaseState yoki None
        """
        phase_num_str = await r.get(f"game:{game_id}:current_phase")
        
        if not phase_num_str:
            return None
        
        phase_num = int(phase_num_str)
        return await game_repo.load_phase(game_id, phase_num)
    
    @staticmethod
    async def get_phase(game_id: int, phase_num: int) -> Optional[GamePhaseState]:
        """Ma'lum phase ni olish."""
        return await game_repo.load_phase(game_id, phase_num)
    
    @staticmethod
    async def end_phase(game_id: int, phase_num: int) -> bool:
        """
        Phase ni yakunlash.
        
        Returns:
            True - muvaffaqiyatli
            False - xatolik
        """
        return await game_repo.update_phase_field(game_id, phase_num, "is_end", True)
    
    @staticmethod
    async def get_phase_number(game_id: int) -> int:
        """
        Joriy phase raqamini olish.
        
        Returns:
            Phase raqami (0 agar mavjud bo'lmasa)
        """
        phase_num_str = await r.get(f"game:{game_id}:current_phase")
        return int(phase_num_str) if phase_num_str else 0
    
    @staticmethod
    async def transition_to_night(game_id: int) -> Optional[GamePhaseState]:
        """
        Kechaga o'tish.
        
        Returns:
            Yangi night phase yoki None
        """
        # Joriy phase ni yakunlash
        current_phase = await PhaseService.get_current_phase(game_id)
        if current_phase:
            await PhaseService.end_phase(game_id, current_phase.phase_num)
        
        # Yangi phase raqami
        next_phase_num = await PhaseService.get_phase_number(game_id) + 1
        
        # Night phase yaratish
        night_phase = await PhaseService.create_phase(
            game_id,
            next_phase_num,
            "night"
        )
        
        # Game state ni yangilash
        await game_repository.update_game_field(game_id, "phase", "night")
        
        return night_phase
    
    @staticmethod
    async def transition_to_day(game_id: int) -> Optional[GamePhaseState]:
        """
        Kunduzga o'tish.
        
        Returns:
            Yangi day phase yoki None
        """
        # Joriy phase ni yakunlash
        current_phase = await PhaseService.get_current_phase(game_id)
        if current_phase:
            await PhaseService.end_phase(game_id, current_phase.phase_num)
        
        # Yangi phase raqami
        next_phase_num = await PhaseService.get_phase_number(game_id) + 1
        
        # Day phase yaratish
        day_phase = await PhaseService.create_phase(
            game_id,
            next_phase_num,
            "day"
        )
        
        # Game state ni yangilash
        await game_repository.update_game_field(game_id, "phase", "day")
        
        return day_phase
    
    @staticmethod
    async def transition_to_morning(game_id: int) -> Optional[GamePhaseState]:
        """
        Ertalabga o'tish (night natijalarini ko'rsatish).
        
        Returns:
            Morning phase yoki None
        """
        current_phase = await PhaseService.get_current_phase(game_id)
        if current_phase:
            await PhaseService.end_phase(game_id, current_phase.phase_num)
        
        next_phase_num = await PhaseService.get_phase_number(game_id) + 1
        
        morning_phase = await PhaseService.create_phase(
            game_id,
            next_phase_num,
            "morning"
        )
        
        await game_repository.update_game_field(game_id, "phase", "morning")
        
        return morning_phase
    
    @staticmethod
    async def transition_to_afternoon(game_id: int) -> Optional[GamePhaseState]:
        """
        Peshindan keyin o'tish (vote natijalarini ko'rsatish).
        
        Returns:
            Afternoon phase yoki None
        """
        current_phase = await PhaseService.get_current_phase(game_id)
        if current_phase:
            await PhaseService.end_phase(game_id, current_phase.phase_num)
        
        next_phase_num = await PhaseService.get_phase_number(game_id) + 1
        
        afternoon_phase = await PhaseService.create_phase(
            game_id,
            next_phase_num,
            "afternoon"
        )
        
        await game_repository.update_game_field(game_id, "phase", "afternoon")
        
        return afternoon_phase
    
    @staticmethod
    async def get_all_phases(game_id: int) -> list[GamePhaseState]:
        """
        O'yinning barcha phase larini olish.
        
        Returns:
            Phase'lar ro'yxati
        """
        phases = []
        phase_num = 1
        
        while True:
            phase = await game_repo.load_phase(game_id, phase_num)
            if not phase:
                break
            phases.append(phase)
            phase_num += 1
        
        return phases
    
    @staticmethod
    async def get_phases_count(game_id: int) -> int:
        """O'yindagi phase'lar sonini olish."""
        return await PhaseService.get_phase_number(game_id)


# Global instance
phase_service = PhaseService()
