
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
    from models.game_set import GameSetTime, GamingOnChat, GroupMoreSet, CommandPermissionsChat
    from models.game_data import Game, Chat
    
    chat_id = -1004297310995
    gt, _ = await GameSetTime.get_or_create(chat_id=chat_id)
    print(f"GameSetTime: reg_time={gt.reg_time}, night_time={gt.night_time}, day_time={gt.day_time}, vote_time={gt.vote_time}")
    
    cp, _ = await CommandPermissionsChat.get_or_create(chat_id=chat_id)
    print(f"CommandPermissions: game={cp.game_cmd}, start={cp.start_cmd}, stop={cp.stop_cmd}")
    
    gc, _ = await GamingOnChat.get_or_create(chat_id=chat_id, defaults={"bot_id": 8755769302})
    print(f"GamingOnChat: can_gaming={gc.can_gaming}")
    
    ms, _ = await GroupMoreSet.get_or_create(chat_id=chat_id)
    print(f"GroupMoreSet: max_players={ms.max_players}, rollarni_guruhlash={ms.rollarni_guruhlash}")
    
    await Tortoise.close_connections()

asyncio.run(run())
