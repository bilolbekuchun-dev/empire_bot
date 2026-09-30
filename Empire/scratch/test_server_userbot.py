
import sys
sys.path.insert(0, "/root/Empire")
import asyncio
from telethon import TelegramClient
from config import TELEGRAM_USERBOT_API_ID, TELEGRAM_USERBOT_API_HASH, TELEGRAM_USERBOT_SESSION

async def test():
    client = TelegramClient(TELEGRAM_USERBOT_SESSION, TELEGRAM_USERBOT_API_ID, TELEGRAM_USERBOT_API_HASH)
    await client.connect()
    is_auth = await client.is_user_authorized()
    print("SERVER_USERBOT_IS_AUTH:", is_auth)
    if is_auth:
        me = await client.get_me()
        print(f"SERVER_USERBOT_LOGGED_IN: {me.first_name} (@{me.username}) ID:{me.id}")
    await client.disconnect()

asyncio.run(test())
