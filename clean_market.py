from tortoise import Tortoise
import json
from models.user import User, Profile  
from models.game_data import Game, GamePlayer, Chat, GamePhase, Action, Vote, VoteLike, GazabdorPick
from redis.asyncio import Redis
from models.user import GeroyMarket
import json
from datetime import datetime
from asyncio import run

redis_client = Redis(host='localhost', port=6379, db=0, decode_responses=True)

async def init():
    await Tortoise.init(
        db_url="postgres://postgres:admin@localhost:5432/mafia_db",
        modules={
            "models": ["models.game_data", 'models.user', "models.game_set"]
        }
    )
    await Tortoise.generate_schemas()
    # Dublikat geroylarni tozalash (bitta egaga bir necha Geroys bo'lsa)
    all_market_items = await GeroyMarket.all().prefetch_related('geroy')
    for item in all_market_items:
        await item.delete() 

run(init())