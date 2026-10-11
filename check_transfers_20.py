import asyncio
import sys
from tortoise import Tortoise

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    from utils.database import init
    await init()
    
    conn = Tortoise.get_connection("default")
    
    # Check any diamond transfers with amount = 20 or to/from users with name containing '𝓪' or similar
    res = await conn.execute_query_dict("""
        SELECT t.*, u1.user_id as from_uid, u1.full_name as from_name, u2.user_id as to_uid, u2.full_name as to_name 
        FROM transfers t
        LEFT JOIN "user" u1 ON t.from_user_id = u1.id
        LEFT JOIN "user" u2 ON t.to_user_id = u2.id
        WHERE t.type = 'diamond' AND (t.amount = 20 OR t.amount = 19 OR t.amount = 21)
        ORDER BY t.id DESC LIMIT 30;
    """)
    print(f"=== DIAMOND TRANSFERS (amount ~20) (count={len(res)}) ===")
    for r in res:
        print(f"[{r['created_at']}] {r['from_name']} ({r['from_uid']}) -> {r['to_name']} ({r['to_uid']}) : {r['amount']} diamonds (type: {r['type']})")

    # Also check if any users have full_name like '𝓪'
    res_users = await conn.execute_query_dict("""
        SELECT u.id, u.user_id, u.full_name, p.diamond, p.dollar 
        FROM "user" u 
        LEFT JOIN profile p ON p.user_id = u.id 
        WHERE u.full_name ILIKE '%𝓪%' OR u.user_id::text LIKE '%811534%'
        LIMIT 20;
    """)
    print(f"\n=== SIMILAR USERS (count={len(res_users)}) ===")
    for ru in res_users:
        print(ru)

    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(main())
