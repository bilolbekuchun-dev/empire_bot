import asyncio
import sys
from tortoise import Tortoise

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    from utils.database import init
    await init()
    
    conn = Tortoise.get_connection("default")
    user_db_id = 13674
    target_uid = 8115343477
    
    tables_res = await conn.execute_query_dict("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    table_names = [r['table_name'] for r in tables_res]
    
    for t in table_names:
        cols_res = await conn.execute_query_dict(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = '{t}'
        """)
        cols = [c['column_name'] for c in cols_res]
        conditions = []
        for col in cols:
            if 'user' in col or col in ['id', 'creator_id', 'owner_id', 'winner_id', 'from_user_id', 'to_user_id', 'buyer_user_id', 'seller_user_id']:
                conditions.append(f"{col} = {target_uid}")
                conditions.append(f"{col} = {user_db_id}")
        if conditions:
            query = f"SELECT count(*) as cnt FROM \"{t}\" WHERE {' OR '.join(conditions)};"
            try:
                r = await conn.execute_query_dict(query)
                cnt = r[0]['cnt']
                if cnt > 0:
                    print(f"Table '{t}': {cnt} rows")
            except:
                pass

    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(main())
