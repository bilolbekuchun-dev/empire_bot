import asyncio
from tortoise import Tortoise
from config import DATABASE_URL
from models.user import User, Profile, Transfers

async def run_analysis():
    await Tortoise.init(db_url=DATABASE_URL, modules={'models': ['models.user', 'models.game_data', 'models.game_set']})
    conn = Tortoise.get_connection("default")
    
    target_tg_id = 8379517793
    u = await User.get(user_id=target_tg_id)
    p = await Profile.get(user=u)
    
    print("=== TO'LIQ FOYDALANUVCHI PROFILI ===")
    print(f"Foydalanuvchi: {u.full_name}")
    print(f"Telegram ID: {u.user_id} (DB ID: {u.id})")
    print(f"Olmoslar (Diamond): {p.diamond} 💎")
    print(f"Dollarlar: {p.dollar} 💵")
    print(f"Miltiq: {p.miltiq}, Himoya: {p.himoya}, Qotildan himoya: {p.qotildan_himoya}")
    print(f"O'yinlar soni: {p.games_count}, G'alabalar: {p.wins}")
    print(f"Ro'yxatdan o'tgan sana: {u.created_at}")
    
    # 1. Barcha kelgan o'tkazmalar (Transfers)
    tr_in = await conn.execute_query_dict(
        "SELECT t.*, u_from.full_name as from_name, u_from.user_id as from_tg "
        "FROM transfers t JOIN \"user\" u_from ON t.from_user_id = u_from.id "
        "WHERE t.to_user_id = $1 ORDER BY t.created_at ASC;",
        [u.id]
    )
    print(f"\n--- KELGAN BARCHA O'TKAZMALAR ({len(tr_in)} ta) ---")
    for t in tr_in:
        print(f"  {t['created_at'].strftime('%Y-%m-%d %H:%M:%S')} | +{t['amount']} {t['type']} | Kimdan: {t['from_name']} ({t['from_tg']})")
        
    # 2. Chiqqan barcha o'tkazmalar
    tr_out = await conn.execute_query_dict(
        "SELECT t.*, u_to.full_name as to_name, u_to.user_id as to_tg "
        "FROM transfers t JOIN \"user\" u_to ON t.to_user_id = u_to.id "
        "WHERE t.from_user_id = $1 ORDER BY t.created_at ASC;",
        [u.id]
    )
    print(f"\n--- CHIQGAN BARCHA O'TKAZMALAR ({len(tr_out)} ta) ---")
    for t in tr_out:
        print(f"  {t['created_at'].strftime('%Y-%m-%d %H:%M:%S')} | -{t['amount']} {t['type']} | Kimga: {t['to_name']} ({t['to_tg']})")

    await Tortoise.close_connections()

if __name__ == '__main__':
    asyncio.run(run_analysis())
