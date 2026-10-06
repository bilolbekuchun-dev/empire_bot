import asyncio
import sys
from tortoise import Tortoise

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    from utils.database import init
    await init()
    
    conn = Tortoise.get_connection("default")
    
    # 1. Get all table names
    tables_res = await conn.execute_query_dict("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    table_names = [r['table_name'] for r in tables_res]
    print(f"Tables in DB ({len(table_names)}): {table_names}\n")
    
    target_uid = 8115343477
    
    # First get user db id
    user_res = await conn.execute_query_dict(f"SELECT * FROM \"user\" WHERE user_id = {target_uid}")
    if not user_res:
        print(f"User {target_uid} not found in user table!")
        await Tortoise.close_connections()
        return
    user = user_res[0]
    user_db_id = user['id']
    print(f"User DB record: {user}\n")
    
    # Scan every table for target_uid or user_db_id
    for tname in table_names:
        cols_res = await conn.execute_query_dict(f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = '{tname}'
        """)
        cols = [c['column_name'] for c in cols_res]
        
        # Build where clause for any int/bigint or text col
        conditions = []
        for col in cols:
            if 'user' in col or col in ['id', 'creator_id', 'owner_id', 'winner_id', 'from_user_id', 'to_user_id', 'buyer_user_id', 'seller_user_id']:
                conditions.append(f"{col} = {target_uid}")
                conditions.append(f"{col} = {user_db_id}")
            elif 'text' in col or 'caption' in col or 'extra' in col or 'details' in col:
                conditions.append(f"{col}::text LIKE '%{target_uid}%'")
        
        if conditions:
            query = f"SELECT * FROM \"{tname}\" WHERE {' OR '.join(conditions)} LIMIT 20;"
            try:
                rows = await conn.execute_query_dict(query)
                if rows:
                    print(f"=== Table: {tname} (found {len(rows)} rows) ===")
                    for row in rows:
                        print(row)
                    print()
            except Exception as e:
                # Query error
                pass

    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(main())
