
import asyncio
from tortoise import Tortoise
from models.user import User
from models.game_data import GamePlayer, Game, GamePhase, VoteLike, Vote
from config import DATABASE_URL

async def find_dunyoim_votes():
    await Tortoise.init(db_url=DATABASE_URL, modules={'models': ['models.user', 'models.game_data', 'models.game_set']})
    
    u = await User.filter(user_id=8734301289).first()
    gps = await GamePlayer.filter(user=u).all()
    gp_ids = [p.id for p in gps]
    
    # Check VoteLike received
    vls = await VoteLike.filter(target_id__in=gp_ids).prefetch_related("phase", "phase__game", "target").all()
    print(f"Total VoteLikes where Dunyoim was target: {len(vls)}")
    for vl in vls:
        print(f"VoteLike ID={vl.id}, Game={vl.phase.game_id}, Phase={vl.phase.id}, GP_ID={vl.target_id}, GP_Role={repr(vl.target.role)}, Like={vl.is_like}")

    # Check Day Votes received
    votes = await Vote.filter(target_id__in=gp_ids).prefetch_related("phase", "phase__game", "target").all()
    print(f"Total Day Votes where Dunyoim was target: {len(votes)}")
    for v in votes:
        print(f"Day Vote ID={v.id}, Game={v.phase.game_id}, Phase={v.phase.id}, GP_ID={v.target_id}, GP_Role={repr(v.target.role)}")

    await Tortoise.close_connections()

if __name__ == '__main__':
    asyncio.run(find_dunyoim_votes())
