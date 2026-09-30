import asyncio
from tortoise import Tortoise
from config import DATABASE_URL
from models.user import User, Profile, AdminGiveLog, DiamondBuyStars, ChangeDiamondGiveAway, OpenSandiqs, Paralar

async def run_check():
    await Tortoise.init(db_url=DATABASE_URL, modules={'models': ['models.user', 'models.game_data', 'models.game_set']})
    conn = Tortoise.get_connection("default")
    
    target_tg_id = 8379517793
    u = await User.get(user_id=target_tg_id)
    p = await Profile.get(user=u)
    
    print(f"USER: {u.full_name} ({u.user_id}, internal_id={u.id})")
    print(f"PROFILE: diamonds={p.diamond}, dollars={p.dollar}")
    
    # 1. Admin Give Log
    admin_logs = await AdminGiveLog.filter(target_user_id=target_tg_id).all()
    print(f"\n--- ADMIN GIVE LOGS ({len(admin_logs)} ta) ---")
    for l in admin_logs:
        print(f"  Admin: {l.admin_user_id} | Field: {l.field} | Amount: {l.amount} | Source: {l.source} | Date: {l.created_at}")
        
    # 2. Stars Diamond Purchases
    stars_buys = await DiamondBuyStars.filter(user_id=target_tg_id).all()
    print(f"\n--- STARS PURCHASES ({len(stars_buys)} ta) ---")
    for s in stars_buys:
        print(f"  Amount: {s.amount} {s.kind} | Stars: {s.stars} | Source: {s.source} | Date: {s.created_at}")
        
    # 3. ChangeDiamondGiveAway (olmos tarqatishlaridan yig'ish)
    all_gw = await conn.execute_query_dict("SELECT * FROM changediamondgiveaway;")
    collected_gw = []
    for gw in all_gw:
        # collected_users can be list or json string
        import json
        c_users = gw['collected_users']
        if isinstance(c_users, str):
            try: c_users = json.loads(c_users)
            except: c_users = []
        if target_tg_id in c_users or str(target_tg_id) in [str(x) for x in c_users]:
            collected_gw.append(gw)
            
    print(f"\n--- COLLECTED DIAMOND GIVEAWAYS ({len(collected_gw)} ta) ---")
    for gw in collected_gw:
        print(f"  Giveaway #{gw['id']}: Amount={gw['amount']} | Chat={gw['chat_id']} | Date={gw['created_at']}")
        
    # 4. OpenSandiqs
    sandiqs = await OpenSandiqs.filter(user=u).all()
    print(f"\n--- OPEN SANDIQS ({len(sandiqs)} ta) ---")
    for s in sandiqs:
        print(f"  Sandiq type: {s.sandiq_type} | Date: {s.created_at}")

    await Tortoise.close_connections()

if __name__ == '__main__':
    asyncio.run(run_check())
