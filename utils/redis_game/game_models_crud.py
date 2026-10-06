from typing import TypeVar, Generic, Type, Optional, Any
from pydantic import BaseModel
from utils.redis_game.game_models_schema import (
    GameState, 
    PlayerState, 
    GamePhaseState, 
    VoteLikeState, 
    VoteState,
    ActionState,
    GeroyActionState,
    PlayerGameBallState 
)
from utils.database import redis_client as r

T = TypeVar('T', bound=BaseModel)


class RedisStateManager(Generic[T]):
    """
    Generic Redis state manager - barcha state turlari uchun umumiy CRUD operatsiyalari.
    """
    
    def __init__(self, model_class: Type[T]):
        self.model_class = model_class
    
    async def save(self, state: T, ttl_sec: Optional[int] = None) -> None:
        """State ni Redis ga saqlash."""
        await r.set(state.key, state.model_dump_json())
        if ttl_sec:
            await r.expire(state.key, ttl_sec)
    
    async def load(self, key: str) -> Optional[T]:
        """State ni Redis dan yuklash."""
        data = await r.get(key)
        if not data:
            return None
        return self.model_class.model_validate_json(data)
    
    async def delete(self, key: str) -> None:
        """State ni Redis dan o'chirish."""
        await r.delete(key)
    
    async def exists(self, key: str) -> bool:
        """State mavjudligini tekshirish."""
        return await r.exists(key) == 1
    
    async def update_field(self, key: str, field: str, value: Any) -> bool:
        """State ning bitta field ini yangilash. True qaytarsa muvaffaqiyatli."""
        state = await self.load(key)
        if not state:
            return False
        setattr(state, field, value)
        await self.save(state)
        return True
    
    async def update_fields(self, key: str, **fields) -> bool:
        """State ning bir nechta field larini yangilash."""
        state = await self.load(key)
        if not state:
            return False
        for field, value in fields.items():
            setattr(state, field, value)
        await self.save(state)
        return True


class GameStateRepository:
    """Barcha game state operatsiyalarini bir joyda yig'ish."""
    
    def __init__(self):
        self._game = RedisStateManager[GameState](GameState)
        self._player = RedisStateManager[PlayerState](PlayerState)
        self._phase = RedisStateManager[GamePhaseState](GamePhaseState)
        self._vote = RedisStateManager[VoteState](VoteState)
        self._vote_like = RedisStateManager[VoteLikeState](VoteLikeState)
        self._action = RedisStateManager[ActionState](ActionState)
        self._geroy_action = RedisStateManager[GeroyActionState](GeroyActionState)
        player_game_ball_state = RedisStateManager[PlayerState](PlayerState)

    # ============ GAME STATE ============
    async def save_game(self, state: GameState, ttl_sec: Optional[int] = None) -> None:
        await self._game.save(state, ttl_sec)
    
    async def load_game(self, game_id: int) -> Optional[GameState]:
        return await self._game.load(f"game:{game_id}:state")
    
    async def delete_game(self, game_id: int) -> None:
        await self._game.delete(f"game:{game_id}:state")
    
    async def game_exists(self, game_id: int) -> bool:
        return await self._game.exists(f"game:{game_id}:state")
    
    async def update_game_field(self, game_id: int, field: str, value: Any) -> bool:
        return await self._game.update_field(f"game:{game_id}:state", field, value)
    
    async def update_game_fields(self, game_id: int, **fields) -> bool:
        return await self._game.update_fields(f"game:{game_id}:state", **fields)
    
    # ============ PLAYER STATE ============
    async def save_player(self, state: PlayerState, ttl_sec: Optional[int] = None) -> None:
        await self._player.save(state, ttl_sec)
    
    async def load_player(self, game_id: int, user_id: int) -> Optional[PlayerState]:
        return await self._player.load(f"game:{game_id}:player:{user_id}")
    
    async def delete_player(self, game_id: int, user_id: int) -> None:
        await self._player.delete(f"game:{game_id}:player:{user_id}")
    
    async def player_exists(self, game_id: int, user_id: int) -> bool:
        return await self._player.exists(f"game:{game_id}:player:{user_id}")
    
    async def update_player_field(self, game_id: int, user_id: int, field: str, value: Any) -> bool:
        return await self._player.update_field(f"game:{game_id}:player:{user_id}", field, value)
    
    async def update_player_fields(self, game_id: int, user_id: int, **fields) -> bool:
        return await self._player.update_fields(f"game:{game_id}:player:{user_id}", **fields)
    
    # ============ PHASE STATE ============
    async def save_phase(self, state: GamePhaseState, ttl_sec: Optional[int] = None) -> None:
        await self._phase.save(state, ttl_sec)
    
    async def load_phase(self, game_id: int, phase_num: int) -> Optional[GamePhaseState]:
        return await self._phase.load(f"game:{game_id}:phase:{phase_num}")
    
    async def delete_phase(self, game_id: int, phase_num: int) -> None:
        await self._phase.delete(f"game:{game_id}:phase:{phase_num}")
    
    async def phase_exists(self, game_id: int, phase_num: int) -> bool:
        return await self._phase.exists(f"game:{game_id}:phase:{phase_num}")
    
    async def update_phase_field(self, game_id: int, phase_num: int, field: str, value: Any) -> bool:
        return await self._phase.update_field(f"game:{game_id}:phase:{phase_num}", field, value)
    
    async def update_phase_fields(self, game_id: int, phase_num: int, **fields) -> bool:
        return await self._phase.update_fields(f"game:{game_id}:phase:{phase_num}", **fields)
    
    # ============ VOTE STATE ============
    async def save_vote(self, state: VoteState, ttl_sec: Optional[int] = None) -> None:
        await self._vote.save(state, ttl_sec)
    
    async def load_vote(self, game_id: int, phase_id: int) -> Optional[VoteState]:
        return await self._vote.load(f"game:{game_id}:votes:{phase_id}")
    
    async def delete_vote(self, game_id: int, phase_id: int) -> None:
        await self._vote.delete(f"game:{game_id}:votes:{phase_id}")
    
    # ============ VOTE LIKE STATE ============
    async def save_vote_like(self, state: VoteLikeState, ttl_sec: Optional[int] = None) -> None:
        await self._vote_like.save(state, ttl_sec)
    
    async def load_vote_like(self, game_id: int, phase_id: int) -> Optional[VoteLikeState]:
        return await self._vote_like.load(f"game:{game_id}:vote_likes:{phase_id}")
    
    async def delete_vote_like(self, game_id: int, phase_id: int) -> None:
        await self._vote_like.delete(f"game:{game_id}:vote_likes:{phase_id}")
    
    # ============ ACTION STATE ============
    async def save_action(self, state: ActionState, ttl_sec: Optional[int] = None) -> None:
        await self._action.save(state, ttl_sec)
    
    async def load_action(self, game_id: int, phase_id: int) -> Optional[ActionState]:
        return await self._action.load(f"game:{game_id}:phase:{phase_id}:actions")
    
    async def delete_action(self, game_id: int, phase_id: int) -> None:
        await self._action.delete(f"game:{game_id}:phase:{phase_id}:actions")
    
    async def action_exists(self, game_id: int, phase_id: int) -> bool:
        return await self._action.exists(f"game:{game_id}:phase:{phase_id}:actions")

    async def update_action_field(self, game_id: int, phase_id: int, field: str, value: Any) -> bool:
        return await self._action.update_field(f"game:{game_id}:phase:{phase_id}:actions", field, value)

    # ============ GEROY ACTION STATE ============
    async def save_geroy_action(self, state: GeroyActionState, ttl_sec: Optional[int] = None) -> None:
        await self._geroy_action.save(state, ttl_sec)
    
    async def load_geroy_action(self, game_id: int, phase_id: int) -> Optional[GeroyActionState]:
        return await self._geroy_action.load(f"game:{game_id}:phase:{phase_id}:geroy_actions")
    
    async def delete_geroy_action(self, game_id: int, phase_id: int) -> None:
        await self._geroy_action.delete(f"game:{game_id}:phase:{phase_id}:geroy_actions")

    # ============ PLAYER GAME BALL STATE ============
    async def save_player_game_ball(self, state: PlayerGameBallState, ttl_sec: Optional[int] = None) -> None:
        await self._player_game_ball.save(state, ttl_sec)

    async def load_player_game_ball(self, game_id: int, player_id: int) -> Optional[PlayerGameBallState]:
        return await self._player_game_ball.load(f"game:{game_id}:player:{player_id}:game_ball")

    async def delete_player_game_ball(self, game_id: int, player_id: int) -> None:
        await self._player_game_ball.delete(f"game:{game_id}:player:{player_id}:game_ball")

    async def player_game_ball_exists(self, game_id: int, player_id: int) -> bool:
        return await self._player_game_ball.exists(f"game:{game_id}:player:{player_id}:game_ball")
    
    async def update_player_game_ball_field(self, game_id: int, player_id: int, field: str, value: Any) -> bool:
        return await self._player_game_ball.update_field(f"game:{game_id}:player:{player_id}:game_ball", field, value)
    
game_repo = GameStateRepository()