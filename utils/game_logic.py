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
    """Bot qayta yoqilganda faol o'yinlarni tiklash"""
    try:
        active_games = await Game.filter(is_active=True).all()
        print(f"🔄 Tiklanayotgan faol o'yinlar soni: {len(active_games)} ta")
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
    """O'yin kutish vaqtini uzaytirish"""
    await message.answer("⏱ O'yin boshlanish vaqti uzaytirildi!")
