import asyncio
import json
from tortoise import Tortoise
from config import DATABASE_URL
from models.user import User, Profile

async def investigate():
    await Tortoise.init(db_url=DATABASE_URL, modules={'models': ['models.user', 'models.game_data', 'models.game_set']})
    conn = Tortoise.get_connection("default")
    
    target_user_id = 8379517793
    user = await User.get_or_none(user_id=target_user_id)
    profile = await Profile.get_or_none(user=user)
    
    print(f"=== USER {user.id} ({user.user_id} - {user.full_name}) ===")
    print(f"CURRENT BALANCE: {profile.diamond} 💎, {profile.dollar} 💵")
    
    # 1. Transfers
    transfers = await conn.execute_query_dict(
        "SELECT t.*, u1.user_id as from_tg, u2.user_id as to_tg, u1.full_name as from_name, u2.full_name as to_name "
        "FROM transfers t "
        "LEFT JOIN \"user\" u1 ON t.from_user_id=u1.id "
        "LEFT JOIN \"user\" u2 ON t.to_user_id=u2.id "
        "WHERE t.from_user_id = $1 OR t.to_user_id = $1 "
        "ORDER BY t.id DESC;",
        [user.id]
    )
    print(f"\n--- TRANSFERS ({len(transfers)} ta) ---")
    for t in transfers:
        direction = "KELDI (+)" if t['to_user_id'] == user.id else "KETDI (-)"
        print(f"  [{direction}] ID={t['id']} | Amount={t['amount']} {t['type']} | From={t['from_name']} ({t['from_tg']}) -> To={t['to_name']} ({t['to_tg']}) | Date={t['created_at']} | Caption={t.get('caption')}")
        
    # 2. Check sandiqlar
    sandiq_rows = await conn.execute_query_dict("SELECT * FROM sandiqlar WHERE user_id = $1;", [user.id])
    print(f"\n--- SANDIQLAR ({len(sandiq_rows)} ta) ---")
    for s in sandiq_rows:
        print(f"  {s}")

    # 3. Check para
    para_rows = await conn.execute_query_dict(
        "SELECT p.*, u1.user_id as u1_tg, u2.user_id as u2_tg, u1.full_name as u1_name, u2.full_name as u2_name "
        "FROM paralar p "
        "LEFT JOIN \"user\" u1 ON p.user1_id=u1.id "
        "LEFT JOIN \"user\" u2 ON p.user2_id=u2.id "
        "WHERE p.user1_id = $1 OR p.user2_id = $1;",
        [user.id]
    )
    print(f"\n--- PARALAR ({len(para_rows)} ta) ---")
    for p in para_rows:
        print(f"  {p}")

    # 4. Check all active roles bought or assigned
    act_roles = await conn.execute_query_dict(
        "SELECT * FROM active_roles WHERE profile_id = $1;",
        [profile.id]
    )
    print(f"\n--- ACTIVE ROLES ({len(act_roles)} ta) ---")
    for ar in act_roles:
        print(f"  {ar}")

    await Tortoise.close_connections()

if __name__ == '__main__':
    asyncio.run(investigate())
