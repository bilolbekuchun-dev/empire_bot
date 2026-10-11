import asyncio
from tortoise import Tortoise
from config import DATABASE_URL

async def migrate():
    await Tortoise.init(db_url=DATABASE_URL, modules={'models': ['models.user', 'models.game_data', 'models.game_set']})
    conn = Tortoise.get_connection("default")
    await conn.execute_query("ALTER TABLE chat ADD COLUMN IF NOT EXISTS lang VARCHAR(5) DEFAULT 'uz';")
    print("Chat table migration done: 'lang' column added.")
    await Tortoise.close_connections()

if __name__ == '__main__':
    asyncio.run(migrate())
