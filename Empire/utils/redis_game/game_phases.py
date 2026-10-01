"""
Game phase handlers for Redis-based game.
Bu modul o'yin fazalarini (night, day) boshqaradi.
"""
from aiogram import Bot
from aiogram.types import Message
from datetime import datetime, timezone
from models.game_data import Chat
from models.game_set import GameSetTime, GameSetWeapons, GroupMoreSet
from utils.redis_game.repositories.game_repository import game_repository as game_repo
from utils.redis_game.repositories.player_repository import player_repository as player_repo
from keyboards.main_keyboard import bot_link_markup
from utils.role_names import RoleNames
import asyncio


async def execute_night_phase_redis(
    game_id: str,
    night_number: int,
    players: list,
    bot: Bot,
    chat: Chat,
    message: Message,
    game_times: GameSetTime,
    paralar=None
):
    """
    Tun fazasini amalga oshirish.
    
    Args:
        game_id: O'yin ID
        night_number: Tun raqami
        players: Tirik o'yinchilar ro'yxati
        bot: Bot instance
        chat: Chat object
        message: Message object
        game_times: O'yin vaqt sozlamalari
        paralar: Para rejimi uchun
    """
    from utils.redis_game.game_models_schema import GamePhaseState
    
    # Create night phase
    night_phase = GamePhaseState(
        game_id=game_id,
        number=night_number,
        phase_type="night",
        is_end=False,
        created_at=datetime.now(timezone.utc)
    )
    
    # TODO: Save phase to Redis
    # await phase_repo.save_phase(night_phase)
    
    # Check paralar (agar para mode bo'lsa)
    if paralar and "para" in (await game_repo.load_game(game_id)).mode:
        # TODO: check_paralar_lst_redis
        pass
    
    # Send night message
    await bot.send_photo(
        chat_id=chat.chat_id,
        photo="https://i2.paste.pics/20ba68d2f84c3ca290a6bdac678b3f72.png",
        caption="🌚 🌃<b>Tun</b>\nKo'chaga faqat jasur va qo'rqmas odamlar chiqishdi. Ertalab tirik qolganlarni sanaymiz...",
        parse_mode="HTML",
        reply_markup=bot_link_markup
    )
    
    # Show players list
    try:
        # TODO: view_players_list_redis
        players_text = f"<b>Tirik o'yinchilar:</b>\n"
        for i, player in enumerate(players, 1):
            players_text += f"{i}. O'yinchi\n"  # Placeholder
        players_text += f"\nTonggacha ⏳ {game_times.night_time} sekund qoldi"
        await bot.send_message(chat.chat_id, players_text, parse_mode="HTML", reply_markup=bot_link_markup)
    except Exception as e:
        print(f"O'yinchilar ro'yxatini ko'rsatishda xato: {e}")
    
    # Night actions - har bir o'yinchiga rol bo'yicha tugma yuborish
    try:
        from utils.redis_game.night_engine import send_night_actions
        await send_night_actions(int(game_id), night_number, players, bot, chat)
    except Exception as e:
        print(f"Tungi harakatlarni yuborishda xato: {e}")
    await bot.send_message(chat.chat_id, "⏳ Tungi harakatlar boshlandi...")
    
    # Wait for night time
    await asyncio.sleep(game_times.night_time)
    
    # Check if game is still active
    game_state = await game_repo.load_game(game_id)
    if not game_state or not game_state.is_active:
        return
    
    # Apply night results (o'ldirish/davolash/himoya/tekshiruv)
    try:
        from utils.redis_game.night_engine import process_night_results
        await process_night_results(int(game_id), night_number, players, bot, chat)
    except Exception as e:
        print(f"Tungi natijalarni qo'llashda xato: {e}")
    
    # Morning message
    await bot.send_photo(
        chat_id=chat.chat_id,
        photo="https://i2.paste.pics/3b5539fcec39e34050bc1365701a66b7.png",
        caption=f"Xayrli tong🌝\n🌄<b>Kun</b>: {night_number}\nShamollar tundagi mish-mishlarni butun shaharga yetkazmoqda..",
        parse_mode="HTML",
    )
    
    # Show night results
    try:
        # TODO: view_night_results_redis
        await bot.send_message(chat.chat_id, "📊 Tungi natijalar ko'rsatilmoqda...")
    except Exception as e:
        print(f"Tungi natijalarni ko'rsatishda xato: {e}")
    
    # Mark phase as ended
    night_phase.is_end = True
    # TODO: await phase_repo.save_phase(night_phase)


async def execute_day_phase_redis(
    game_id: str,
    day_number: int,
    players: list,
    bot: Bot,
    chat: Chat,
    message: Message,
    game_times: GameSetTime,
    paralar=None
):
    """
    Kun fazasini amalga oshirish.
    
    Args:
        game_id: O'yin ID
        day_number: Kun raqami
        players: Tirik o'yinchilar ro'yxati
        bot: Bot instance
        chat: Chat object
        message: Message object
        game_times: O'yin vaqt sozlamalari
        paralar: Para rejimi uchun
    """
    from utils.redis_game.game_models_schema import GamePhaseState
    
    # Create morning phase
    morning_phase = GamePhaseState(
        game_id=game_id,
        number=day_number,
        phase_type="morning",
        is_end=False,
        created_at=datetime.now(timezone.utc)
    )
    
    # Check paralar
    if paralar and "para" in (await game_repo.load_game(game_id)).mode:
        # TODO: check_paralar_lst_redis
        pass
    
    # Get settings
    more_set, _ = await GroupMoreSet.get_or_create(chat_id=chat.chat_id)
    weapons_set, _ = await GameSetWeapons.get_or_create(chat_id=chat.chat_id)
    
    # Show players list with roles
    try:
        # TODO: view_players_list_redis with roles
        players_text = f"<b>Tirik o'yinchilar:</b>\n"
        for i, player in enumerate(players, 1):
            players_text += f"{i}. O'yinchi\n"  # Placeholder
        players_text += "\nEndi kechaning natijalarini muhokama qilamiz..."
        await bot.send_message(chat.chat_id, players_text, parse_mode="HTML")
    except Exception as e:
        print(f"O'yinchilar ro'yxatini ko'rsatishda xato: {e}")
    
    # Geroy actions (if enabled)
    if weapons_set.geroy:
        try:
            # TODO: send_geroys_action_message_redis
            pass
        except Exception as e:
            print(f"Geroy xabarini yuborishda xato: {e}")
    
    # Wait for day discussion
    await asyncio.sleep(game_times.day_time)
    
    # Check if game is still active
    game_state = await game_repo.load_game(game_id)
    if not game_state or not game_state.is_active:
        return
    
    # Mark morning phase as ended
    morning_phase.is_end = True
    
    # Geroy action results
    if "para" not in (await game_repo.load_game(game_id)).mode:
        try:
            # TODO: geroys_action_result_redis
            pass
        except Exception as e:
            print(f"Geroy natijalarini ko'rsatishda xato: {e}")
    
    # Voting message
    await bot.send_message(
        chat.chat_id,
        f"<b>Aybdorlarni aniqlash va jazolash vaqti keldi.</b>\nOvoz berish uchun {game_times.vote_time} sekund\n<a href='https://T.me/Empire_testbot'>Ovoz berish</a>",
        parse_mode="HTML",
        reply_markup=bot_link_markup,
        disable_web_page_preview=True
    )

    # Ovoz berish tugmalarini yuborish
    try:
        from utils.redis_game.night_engine import send_day_votes
        await send_day_votes(int(game_id), day_number, players, bot, chat)
    except Exception as e:
        print(f"Ovoz tugmalarini yuborishda xato: {e}")
    
    # Create day voting phase
    day_phase = GamePhaseState(
        game_id=game_id,
        number=day_number,
        phase_type="day",
        is_end=False,
        created_at=datetime.now(timezone.utc)
    )
    
    # Check paralar
    if paralar and "para" in (await game_repo.load_game(game_id)).mode:
        # TODO: check_paralar_lst_redis
        pass
    
    # Day voting
    # TODO: day_action_redis
    await bot.send_message(chat.chat_id, "🗳 Ovoz berish boshlandi...")
    
    # Wait for voting
    await asyncio.sleep(game_times.vote_time)
    
    # Check if game is still active
    game_state = await game_repo.load_game(game_id)
    if not game_state or not game_state.is_active:
        return

    # Ovozlarni sanab, osishni qo'llash
    try:
        from utils.redis_game.night_engine import process_day_votes
        await process_day_votes(int(game_id), day_number, players, bot, chat)
    except Exception as e:
        print(f"Ovozlarni qayta ishlashda xato: {e}")
    
    # Mark day phase as ended
    day_phase.is_end = True
    
    # Create afternoon phase
    afternoon_phase = GamePhaseState(
        game_id=game_id,
        number=day_number,
        phase_type="afternoon",
        is_end=False,
        created_at=datetime.now(timezone.utc)
    )
    
    # Check joker card selection
    # TODO: joker_card_check_redis
    
    # Vote like action (hanging)
    try:
        # TODO: vote_like_action_redis
        await bot.send_message(chat.chat_id, "📊 Ovoz berish natijalari...")
    except Exception as e:
        print(f"Ovoz berish natijalarini ko'rsatishda xato: {e}")
    
    # Check if game is still active
    game_state = await game_repo.load_game(game_id)
    if not game_state or not game_state.is_active:
        return
    
    # Mark afternoon phase as ended
    afternoon_phase.is_end = True
    
    # Wake up sleeping player
    # TODO: wake_up_sleeping_player_redis
    
    # Check joker card selection penalty
    # TODO: joker_card_penalty_redis
