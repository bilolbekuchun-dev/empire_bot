
import asyncio
from tortoise import Tortoise
from models.user import User
from models.game_data import GamePlayer, Game, GamePhase, Vote, VoteLike, Action
from config import DATABASE_URL

async def inspect_game():
    await Tortoise.init(db_url=DATABASE_URL, modules={'models': ['models.user', 'models.game_data', 'models.game_set']})
    
    game = await Game.filter(id=28046).prefetch_related("chat").first()
    if game:
        print(f"Game: {game.id}, Chat: {game.chat.title} ({game.chat.chat_id}), Phase: {game.phase}, Mode: {game.mode}")
        players = await GamePlayer.filter(game=game).prefetch_related("user").all()
        print(f"Total players in game 28046: {len(players)}")
        for p in players:
            print(f"  P: ID={p.id}, UID={p.user.user_id}, Name={p.user.full_name}, Role={repr(p.role)}, Alive={p.is_alive}, Osildi={p.osildi}")
        
        phases = await GamePhase.filter(game=game).all()
        for ph in phases:
            print(f"  Phase: ID={ph.id}, Type={ph.phase_type}, Number={ph.number}, is_end={ph.is_end}")

    await Tortoise.close_connections()

if __name__ == '__main__':
    asyncio.run(inspect_game())
