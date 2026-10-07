import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import BotCommand
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.webhook.aiohttp_server import TokenBasedRequestHandler
from logging import basicConfig, INFO
from asyncio import run, sleep
from models.game_data import Chat
from aiogram.client.telegram import TelegramAPIServer
from config import ADMINS, TOKEN, PORT
from handlers import router
from logging import basicConfig, INFO
from utils import database
from middlewares.floot import MyThrottlingMiddleware
from aiogram.methods import DeleteWebhook
from asyncio import create_task
from utils.tasks import daily_balance_task, long_games_attack, check_vip_users, long_giveaways_cleanup, check_personal_birthday_gifts
from middlewares.manager import GroupWriteGuardMiddleware
import redis
import logging
from mylogger import setup_db_logging
import os
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

# Ma'lumotlar
# nginx (82.39.213.9.nip.io) allaqachon "/" yo'lini shu botning PORT'iga (8000)
# proxy_pass qilib qo'ygan va Certbot SSL sertifikati bilan sozlangan.
WEBHOOK_HOST = "https://YOUR_SERVER_HOST"
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
WEBAPP_HOST = os.getenv("WEBAPP_HOST", "0.0.0.0")  # 0.0.0.0 for Railway/Docker/Cloud containers
WEBAPP_PORT = int(PORT)
local_server = TelegramAPIServer.from_base("http://localhost:8081")
dp = Dispatcher()
# dp.message.middleware(DefineUserLangMiddleware())
# dp.callback_query.middleware(DefineUserLangMiddleware())

async def startup(bot: Bot):
    await bot.set_webhook(url=f"http://127.0.0.1:{PORT}/{TOKEN}")
    logging.info(f"Webhook o'rnatildi: {WEBHOOK_URL}")

async def shutdown(bot: Bot):
    i = 0
    for chat in await Chat.all():
        try: await bot.send_message(chat.chat_id, "❗️ <b>Bot yangilanmoqda!</b> Agar o'yin bo'layotgan bo'lsa, bot yongach, /stop qilib qayta boshlashingizni so'raymiz!", parse_mode="HTML")
        except: continue
        await sleep(0.1)
        print(f"{i}-chat")
        i += 1

async def kunlik_tasks(bot: Bot):
    while True:
        await daily_balance_task(bot)
        await sleep(86400)

async def nft_catalog_autosync_task():
    """Telegramning sovg'a katalogini har soatda avtomatik qayta sinxronlaydi —
    yangi chiqqan yoki qayta to'ldirilgan sovg'alar qo'lda bosmasdan paydo bo'lishi uchun."""
    from utils.nft_userbot import sync_catalog
    while True:
        try:
            await sync_catalog()
        except Exception as e:
            logging.debug(f"NFT katalog avto-sinxronlash: {e}")
        await sleep(3600)


import logging

@dp.message.outer_middleware()
async def log_all_messages(handler, event, data):
    logging.info(f"RECEIVED MESSAGE: {event.text} from {event.from_user.id} in chat {event.chat.id}")
    return await handler(event, data)

from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

async def main():
    api_server_url = os.getenv("TELEGRAM_API_SERVER")
    proxy_url = os.getenv("TELEGRAM_PROXY") or os.getenv("PROXY")
    
    if api_server_url:
        custom_server = TelegramAPIServer.from_base(api_server_url)
        session = AiohttpSession(api=custom_server, proxy=proxy_url) if proxy_url else AiohttpSession(api=custom_server)
        logging.info(f"Custom Telegram API server bilan ulanmoqda: {api_server_url}")
    elif proxy_url:
        session = AiohttpSession(proxy=proxy_url)
        logging.info(f"Proxy orqali ulanmoqda: {proxy_url}")
    else:
        session = None

    if session:
        bot = Bot(token=TOKEN, session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    else:
        bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    basicConfig(level=INFO)
    logging.getLogger("telethon").setLevel(logging.WARNING)
    await database.init()

    # Guruhlar uchun komandalar
    group_commands = [
        BotCommand(command="start", description="O'yinni boshlash"),
        BotCommand(command="game", description="O'yin yaratish"),
        BotCommand(command="vsgame", description="Jamoaviy o'yin yaratish"),
        BotCommand(command="roles", description="O'yin rollarini ko'rish"),
        BotCommand(command="lang", description="Tilni tanlash / Язык / Language"),
        BotCommand(command="leave", description="O'yindan chiqish"),
        BotCommand(command="sozlamalar", description="O'yin sozlamalarini shaxsiyda ochish"),
        BotCommand(command="stop", description="O'yinni to'xtatish"),
        BotCommand(command="extend", description="O'yin vaqtini uzaytirish"),
    ]
    # Foydalanuvchilar (shaxsiy chat) uchun komandalar
    private_commands = [
        BotCommand(command="start", description="O'yinni boshlash"),
        BotCommand(command="profile", description="Profilingizni ko'rish (Shaxsiy chatda)"),
        BotCommand(command="roles", description="O'yin rollarini ko'rish"),
        BotCommand(command="lang", description="Tilni tanlash / Язык / Language"),
    ]
    admin_commands = [
        BotCommand(command="start", description="O'yinni boshlash"),
        BotCommand(command="profile", description="Profilingizni ko'rish (Shaxsiy chatda)"),
        BotCommand(command="roles", description="O'yin rollarini ko'rish"),
        BotCommand(command="lang", description="Tilni tanlash / Язык / Language"),
        BotCommand(command="groups", description="Guruhlar ro'yxati"),
        BotCommand(command="tchat", description="Guruhlar reytingi"),
        BotCommand(command="boylar", description="Boylar ro'yxati"),
        BotCommand(command="blocks", description="Bloklanganlar ro'yxati"),
        BotCommand(command="vips", description="Vip userlar ro'yxati"),
        BotCommand(command="vipemoji", description="VIP emoji o'rnatish (reply orqali)"),
        BotCommand(command="geroys", description="Geroylar ro'yxati"),
    ]
    try:
        await bot.set_my_commands(private_commands, scope={"type": "default"})
        await bot.set_my_commands(group_commands, scope={"type": "all_group_chats"})
        for admin_id in ADMINS:
            try:
                await bot.set_my_commands(admin_commands, scope={"type": "chat", "chat_id": admin_id})
            except Exception:
                continue
        await bot.set_my_commands(private_commands, scope={"type": "all_private_chats"})
    except Exception as e:
        logging.warning(f"set_my_commands o'rnatishda tarmoq xatoligi (o'tkazib yuborildi): {e}")
    # dp.callback_query.middleware(MyThrottlingMiddleware())
    # dp.message.middleware(MyErrorHandler())
    # dp.startup.register(startup)
    # dp.shutdown.register(shutdown)
    dp.message.middleware(MyThrottlingMiddleware())
    dp.callback_query.middleware(MyThrottlingMiddleware())
    dp.message.middleware(GroupWriteGuardMiddleware())
    dp.include_router(router)
    create_task(kunlik_tasks(bot))
    create_task(long_games_attack(bot=bot))
    create_task(check_vip_users(bot=bot))
    create_task(nft_catalog_autosync_task())
    create_task(long_giveaways_cleanup(bot=bot))
    create_task(check_personal_birthday_gifts(bot=bot))
    try:
        from utils.game_logic import resume_active_games
        await resume_active_games(bot)
    except Exception as e:
        logging.error(f"resume_active_games error: {e}")
    try:
        await database.redis_client.ping()
        print("Redisga ulanish muvaffaqiyatli!")
    except Exception as e:
        print(f"Redis ulanmadi ({e})")
        try:
            import fakeredis.aioredis
            database.redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
            print("Lokal FakeRedis ishga tushirildi.")
        except Exception:
            pass
    use_polling = os.getenv("USE_POLLING", "false").lower() in ("true", "1", "yes")

    if use_polling:
        await bot.delete_webhook(drop_pending_updates=True)
        logging.info("Bot POLLING rejimida ishga tushdi...")
        
        # Webapp endpointlari uchun HTTP server
        app = web.Application(client_max_size=20 * 1024 * 1024)
        from utils.webapp_api import setup_webapp_routes
        setup_webapp_routes(app, static_dir=os.path.dirname(os.path.abspath(__file__)), bot=bot)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=WEBAPP_HOST, port=int(os.getenv("PORT", "8002")))
        await site.start()
        logging.info(f"Webapp serveri {WEBAPP_HOST}:{os.getenv('PORT', '8002')} da ishga tushdi")
        
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    else:
        await bot.set_webhook(
            url=WEBHOOK_URL,
            drop_pending_updates=True,
            allowed_updates=dp.resolve_used_update_types(),
        )
        logging.info(f"Webhook o'rnatildi: {WEBHOOK_URL}")

        # Standart client_max_size 1 MiB — rasm yuklash endpoint'lari ichidagi 18 MB tekshiruvidan
        # OLDIN har qanday oddiy telefon kamerasi rasmini rad etib yuborardi.
        app = web.Application(client_max_size=20 * 1024 * 1024)
        SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)

        from utils.webapp_api import setup_webapp_routes
        setup_webapp_routes(app, static_dir=os.path.dirname(os.path.abspath(__file__)), bot=bot)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=WEBAPP_HOST, port=WEBAPP_PORT)
        await site.start()
        logging.info(f"Webhook serveri {WEBAPP_HOST}:{WEBAPP_PORT} da ishga tushdi")

        await asyncio.Event().wait()

if __name__ == "__main__":
    run(main())