
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
    from models.game_data import Game, GamePhase
    
    g = await Game.get_or_none(id=27131)
    if g:
        print(f"Game 27131: active={g.is_active}, phase={g.phase}")
        phases = await GamePhase.filter(game=g).order_by('-id').limit(5)
        for p in phases:
            print(f"  Phase {p.id}: {p.phase_type}, num={p.number}, is_end={p.is_end}")
            
    await Tortoise.close_connections()

asyncio.run(run())
