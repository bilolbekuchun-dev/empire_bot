
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
    from models.game_data import Game, GamePlayer, Chat
    
    g = await Game.get_or_none(id=27131)
    if g:
        print(f"Game 27131: active={g.is_active}, phase={g.phase}, mode={g.mode}, message_id={g.message_id}, created_at={g.created_at}")
        players = await GamePlayer.filter(game=g).prefetch_related('user').all()
        for p in players:
            print(f"  Player: {p.user.user_id} ({p.user.full_name}) -> Role: {p.role!r}, Alive: {p.is_alive}")
    else:
        print("Game 27131 not found")

    await Tortoise.close_connections()

asyncio.run(run())
