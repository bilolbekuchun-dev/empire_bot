"""
Game phase handlers for Redis-based game.
Bu modul o'yin fazalarini (night, day) boshqaradi.
"""
import html
import asyncio
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.types import Message

from config import BOT_URL, tinch_rollar, mafia_rollar, yakka_rollar
from models.game_data import Chat
from models.game_set import GameSetTime, GameSetWeapons, GroupMoreSet
from models.user import User
from utils.redis_game.repositories.game_repository import game_repository as game_repo
from keyboards.main_keyboard import bot_link_markup
from utils.premium_emojis import role_display
from utils.database import redis_client as r


def _player_mention_label(uid, user, player) -> str:
    if user and user.mention:
        return user.mention
    name = html.escape(
        (user.full_name if user and user.full_name else getattr(player, "first_name", None))
        or "O'yinchi"
    )
    return f'<a href="tg://user?id={uid}">{name}</a>' if uid else name


async def _alive_players_text(players: list, *, dawn: bool = False) -> str:
    """Tirik o'yinchilar ro'yxati. Tongda rollar guruhi ham chiqadi."""
    lines = ["<b>Tirik o'yinchilar:</b>"]
    user_ids = [p.user_id for p in players if getattr(p, "user_id", None)]
    users = {}
    vips = {}
    if user_ids:
        from models.user import VipUser
        for user in await User.filter(user_id__in=list(set(user_ids))):
            users[user.user_id] = user
        for vip in await VipUser.filter(user__user_id__in=list(set(user_ids))):
            vips[vip.user_id] = vip

    numbered = []
    for idx, player in enumerate(players, 1):
        num = getattr(player, "maxsus_raqam", None) or idx
        numbered.append((int(num), player))
    numbered.sort(key=lambda x: x[0])

    for num, player in numbered:
        uid = getattr(player, "user_id", None)
        vip = vips.get(uid)
        vip_prefix = f"{vip.emoji_char} " if (vip and vip.emoji_char) else ""
        lines.append(f"{num}. {vip_prefix}{_player_mention_label(uid, users.get(uid), player)}")

    if not dawn:
        return "\n".join(lines)

    tinch_set, mafia_set, yakka_set = set(tinch_rollar), set(mafia_rollar), set(yakka_rollar)
    tinch = [p for p in players if p.role in tinch_set]
    mafia = [p for p in players if p.role in mafia_set]
    yakka = [p for p in players if p.role in yakka_set]
    leftover = [p for p in players if p.role not in tinch_set | mafia_set | yakka_set]
    yakka.extend(leftover)

    def faction_block(title: str, group: list) -> list:
        if not group:
            return []
        block = [f"\n<b>{title} - {len(group)}:</b>"]
        for p in group:
            block.append(role_display(p.role))
        return block

    lines.append("")
    lines.extend(faction_block("Tinchlar", tinch))
    lines.extend(faction_block("Mafiyalar", mafia))
    lines.extend(faction_block("Yakkalar", yakka))
    lines.append(f"\n<b>Jami:</b> {len(players)} ta")
    lines.append("\nEndi kechaning natijalarini muhokama qilamiz...")
    return "\n".join(lines)


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
        phase_num=night_number,
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
    
    # Night presentation (state transitioned + persisted by the caller first).
    # Idempotent + failure-isolated: never raises into the game loop.
    try:
        from utils.redis_game.presentation import send_night_presentation
        await send_night_presentation(
            bot, chat.chat_id, int(game_id), night_number,
            reply_markup=bot_link_markup,
        )
    except Exception as e:
        print(f"Tungi taqdimotni yuborishda xato: {e}")
    
    try:
        await r.set(f"game:{game_id}:night_num", str(night_number), ex=86400)
    except Exception:
        pass

    # Show players list
    try:
        players_text = await _alive_players_text(players)
        players_text += f"\n\nTonggacha ⏳ {game_times.night_time} sekund qoldi"
        await bot.send_message(chat.chat_id, players_text, parse_mode="HTML", reply_markup=bot_link_markup)
    except Exception as e:
        print(f"O'yinchilar ro'yxatini ko'rsatishda xato: {e}")
    
    # Night actions - har bir o'yinchiga rol bo'yicha tugma yuborish
    try:
        from utils.redis_game.night_engine import send_night_actions
        await send_night_actions(int(game_id), night_number, players, bot, chat)
    except Exception as e:
        print(f"Tungi harakatlarni yuborishda xato: {e}")
    
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
    
    # Day dawn presentation is emitted when the game actually enters the "day"
    # phase (execute_day_phase_redis), i.e. AFTER the state transition is
    # persisted -- not here. See utils/redis_game/presentation.py.
    
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
        phase_num=day_number,
        phase_type="morning",
        is_end=False,
        created_at=datetime.now(timezone.utc)
    )

    # Day presentation (state transitioned + persisted by the caller first).
    # Idempotent + failure-isolated: never raises into the game loop.
    try:
        from utils.redis_game.presentation import send_day_presentation
        await send_day_presentation(bot, chat.chat_id, int(game_id), day_number)
    except Exception as e:
        print(f"Kunni taqdim etishda xato: {e}")

    # TO'G'RI NAVBAT: 1) tong habari (yuborildi) → 2) tunda o'lganlar → 3) tirik o'yinchilar
    try:
        from utils.redis_game.night_engine import flush_pending_deaths
        await flush_pending_deaths(int(game_id), bot, chat)
    except Exception as e:
        print(f"Tunda o'lganlar xabarini yuborishda xato: {e}")

    # Check paralar
    if paralar and "para" in (await game_repo.load_game(game_id)).mode:
        # TODO: check_paralar_lst_redis
        pass
    
    # Get settings
    more_set, _ = await GroupMoreSet.get_or_create(chat_id=chat.chat_id)
    weapons_set, _ = await GameSetWeapons.get_or_create(chat_id=chat.chat_id)
    
    # Show players list
    try:
        players_text = await _alive_players_text(players, dawn=True)
        await bot.send_message(chat.chat_id, players_text, parse_mode="HTML", disable_web_page_preview=True)
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
    vote_url = BOT_URL if BOT_URL and BOT_URL.startswith("http") else "https://t.me/Empire_testbot"
    await bot.send_message(
        chat.chat_id,
        f"<b>Aybdorlarni aniqlash va jazolash vaqti keldi.</b>\nOvoz berish uchun {game_times.vote_time} sekund\n<a href='{vote_url}'>Ovoz berish</a>",
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
        phase_num=day_number,
        phase_type="day",
        is_end=False,
        created_at=datetime.now(timezone.utc)
    )
    
    # Check paralar
    if paralar and "para" in (await game_repo.load_game(game_id)).mode:
        # TODO: check_paralar_lst_redis
        pass
    
    # Wait for voting
    await asyncio.sleep(game_times.vote_time)
    
    # Check if game is still active
    game_state = await game_repo.load_game(game_id)
    if not game_state or not game_state.is_active:
        return

    # Ovozlarni sanab, like/dislike orqali osishni qo'llash
    try:
        from utils.redis_game.night_engine import process_day_votes
        await process_day_votes(
            int(game_id), day_number, players, bot, chat,
            like_time=int(getattr(game_times, "like_time", 30) or 0),
        )
    except Exception as e:
        print(f"Ovozlarni qayta ishlashda xato: {e}")
    
    # Mark day phase as ended
    day_phase.is_end = True
    
    # Create afternoon phase
    afternoon_phase = GamePhaseState(
        game_id=game_id,
        phase_num=day_number,
        phase_type="afternoon",
        is_end=False,
        created_at=datetime.now(timezone.utc)
    )
    
    # Check joker card selection
    # TODO: joker_card_check_redis
    
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
