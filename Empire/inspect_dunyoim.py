
import asyncio
from tortoise import Tortoise
from models.user import User
from models.game_data import GamePlayer, Game
from config import DATABASE_URL

async def inspect():
    await Tortoise.init(db_url=DATABASE_URL, modules={'models': ['models.user', 'models.game_data', 'models.game_set']})
    
    # Check user Dunyoim
    users = await User.filter(full_name__icontains="𝒟𝓊𝓃𝓎𝑜𝒾𝓂")
    print(f"Found users with Dunyoim: {len(users)}")
    for u in users:
        print(f"User ID: {u.user_id}, Name: {u.full_name}, Mention: {u.mention}")
        # find recent GamePlayer records
        gps = await GamePlayer.filter(user=u).order_by("-id").limit(10)
        for gp in gps:
            print(f"  GP ID: {gp.id}, Game ID: {gp.game_id}, Role: {repr(gp.role)}, is_alive: {gp.is_alive}, osildi: {gp.osildi}")

    # Check any GamePlayer where role is None or empty or strange
    bad_gps = await GamePlayer.filter(role__in=["", "None", None]).order_by("-id").limit(10)
    print(f"Total bad role gps: {len(bad_gps)}")
    for gp in bad_gps:
        print(f"Bad GP: ID={gp.id}, Game={gp.game_id}, Role={repr(gp.role)}")

    await Tortoise.close_connections()

if __name__ == '__main__':
    asyncio.run(inspect())
