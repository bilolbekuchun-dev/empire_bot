
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
    
    print('--- Active Games ---')
    active_games = await Game.filter(is_active=True).all()
    print(f'Total active games: {len(active_games)}')
    for g in active_games:
        players = await GamePlayer.filter(game=g).prefetch_related('user').all()
        print(f'Game ID: {g.id}, Chat: {g.chat_id}, Mode: {g.mode}, Phase: {g.phase}, Players: {len(players)}, Created: {g.created_at}')
        for p in players:
            print(f'   Player: {p.user.user_id} ({p.user.full_name}), Role: {p.role}, Alive: {p.is_alive}')

    print('\n--- Recent 5 Games ---')
    recent_games = await Game.all().order_by('-id').limit(5)
    for g in recent_games:
        print(f'Game ID: {g.id}, Chat: {g.chat_id}, Active: {g.is_active}, Phase: {g.phase}, Created: {g.created_at}')


    await Tortoise.close_connections()

asyncio.run(run())
