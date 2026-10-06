
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
    
    active_games = await Game.filter(is_active=True).prefetch_related('chat', 'creator').all()
    print(f"=== TOTAL ACTIVE GAMES: {len(active_games)} ===")
    for g in active_games:
        p_count = await GamePlayer.filter(game=g).count()
        alive_count = await GamePlayer.filter(game=g, is_alive=True).count()
        print(f"Game #{g.id} in Chat {g.chat.chat_id} ({g.chat.title}): Phase={g.phase}, Mode={g.mode}, Total Players={p_count}, Alive={alive_count}, Created={g.created_at}")

    await Tortoise.close_connections()

asyncio.run(run())
