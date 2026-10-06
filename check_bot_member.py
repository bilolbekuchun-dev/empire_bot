
import asyncio, sys, os
sys.path.insert(0, '/root/Empire')
from aiogram import Bot
from tortoise import Tortoise
from dotenv import load_dotenv
load_dotenv('/root/Empire/.env')

async def run():
    await Tortoise.init(
        db_url=os.getenv('DATABASE_URL'),
        modules={'models': ['models.game_data', 'models.user', 'models.game_set']}
    )
    from models.game_data import Game, GamePlayer, Chat
    bot = Bot(token=os.getenv('TOKEN'))
    
    chats = await Chat.all().order_by('-id').limit(10)
    for c in chats:
        try:
            member = await bot.get_chat_member(c.chat_id, (await bot.get_me()).id)
            print(f"Chat {c.chat_id} ({c.title}): status={member.status}, can_delete={getattr(member, 'can_delete_messages', None)}")
        except Exception as e:
            print(f"Chat {c.chat_id} ({c.title}): ERROR={e}")
            
    await bot.session.close()
    await Tortoise.close_connections()

asyncio.run(run())
