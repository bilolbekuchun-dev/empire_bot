
import asyncio
from tortoise import Tortoise
from models.user import User
from models.game_data import GamePlayer, Game, GamePhase
from config import DATABASE_URL

async def check_all_bad_roles():
    await Tortoise.init(db_url=DATABASE_URL, modules={'models': ['models.user', 'models.game_data', 'models.game_set']})
    
    # Check all active or recent games where phase != 'waiting' and players have role == ''
    games = await Game.filter(phase__in=["day", "night", "end"]).order_by("-id").limit(20)
    for g in games:
        gps = await GamePlayer.filter(game=g).all()
        empty_roles = [p for p in gps if not p.role or p.role.strip() == ""]
        if empty_roles:
            print(f"Game {g.id}: phase={g.phase}, mode={g.mode}, total_players={len(gps)}, empty_role_players={len(empty_roles)}")
            for ep in empty_roles:
                await ep.fetch_related("user")
                print(f"  Empty Role Player: GP {ep.id}, User {ep.user.full_name} ({ep.user.user_id})")

    await Tortoise.close_connections()

if __name__ == '__main__':
    asyncio.run(check_all_bad_roles())
