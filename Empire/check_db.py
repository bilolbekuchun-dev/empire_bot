import asyncio
from tortoise import Tortoise
import config

async def main():
    await Tortoise.init(
        db_url=config.DATABASE_URL,
        modules={'models': ["models.game_data", 'models.user', "models.game_set"]}
    )
    from models.game_data import Game
    games = await Game.filter(is_active=True).all().prefetch_related("chat")
    for g in games:
        print(f"Active game {g.id} in chat {g.chat.chat_id} (phase: {g.phase})")

if __name__ == "__main__":
    asyncio.run(main())
