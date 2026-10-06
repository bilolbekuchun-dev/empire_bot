import asyncio
import json
from tortoise import Tortoise
from config import DATABASE_URL
from models.user import User, Profile
from models.game_data import GamePlayer, Action

async def investigate():
    await Tortoise.init(db_url=DATABASE_URL, modules={'models': ['models.user', 'models.game_data', 'models.game_set']})
    conn = Tortoise.get_connection("default")
    
    target_user_id = 8379517793
    print(f"=== INVESTIGATION FOR USER: {target_user_id} ===")
    
    user = await User.get_or_none(user_id=target_user_id)
    if not user:
        print("User topilmadi!")
        return
        
    print(f"User: ID={user.id}, user_id={user.user_id}, full_name={user.full_name}, mention={user.mention}")
    
    profile = await Profile.get_or_none(user=user)
    if profile:
        print(f"Profile: ID={profile.id}, Diamond={profile.diamond}, Dollar={profile.dollar}, Miltiq={profile.miltiq}, Himoya={profile.himoya}")
    
    # 1. Konchi qazishlari (Mining)
    mining_acts = await conn.execute_query_dict(
        "SELECT * FROM action WHERE actor_id IN (SELECT id FROM gameplayer WHERE user_id = $1) AND action_type LIKE '%konchi%' ORDER BY id DESC LIMIT 50;",
        [user.id]
    )
    print(f"--- Konchi / Mining Actions: {len(mining_acts)} ta ---")
    for a in mining_acts[:15]:
        print(f"  Action ID={a.get('id')}, type={a.get('action_type')}, result={a.get('result')}")
        
    # 2. Barcha Actionlar (actor yoki target sifatida)
    recent_acts = await conn.execute_query_dict(
        "SELECT a.*, gp.role as actor_role FROM action a JOIN gameplayer gp ON a.actor_id = gp.id WHERE gp.user_id = $1 ORDER BY a.id DESC LIMIT 30;",
        [user.id]
    )
    print(f"--- Oxirgi Actionlari (Actor): {len(recent_acts)} ta ---")
    for a in recent_acts[:15]:
        print(f"  ID={a.get('id')}, type={a.get('action_type')}, result={a.get('result')}, role={a.get('actor_role')}")
        
    # 3. O'yinlardagi ishtiroki
    gp_list = await conn.execute_query_dict(
        "SELECT gp.*, g.id as game_id, g.created_at, g.mode FROM gameplayer gp JOIN game g ON gp.game_id = g.id WHERE gp.user_id = $1 ORDER BY gp.id DESC LIMIT 20;",
        [user.id]
    )
    print(f"--- Oxirgi o'yinlari: {len(gp_list)} ta ---")
    for gp in gp_list[:10]:
        print(f"  Game #{gp.get('game_id')}, role={gp.get('role')}, is_alive={gp.get('is_alive')}, created_at={gp.get('created_at')}")
        
    # 4. Check all other tables containing user data
    tables = await conn.execute_query_dict("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
    print(f"--- Barcha SQL jadvallarni tekshirish ---")
    for t in tables:
        tname = t['table_name']
        cols = await conn.execute_query_dict(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{tname}';")
        cnames = [c['column_name'] for c in cols]
        for user_col in ['user_id', 'from_user_id', 'to_user_id', 'profile_id', 'owner_id']:
            if user_col in cnames:
                # check matching rows
                val = user.id if user_col in ['user_id', 'owner_id'] else (profile.id if user_col == 'profile_id' else target_user_id)
                try:
                    rows = await conn.execute_query_dict(f"SELECT * FROM {tname} WHERE {user_col} = {val} LIMIT 10;")
                    if rows:
                        print(f"  [TOPILDI] Jadval: {tname} ({len(rows)} qator): {rows}")
                except Exception:
                    pass
            
    await Tortoise.close_connections()

if __name__ == '__main__':
    asyncio.run(investigate())
