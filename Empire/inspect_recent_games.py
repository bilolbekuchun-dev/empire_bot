import asyncio
import sys
from tortoise import Tortoise
from models.game_data import Game, GamePlayer

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    from utils.database import init
    await init()
    
    # Get last 5 games
    games = await Game.filter(phase="end").order_by("-id").limit(5).prefetch_related("chat")
    for g in games:
        print(f"=== GAME ID: {g.id} | Mode: {g.mode} | Chat: {g.chat.chat_id} ({g.chat.title}) | Created: {g.created_at} ===")
        players = await GamePlayer.filter(game=g).prefetch_related("user").order_by("id").all()
        alive_players = [p for p in players if p.is_alive]
        dead_players = [p for p in players if not p.is_alive]
        print(f"Total players: {len(players)}, Alive at end: {len(alive_players)}, Dead: {len(dead_players)}")
        print("Alive at end:")
        for p in alive_players:
            print(f"  - {p.user.full_name} ({p.user.user_id}): role={p.role}, win={p.win}")
        print("Dead at end:")
        for p in dead_players:
            print(f"  - {p.user.full_name} ({p.user.user_id}): role={p.role}, win={p.win}, deaded_at={p.deaded_at}")
        print()

    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(main())
