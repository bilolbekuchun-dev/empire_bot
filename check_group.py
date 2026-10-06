import asyncio
from tortoise import Tortoise
from config import DATABASE_URL
from models.game_set import CommandPermissionsChat, GamingOnChat
from models.game_data import Chat
import sys

async def main():
    await Tortoise.init(
        db_url=DATABASE_URL,
        modules={'models': ['models.user', 'models.game_data', 'models.game_set']}
    )
    chat_id = -1003896649758
    
    chat = await Chat.filter(chat_id=chat_id).first()
    print(f"Chat: {chat.title if chat else 'NOT FOUND'}")
    
    gaming = await GamingOnChat.filter(chat_id=chat_id).first()
    if gaming:
        print(f"can_gaming: {gaming.can_gaming}")
    else:
        print("GamingOnChat: NOT FOUND (defaults to True)")
        
    cmd_perm = await CommandPermissionsChat.filter(chat_id=chat_id).first()
    if cmd_perm:
        print(f"game_cmd permission: {cmd_perm.game_cmd}")
    else:
        print("CommandPermissionsChat: NOT FOUND (defaults to 'admin')")
    
    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(main())
