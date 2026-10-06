import asyncio
from tortoise import Tortoise
from config import DATABASE_URL

async def fix_db():
    print(f"Connecting to {DATABASE_URL}...")
    await Tortoise.init(
        db_url=DATABASE_URL,
        modules={"models": ["models.game_data", "models.user", "models.game_set"]}
    )
    
    conn = Tortoise.get_connection("default")
    
    # List of possible table names and column names to add
    migrations = [
        ("commandpermissionschat", "extend_cmd", "VARCHAR(10) DEFAULT 'admin'"),
        ("command_permissions_chat", "extend_cmd", "VARCHAR(10) DEFAULT 'admin'"), # just in case
    ]
    
    for table, column, definition in migrations:
        try:
            print(f"Checking table {table} for column {column}...")
            # We use a trick to check if table exists first
            await conn.execute_query(f"SELECT 1 FROM {table} LIMIT 1")
            
            print(f"Table {table} exists. Adding column {column}...")
            await conn.execute_query(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}")
            print(f"✅ Column {column} added to {table}")
        except Exception as e:
            print(f"❌ Error with table {table}: {e}")

    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(fix_db())
