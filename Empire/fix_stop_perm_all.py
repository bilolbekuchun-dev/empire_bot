import asyncio
from tortoise import Tortoise
from config import DATABASE_URL
from models.game_set import CommandPermissionsChat

async def main():
    await Tortoise.init(
        db_url=DATABASE_URL,
        modules={'models': ['models.user', 'models.game_data', 'models.game_set']}
    )
    # To be safe, set all stop_cmd to 'admin' where it might be causing issues
    # or just tell the user they can change it back from settings.
    await Tortoise.close_connections()

if __name__ == '__main__':
    asyncio.run(main())
