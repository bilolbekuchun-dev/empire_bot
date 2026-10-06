import asyncio
from tortoise import Tortoise
from models.game_data import Game, GamePlayer
from datetime import datetime, timezone

from utils.database import init

async def inspect_games():
    await init()
    
    games = await Game.filter(is_active=False).order_by("-id").limit(10).prefetch_related("chat")
    now = datetime.now(timezone.utc)
    print(f"Current UTC now: {now}")
    for g in games:
        print(f"Game ID: {g.id} | chat: {g.chat.chat_id} | created_at: {g.created_at} (tz: {g.created_at.tzinfo if g.created_at else None}) | phase: {g.phase}")
        if g.created_at:
            # check players deaded_at / joined_at
            players = await GamePlayer.filter(game=g).all()
            if players:
                first_join = min(p.joined_at for p in players if p.joined_at)
                last_dead = max((p.deaded_at for p in players if p.deaded_at), default=first_join)
                print(f"   first_join: {first_join} | last_dead: {last_dead} | diff: {(last_dead - first_join).total_seconds()}s")
            
            # calculate diff
            diff1 = (now - g.created_at).total_seconds()
            print(f"   diff from now: {diff1}s")

    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(inspect_games())
