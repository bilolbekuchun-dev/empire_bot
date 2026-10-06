import asyncio
from tortoise import Tortoise
from config import DATABASE_URL
from models.user import User, Profile
from models.game_data import GamePlayer, Action

async def check_all():
    await Tortoise.init(db_url=DATABASE_URL, modules={'models': ['models.user', 'models.game_data', 'models.game_set']})
    conn = Tortoise.get_connection("default")
    
    u = await User.get(user_id=8379517793)
    p = await Profile.get(user=u)
    print(f"User: {u.id}, full_name: {u.full_name}, tg_id: {u.user_id}")
    print(f"Profile: {p.diamond} diamonds, {p.dollar} dollars, {p.miltiq} miltiq")
    
    # 1. Transfers where this user received diamonds or dollars
    transfers = await conn.execute_query_dict(
        "SELECT t.*, u_from.full_name as from_name, u_from.user_id as from_tg "
        "FROM transfers t JOIN \"user\" u_from ON t.from_user_id = u_from.id "
        "WHERE t.to_user_id = $1 ORDER BY t.id DESC;",
        [u.id]
    )
    print(f"\n=== RECEIVED TRANSFERS ({len(transfers)} ta) ===")
    total_tr_diamonds = sum(t['amount'] for t in transfers if t['type'] == 'diamond')
    total_tr_dollars = sum(t['amount'] for t in transfers if t['type'] == 'dollar')
    print(f"Total transferdan kelgan: {total_tr_diamonds} 💎, {total_tr_dollars} 💵")
    for t in transfers:
        print(f"  + {t['amount']} {t['type']} from {t['from_name']} ({t['from_tg']}) at {t['created_at']}")
        
    # 2. Sent transfers
    sent = await conn.execute_query_dict(
        "SELECT t.*, u_to.full_name as to_name, u_to.user_id as to_tg "
        "FROM transfers t JOIN \"user\" u_to ON t.to_user_id = u_to.id "
        "WHERE t.from_user_id = $1 ORDER BY t.id DESC;",
        [u.id]
    )
    print(f"\n=== SENT TRANSFERS ({len(sent)} ta) ===")
    for t in sent:
        print(f"  - {t['amount']} {t['type']} to {t['to_name']} ({t['to_tg']}) at {t['created_at']}")

    # 3. Games played
    gps = await conn.execute_query_dict(
        "SELECT gp.id, gp.game_id, gp.role, gp.win, gp.is_really_winner, gp.is_alive, g.created_at, g.chat_id "
        "FROM gameplayer gp JOIN game g ON gp.game_id = g.id WHERE gp.user_id = $1 ORDER BY gp.id DESC;",
        [u.id]
    )
    print(f"\n=== ALL GAMES PLAYED ({len(gps)} ta) ===")
    for gp in gps:
        print(f"  Game #{gp['game_id']} | Role: {gp['role']} | Win: {gp['win']} | RealWinner: {gp['is_really_winner']} | Chat: {gp['chat_id']} | Date: {gp['created_at']}")
        
    # 4. Actions in these games (Konchi, Jin, etc.)
    gp_ids = [gp['id'] for gp in gps]
    if gp_ids:
        gp_ids_str = ",".join(str(i) for i in gp_ids)
        acts = await conn.execute_query_dict(
            f"SELECT * FROM action WHERE actor_id IN ({gp_ids_str}) OR target_id IN ({gp_ids_str}) ORDER BY id DESC;"
        )
        print(f"\n=== ALL ACTIONS INVOLVING USER ({len(acts)} ta) ===")
        for a in acts:
            print(f"  Action #{a['id']}: actor_id={a['actor_id']}, target_id={a['target_id']}, type={a['action_type']}, result={a['result']}")

    await Tortoise.close_connections()

if __name__ == '__main__':
    asyncio.run(check_all())
