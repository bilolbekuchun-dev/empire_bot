
import asyncio, sys, os
sys.path.insert(0, '/root/Empire')
from tortoise import Tortoise
from dotenv import load_dotenv
load_dotenv('/root/Empire/.env')

async def run():
    await Tortoise.init(
        db_url=os.getenv('DATABASE_URL'),
        modules={'models': ['models.game_data', 'models.user', 'models.game_set']}
    )
    from models.game_data import Game, GamePlayer, Chat
    chat = await Chat.get_or_none(id=404)
    if chat:
        print(f"Chat 404: chat_id={chat.chat_id}, title={chat.title}, type={chat.type}")
    
    await Tortoise.close_connections()

asyncio.run(run())
