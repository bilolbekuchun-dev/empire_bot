"""
Action Service - O'yin action'lari (kill, heal, protect, investigate).
"""
from typing import Optional, List
from datetime import datetime, timezone

from utils.redis_game.game_models_schema import ActionState
from utils.redis_game.game_models_crud import game_repo
from utils.redis_game.repositories import player_repository
from utils.database import redis_client as r


class ActionService:
    """Action management - tungi va kunduzi action'lar."""
    
    @staticmethod
    async def save_action(
        game_id: int,
        phase_id: int,
        actor_id: int,
        target_id: Optional[int],
        action_type: str
    ) -> ActionState:
        """
        Action saqlash.
        
        Args:
            game_id: O'yin ID
            phase_id: Phase ID
            actor_id: Harakat qiluvchi player ID
            target_id: Nishon player ID (None bo'lishi mumkin)
            action_type: Action turi (kill/heal/protect/investigate/etc.)
        
        Returns:
            ActionState
        """
        action = ActionState(
            game_id=game_id,
            phase_id=phase_id,
            actor_id=actor_id,
            target_id=target_id,
            action_type=action_type,
            created_at=datetime.now(timezone.utc)
        )
        
        await game_repo.save_action(action, ttl_sec=86400)
        
        # Action'ni set ga qo'shish (phase bo'yicha)
        action_key = f"{actor_id}:{target_id}:{action_type}"
        await r.sadd(f"game:{game_id}:phase:{phase_id}:action_keys", action_key)
        
        return action
    
    @staticmethod
    async def get_phase_actions(game_id: int, phase_id: int) -> List[dict]:
        """
        Phase ning barcha action'larini olish.
        
        Returns:
            [{'actor_id': int, 'target_id': int, 'action_type': str}, ...]
        """
        action_keys = await r.smembers(f"game:{game_id}:phase:{phase_id}:action_keys")
        
        actions = []
        for key_str in action_keys:
            parts = key_str.split(":")
            if len(parts) == 3:
                actor_id, target_id, action_type = parts
                actions.append({
                    'actor_id': int(actor_id),
                    'target_id': int(target_id) if target_id != "None" else None,
                    'action_type': action_type
                })
        
        return actions
    
    @staticmethod
    async def has_action(
        game_id: int,
        phase_id: int,
        actor_id: int
    ) -> bool:
        """Player action qilgan yoki yo'qligini tekshirish."""
        actions = await ActionService.get_phase_actions(game_id, phase_id)
        return any(a['actor_id'] == actor_id for a in actions)
    
    @staticmethod
    async def get_player_action(
        game_id: int,
        phase_id: int,
        actor_id: int
    ) -> Optional[dict]:
        """Ma'lum player ning action ini olish."""
        actions = await ActionService.get_phase_actions(game_id, phase_id)
        for action in actions:
            if action['actor_id'] == actor_id:
                return action
        return None
    
    @staticmethod
    async def get_actions_by_type(
        game_id: int,
        phase_id: int,
        action_type: str
    ) -> List[dict]:
        """Ma'lum turdagi barcha action'larni olish."""
        all_actions = await ActionService.get_phase_actions(game_id, phase_id)
        return [a for a in all_actions if a['action_type'] == action_type]
    
    @staticmethod
    async def get_target_actions(
        game_id: int,
        phase_id: int,
        target_id: int
    ) -> List[dict]:
        """Ma'lum player ga yo'naltirilgan barcha action'lar."""
        all_actions = await ActionService.get_phase_actions(game_id, phase_id)
        return [a for a in all_actions if a['target_id'] == target_id]
    
    @staticmethod
    async def apply_kill_action(game_id: int, target_id: int) -> bool:
        """
        Kill action ni amalga oshirish.
        
        Returns:
            True - player o'ldi
            False - himoyalangan yoki xato
        """
        return await player_repository.update_player_fields(
            game_id,
            target_id,
            is_alive=False,
            deaded_at=datetime.now(timezone.utc)
        )
    
    @staticmethod
    async def apply_heal_action(game_id: int, target_id: int) -> bool:
        """Heal action (player sog'lomlashtirish)."""
        # Life ni 100 ga qaytarish
        return await player_repository.update_player_field(
            game_id,
            target_id,
            "life",
            100
        )
    
    @staticmethod
    async def apply_protect_action(game_id: int, target_id: int) -> bool:
        """Protect action (keyingi turnda himoyalangan bo'ladi)."""
        # Bu protected flag'ni set qiladi
        return await player_repository.update_player_field(
            game_id,
            target_id,
            "is_protected",
            True
        )
    
    @staticmethod
    async def is_protected(game_id: int, target_id: int) -> bool:
        """Player himoyalangan yoki yo'qligini tekshirish."""
        player = await player_repository.load_player(game_id, target_id)
        return getattr(player, 'is_protected', False) if player else False
    
    @staticmethod
    async def clear_protections(game_id: int):
        """Barcha himoyalarni tozalash (turn oxirida)."""
        player_ids = await player_repository.get_player_ids(game_id)
        
        for player_id in player_ids:
            await player_repository.update_player_field(
                game_id,
                player_id,
                "is_protected",
                False
            )
    
    @staticmethod
    async def process_night_actions(game_id: int, phase_id: int) -> dict:
        """
        Tungi action'larni qayta ishlash.
        
        Returns:
            {
                'kills': [user_id, ...],
                'heals': [user_id, ...],
                'protects': [user_id, ...],
                'survived': [user_id, ...]
            }
        """
        kills = await ActionService.get_actions_by_type(game_id, phase_id, "kill")
        heals = await ActionService.get_actions_by_type(game_id, phase_id, "heal")
        protects = await ActionService.get_actions_by_type(game_id, phase_id, "protect")
        
        killed_ids = []
        healed_ids = []
        protected_ids = []
        survived_ids = []
        
        # Protect'larni birinchi qo'llash
        for protect in protects:
            if protect['target_id']:
                await ActionService.apply_protect_action(game_id, protect['target_id'])
                protected_ids.append(protect['target_id'])
        
        # Kill va heal'larni qayta ishlash
        for kill in kills:
            if kill['target_id']:
                target_id = kill['target_id']
                
                # Himoyalangan yoki heal qilingan yoki yo'q
                is_healed = any(h['target_id'] == target_id for h in heals)
                is_protected = await ActionService.is_protected(game_id, target_id)
                
                if not is_healed and not is_protected:
                    await ActionService.apply_kill_action(game_id, target_id)
                    killed_ids.append(target_id)
                else:
                    survived_ids.append(target_id)
                    if is_healed:
                        healed_ids.append(target_id)
        
        return {
            'kills': killed_ids,
            'heals': healed_ids,
            'protects': protected_ids,
            'survived': survived_ids
        }


# Global instance
action_service = ActionService()
