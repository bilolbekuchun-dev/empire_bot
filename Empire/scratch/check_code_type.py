
import sys
sys.path.insert(0, '/root/Empire')
import asyncio
from telethon import TelegramClient
from config import TELEGRAM_USERBOT_API_ID, TELEGRAM_USERBOT_API_HASH, TELEGRAM_USERBOT_SESSION

PHONE = '+998900921511'

async def main():
    client = TelegramClient(TELEGRAM_USERBOT_SESSION, TELEGRAM_USERBOT_API_ID, TELEGRAM_USERBOT_API_HASH)
    await client.connect()
    try:
        sent = await client.send_code_request(PHONE)
        print("SENT_CODE_TYPE:", type(sent.type).__name__)
        print("SENT_DETAILS:", sent)
    except Exception as e:
        print("ERROR:", type(e).__name__, str(e))
    finally:
        await client.disconnect()

asyncio.run(main())
