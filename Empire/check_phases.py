
import asyncio, sys, os
sys.path.insert(0, '/root/Empire')
from tortoise import Tortoise
from dotenv import load_dotenv
load_dotenv('/root/Empire/.env')

async def run():
    await Tortoise.init(
        db_url=os.getenv('DATABASE_URL'),
        modules={'models': ['models.game_data', 'models.user', 'models.game_set']}
    )
    from models.game_data import Game, GamePhase, Action, Vote, Chat
    
    phases = await GamePhase.filter(game_id=27131).all()
    print(f"Phases for game 27131 (count={len(phases)}):")
    for ph in phases:
        print(f"  Phase id={ph.id}, num={ph.number}, type={ph.phase_type}, is_end={ph.is_end}")
        
    actions = await Action.filter(phase__in=phases).all()
    print(f"Actions in game 27131 (count={len(actions)}):")
    for a in actions:
        print(f"  Action: from={a.player_id}, target={a.target_player_id}, action={a.action_type}")
        
    await Tortoise.close_connections()

asyncio.run(run())
