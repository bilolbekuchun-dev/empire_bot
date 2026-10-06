from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime

class GameState(BaseModel):
    game_id: int
    chat_id: int
    creator_id: int
    phase: str = "waiting"     # waiting/night/day/end
    mode: str = "classic"
    is_active: bool = True
    message_id: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None

    @property
    def key(self) -> str:
        return f"game:{self.game_id}:state"


class PlayerState(BaseModel):
    game_id: int
    user_id: int
    role: str
    team: Optional[str] = None

    is_alive: bool = True
    is_sleep: bool = False
    life: int = 100

    can_heal_self: bool = True
    is_actioned: bool = False
    last_visited_user_id: Optional[int] = None
    can_protection_self: bool = True
    can_document_self: bool = True
    can_investigate_self: bool = True
    can_osishdan_himoya: bool = True
    can_osishdan_himoya_adv: bool = True
    can_slip_himoya: bool = True
    missed_nights: int = 0
    should_choose_card: bool = False
    is_really_winner: bool = False
    win: bool = False
    osildi: bool = False
    
    # Action service uchun qo'shimcha
    is_protected: bool = False  # Protect action uchun

    maxsus_raqam: Optional[int] = None
    joined_at: datetime = Field(default_factory=datetime.now)
    deaded_at: Optional[datetime] = None

    is_sayed_last_word: bool = False
    
    @property
    def key(self) -> str:
        return f"game:{self.game_id}:player:{self.user_id}"

class GamePhaseState(BaseModel):
    game_id: int
    phase_num: int
    phase_type: str  # night/day
    started_at: datetime = Field(default_factory=datetime.now)
    is_end : bool = False

    @property
    def key(self) -> str:
        return f"game:{self.game_id}:phase:{self.phase_num}"
    
class ActionState(BaseModel):
    game_id: int
    phase_id: int
    actor_id: int
    target_id: Optional[int] = None
    action_type: str  # heal/kill/investigate/protect/document/osishdan_himoya/osishdan_himoya_adv/slip_himoya
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def key(self) -> str:
        return f"game:{self.game_id}:phase:{self.phase_id}:actions"

class VoteState(BaseModel):
    game_id: int
    phase_id: int
    voter_id: int
    target_id: int
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def key(self) -> str:
        # har phase uchun bitta hash ichida saqlaymiz: voter_id -> target_id
        return f"game:{self.game_id}:votes:{self.phase_no}"

class VoteLikeState(BaseModel):
    game_id: int
    phase_id: int
    voter_id: int
    target_id: int
    is_like: bool
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def key(self) -> str:
        # har phase uchun bitta hash ichida saqlaymiz: liker_id -> liked_id
        return f"game:{self.game_id}:vote_likes:{self.phase_id}"
    
class GeroyActionState(BaseModel):
    game_id: int
    phase_id: int
    actor_id: int
    target_id: Optional[int] = None
    action_type: str  # specific action types for Geroy
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def key(self) -> str:
        return f"game:{self.game_id}:phase:{self.phase_id}:geroy_actions"
    
class PlayerGameBallState(BaseModel):
    game_id: int
    player_id: int
    ball: int = 0

    @property
    def key(self) -> str:
        return f"game:{self.game_id}:player:{self.player_id}:game_ball"