import asyncio
import random
from typing import List, Optional
from aiogram import Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from models.game_data import Game, GamePlayer, GamePhase, Chat
from models.user import User, Profile
from models.game_set import GameSetTime
from utils.role_names import RoleNames
from keyboards.game_keyboard import join_game_button, go_group_button
from keyboards.main_keyboard import bot_link_markup

from utils.premium_emojis import role_display

# Redis-based game handlers dan import va fallback
try:
    from utils.redis_game.handlers import (
        create_game_handler_redis as create_game_handler,
        create_vs_game_handler_redis as create_vs_game_handler,
        join_game_handler_redis as join_game_handler,
        kick_player_redis as kick_player,
        leave_game_redis as leave_game,
        stop_game_handler_redis as stop_game_handler,
        start_game_handler_redis as start_game_handler,
    )
except ImportError:
    async def create_game_handler(message: Message, bot: Bot):
        await message.answer("🎮 O'yin yaratish boshlandi!", reply_markup=await join_game_button(message.chat.id))

    async def create_vs_game_handler(message: Message, bot: Bot):
        await message.answer("⚔️ VS O'yin yaratildi!")

    async def join_game_handler(message: Message, bot: Bot, state: FSMContext):
        await message.answer("✅ O'yinga qo'shildingiz!")

    async def kick_player(message: Message, bot: Bot):
        await message.answer("👢 O'yinchi chiqarib yuborildi.")

    async def leave_game(message: Message, bot: Bot):
        await message.answer("🚪 O'yindan chiqdingiz.")

    async def stop_game_handler(message: Message, bot: Bot):
        await message.answer("🛑 O'yin to'xtatildi.")

    async def start_game_handler(message: Message, bot: Bot, state: FSMContext):
        await message.answer("🎲 O'yin boshlandi!")


async def safe_send_message(bot: Bot, chat_id: int, text: str, reply_markup=None, parse_mode: str = "HTML") -> Optional[Message]:
    """Xabarni xavfsiz yuborish (bloklangan bo'lsa xatoni yutib yuboradi)"""
    try:
        return await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        return None


async def resume_active_games(bot: Bot):
    """Bot qayta yoqilganda barcha to'xtab qolgan faol o'yinlarni fazasidan davom ettirish."""
    from datetime import datetime, timezone
    from utils.database import redis_client as r
    from utils.redis_game.game_models_crud import game_repo
    from utils.redis_game.repositories.player_repository import player_repository as player_repo
    from utils.redis_game.win_conditions import cleanup_game_redis
    from utils.redis_game.handlers import starting_game_redis

    try:
        active_game_ids = set()

        # 1. global:active_games dan olish
        try:
            g_active = await r.smembers("global:active_games")
            for gid_raw in g_active:
                gid_str = gid_raw.decode() if isinstance(gid_raw, bytes) else str(gid_raw)
                if gid_str and gid_str.isdigit():
                    active_game_ids.add(int(gid_str))
        except Exception as ge:
            print(f"⚠️ global:active_games scan xatosi: {ge}")

        # 2. chat:*:active_games orqali tekshirish
        try:
            cursor = 0
            while True:
                cursor, keys = await r.scan(cursor, match="chat:*:active_games", count=100)
                for k in keys:
                    key_str = k.decode() if isinstance(k, bytes) else str(k)
                    members = await r.smembers(key_str)
                    for m in members:
                        m_str = m.decode() if isinstance(m, bytes) else str(m)
                        if m_str and m_str.isdigit():
                            active_game_ids.add(int(m_str))
                if cursor == 0:
                    break
        except Exception as ce:
            print(f"⚠️ chat:*:active_games scan xatosi: {ce}")

        # 3. game:*:state orqali ham tekshirish
        try:
            cursor = 0
            while True:
                cursor, keys = await r.scan(cursor, match="game:*:state", count=100)
                for k in keys:
                    key_str = k.decode() if isinstance(k, bytes) else str(k)
                    parts = key_str.split(":")
                    if len(parts) == 3 and parts[1].isdigit():
                        active_game_ids.add(int(parts[1]))
                if cursor == 0:
                    break
        except Exception as se:
            print(f"⚠️ game:*:state scan xatosi: {se}")

        print(f"🔄 Redisda topilgan potentsial o'yinlar: {len(active_game_ids)} ta")

        resumed_count = 0
        for gid in active_game_ids:
            try:
                game_state = await game_repo.load_game(gid)
                if not game_state or not game_state.is_active:
                    continue

                # Agar o'yin kutish (lobby) rejimida bo'lsa
                if game_state.phase == "waiting":
                    # Agar 3 soatdan oshib ketgan bo'lsa, eskirgan deb tozalaymiz
                    time_diff = (datetime.now(timezone.utc) - game_state.created_at).total_seconds()
                    if time_diff > 10800:
                        await cleanup_game_redis(str(gid))
                    continue

                # Agar o'yin tun yoki kun fazasida bo'lsa
                if game_state.phase in ("night", "day"):
                    players = await player_repo.get_alive_players(gid)
                    if len(players) < 2:
                        await cleanup_game_redis(str(gid))
                        continue

                    # Concurrency check
                    is_running = await r.get(f"game:{gid}:loop_active")
                    if is_running:
                        continue

                    print(f"▶️ O'yin tiklanmoqda: Game ID={gid}, Chat ID={game_state.chat_id}, Phase={game_state.phase}")
                    asyncio.create_task(
                        starting_game_redis(
                            game_id=str(gid),
                            message=None,
                            bot=bot,
                            start=False,
                            is_resumed=True
                        )
                    )
                    resumed_count += 1
            except Exception as item_err:
                print(f"⚠️ O'yin {gid} ni tiklashda xatolik: {item_err}")

        print(f"✅ Muvaffaqiyatli tiklangan o'yinlar soni: {resumed_count} ta")
    except Exception as e:
        print(f"⚠️ Active games resume xatosi: {e}")


async def assign_new_role(player: GamePlayer, phase: GamePhase, bot: Bot, chat: Chat):
    """Joker yoki Aktyor uchun yangi rol berish"""
    new_role = RoleNames.FUQARO
    player.role = new_role
    await player.save()
    await safe_send_message(
        bot,
        player.user.user_id,
        f"🎭 Sizning yangi rolingiz: {role_display(new_role)} ({new_role})"
    )


async def handle_vote_like(call: CallbackQuery, bot: Bot, state: FSMContext):
    """Sud ovoz berish jarayonida Like/Dislike qabul qilish"""
    action = "like" if "like" in call.data else "dislike"
    await call.answer(f"👍 Ovoz qabul qilindi: {action.upper()}", show_alert=True)


async def create_nick_game_handler(message: Message, bot: Bot):
    """Laqabli/Maxsus nomli o'yin yaratish"""
    await create_game_handler(message, bot)


async def extend_game_timer(message: Message, bot: Bot):
    """O'yin registratsiya vaqtini (120s) bekor qilib cheksizga uzaytirish"""
    from utils.i18n import get_chat_lang, clean_lang
    from utils.redis_game.repositories import game_repository
    from utils.database import redis_client as r

    lang = clean_lang(await get_chat_lang(message.chat.id))
    active_game_id = await game_repository.get_active_game(message.chat.id)

    if active_game_id:
        game_state = await game_repository.load_game(active_game_id)
        if game_state and game_state.phase == "waiting":
            await r.set(f"game:{active_game_id}:is_extended", "1", ex=86400)
            await r.delete(f"game:{active_game_id}:reg_expires_at")

            text_map = {
                "uz": "⏱ <b>Taymer cheksiz qilib belgilandi!</b>",
                "ru": "⏱ <b>Таймер установлен на бессрочно!</b>",
                "en": "⏱ <b>Timer set to unlimited!</b>",
                "tr": "⏱ <b>Zamanlayıcı süresiz olarak ayarlandı!</b>",
                "kk": "⏱ <b>Таймер шексіздікке орнатылды!</b>"
            }
            await message.answer(text_map.get(lang, text_map["uz"]), parse_mode="HTML")
            return

    text_map = {
        "uz": "⚠️ Hozirda kutish rejimida faol o'yin topilmadi!",
        "ru": "⚠️ В настоящее время активная игра в режиме ожидания не найдена!",
        "en": "⚠️ No active game in waiting mode found!",
        "tr": "⚠️ Bekleme modunda aktif oyun bulunamadı!",
        "kk": "⚠️ Күту режимінде белсенді ойын табылмады!"
    }
    await message.answer(text_map.get(lang, text_map["uz"]), parse_mode="HTML")


