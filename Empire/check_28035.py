
import asyncio
from tortoise import Tortoise
from models.user import User
from models.game_data import GamePlayer, Game, GamePhase, Vote, VoteLike, Action
from config import DATABASE_URL

async def check_game():
    await Tortoise.init(db_url=DATABASE_URL, modules={'models': ['models.user', 'models.game_data', 'models.game_set']})
    
    # Check Game 28035 phases
    game = await Game.get(id=28035)
    phases = await GamePhase.filter(game=game).all()
    for ph in phases:
        print(f"Phase {ph.id}: type={ph.phase_type}, num={ph.number}")
        vls = await VoteLike.filter(phase=ph).prefetch_related("target", "target__user").all()
        for vl in vls:
            print(f"  VoteLike: Target={vl.target.user.full_name} (Role='{vl.target.role}'), Like={vl.is_like}")

    await Tortoise.close_connections()

if __name__ == '__main__':
    asyncio.run(check_game())
