
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
    
    chat_id = -1004297310995
    print("=== Checking chat -1004297310995 ===")
    try:
        chat_info = await bot.get_chat(chat_id)
        print("Chat title:", chat_info.title)
        member = await bot.get_chat_member(chat_id, (await bot.get_me()).id)
        print(f"Bot status in chat: {member.status}")
    except Exception as e:
        print("Error getting chat info:", e)
        
    game = await Game.filter(chat__chat_id=chat_id, is_active=True).first()
    if game:
        print(f"Active game found: id={game.id}, phase={game.phase}, mode={game.mode}")
        players = await GamePlayer.filter(game=game).prefetch_related('user').all()
        print(f"Players count: {len(players)}")
        for p in players:
            print(f"  Player {p.user.user_id} ({p.user.full_name}): role={p.role!r}, alive={p.is_alive}")
    else:
        print("No active game in this chat!")
        
    await bot.session.close()
    await Tortoise.close_connections()

asyncio.run(run())
