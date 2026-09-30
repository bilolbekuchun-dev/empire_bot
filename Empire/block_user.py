import asyncio
from utils.database import init
from models.user import User, Blocked_user
from tortoise import Tortoise

async def main():
    await init()
    user_id = 2099616410
    user = await User.get_or_none(user_id=user_id)
    if not user:
        print(f"User {user_id} not found in DB.")
        await Tortoise.close_connections()
        return
    
    blocked = await Blocked_user.get_or_none(user=user)
    if blocked:
        print("User already blocked.")
    else:
        await Blocked_user.create(user=user)
        print("User successfully blocked in DB.")
    
    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(main())
