import asyncio
from tortoise import Tortoise
from config import DATABASE_URL
from models.user import User, Profile
from models.game_data import GamePlayer, Action

async def investigate():
    await Tortoise.init(db_url=DATABASE_URL, modules={'models': ['models.user', 'models.game_data', 'models.game_set']})
    conn = Tortoise.get_connection("default")
    
    target_user_id = 8379517793
    user = await User.get_or_none(user_id=target_user_id)
    if not user:
        print("User topilmadi!")
        return
        
    profile = await Profile.get_or_none(user=user)
    print("USER ID:", user.id, "TG_ID:", user.user_id, "NAME:", user.full_name)
    print("PROFILE: diamonds =", profile.diamond, "dollars =", profile.dollar)
    
    # Check all transactions / transfers involving 8379517793
    for tname in ["transfers", "transactions", "sandiqlar", "user_sandiqlar", "paralar", "active_roles"]:
        try:
            rows = await conn.execute_query_dict(f"SELECT * FROM {tname} LIMIT 5;")
            print(f"Table {tname} exists, sample: {rows}")
        except Exception as e:
            pass
            
    # Check all actions where target is 8379517793
    acts = await conn.execute_query_dict(
        "SELECT a.id, a.action_type, a.result, gp.role as actor_role, u.user_id as actor_tg "
        "FROM action a JOIN gameplayer gp ON a.actor_id = gp.id JOIN \"user\" u ON gp.user_id = u.id "
        "WHERE a.target_id IN (SELECT id FROM gameplayer WHERE user_id = $1) "
        "ORDER BY a.id DESC LIMIT 40;",
        [user.id]
    )
    print("--- ACTIONS ON USER ---")
    for a in acts:
        print(f"  Action #{a['id']}: type={a['action_type']}, result={a['result']}, actor_role={a['actor_role']}, actor_tg={a['actor_tg']}")
        
    # Check all actions BY user
    my_acts = await conn.execute_query_dict(
        "SELECT a.id, a.action_type, a.result, gp.role as my_role, g.id as game_id "
        "FROM action a JOIN gameplayer gp ON a.actor_id = gp.id JOIN game g ON gp.game_id = g.id "
        "WHERE gp.user_id = $1 "
        "ORDER BY a.id DESC LIMIT 40;",
        [user.id]
    )
    print("--- ACTIONS BY USER ---")
    for a in my_acts:
        print(f"  Game #{a['game_id']} (Role: {a['my_role']}): action_type={a['action_type']}, result={a['result']}")

    await Tortoise.close_connections()

if __name__ == '__main__':
    asyncio.run(investigate())
