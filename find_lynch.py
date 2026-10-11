
import asyncio
from tortoise import Tortoise
from models.user import User
from models.game_data import GamePlayer, Game, GamePhase, Vote, VoteLike, Action
from config import DATABASE_URL

async def find_lynch():
    await Tortoise.init(db_url=DATABASE_URL, modules={'models': ['models.user', 'models.game_data', 'models.game_set']})
    
    u = await User.filter(user_id=8734301289).first()
    if u:
        gps = await GamePlayer.filter(user=u).order_by("-id").limit(15)
        for gp in gps:
            await gp.fetch_related("game", "game__chat")
            print(f"GP {gp.id}: Game {gp.game.id} ({gp.game.phase}), Role='{gp.role}', alive={gp.is_alive}, osildi={gp.osildi}, chat={gp.game.chat.title}")

    print("--- Recent Lynched Players across DB ---")
    lynched_gps = await GamePlayer.filter(osildi=True).order_by("-id").limit(10).prefetch_related("user", "game")
    for gp in lynched_gps:
        print(f"Lynched: GP {gp.id}, Game {gp.game.id}, User {gp.user.full_name}, Role='{gp.role}'")

    await Tortoise.close_connections()

if __name__ == '__main__':
    asyncio.run(find_lynch())
