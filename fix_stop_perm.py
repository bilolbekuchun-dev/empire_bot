import asyncio
from tortoise import Tortoise
from config import DATABASE_URL
from models.game_set import CommandPermissionsChat

async def main():
    await Tortoise.init(
        db_url=DATABASE_URL,
        modules={'models': ['models.user', 'models.game_data', 'models.game_set']}
    )
    chat_id = -1003896649758
    cmd_perm, _ = await CommandPermissionsChat.get_or_create(chat_id=chat_id)
    cmd_perm.stop_cmd = 'admin'
    await cmd_perm.save()
    print("Fixed stop_cmd to 'admin'")
    
    await Tortoise.close_connections()

if __name__ == '__main__':
    asyncio.run(main())
