import sys
sys.path.insert(0, '/root/Empire')
import asyncio
from telethon import TelegramClient
from config import TELEGRAM_USERBOT_API_ID, TELEGRAM_USERBOT_API_HASH, TELEGRAM_USERBOT_SESSION

async def main():
    client = TelegramClient(TELEGRAM_USERBOT_SESSION, TELEGRAM_USERBOT_API_ID, TELEGRAM_USERBOT_API_HASH)
    await client.connect()
    qr = await client.qr_login()
    print("NEW_QR_URL_START", flush=True)
    print(qr.url, flush=True)
    print("NEW_QR_URL_END", flush=True)
    
    try:
        user = await qr.wait(timeout=180)
        print("QR_AUTH_SUCCESSFUL", flush=True)
        print(f"Logged in as: {user.first_name} (@{user.username}) {user.phone}", flush=True)
    except Exception as e:
        print("QR_AUTH_RESULT:", type(e).__name__, str(e), flush=True)
    finally:
        await client.disconnect()

asyncio.run(main())
