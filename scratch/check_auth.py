
import sys
sys.path.insert(0, '/root/Empire')
import asyncio
from telethon import TelegramClient
from config import TELEGRAM_USERBOT_API_ID, TELEGRAM_USERBOT_API_HASH, TELEGRAM_USERBOT_SESSION

async def main():
    client = TelegramClient(TELEGRAM_USERBOT_SESSION, TELEGRAM_USERBOT_API_ID, TELEGRAM_USERBOT_API_HASH)
    await client.connect()
    is_auth = await client.is_user_authorized()
    print('is_user_authorized:', is_auth)
    if is_auth:
        me = await client.get_me()
        print('Logged in as:', me.first_name, me.username, me.phone)
    await client.disconnect()

asyncio.run(main())
