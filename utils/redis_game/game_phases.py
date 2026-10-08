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


async def _alive_players_text(players: list, *, dawn: bool = False, lang: str = "uz") -> str:
    """Tirik o'yinchilar ro'yxati. Tongda rollar guruhi ham chiqadi."""
    from utils.i18n import clean_lang
    lang = clean_lang(lang)

    headers = {
        "uz": "<b>Tirik o'yinchilar:</b>",
        "ru": "<b>Живые игроки:</b>",
        "en": "<b>Surviving players:</b>",
        "tr": "<b>Hayatta kalan oyuncular:</b>"
    }
    lines = [headers.get(lang, headers["uz"])]
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

    faction_labels = {
        "uz": {"tinch": "Tinchlar", "mafia": "Mafiyalar", "yakka": "Yakkalar", "total": "Jami", "total_unit": "ta", "footer": "\nEndi kechaning natijalarini muhokama qilamiz..."},
        "ru": {"tinch": "Мирные", "mafia": "Мафия", "yakka": "Одиночки", "total": "Всего", "total_unit": "чел.", "footer": "\nОбсуждаем результаты ночи..."},
        "en": {"tinch": "Townsfolk", "mafia": "Mafia", "yakka": "Neutrals", "total": "Total", "total_unit": "players", "footer": "\nDiscussing night results..."},
        "tr": {"tinch": "Siviller", "mafia": "Mafya", "yakka": "Tarafsızlar", "total": "Toplam", "total_unit": "oyuncu", "footer": "\nGecenin sonuçlarını tartışıyoruz..."}
    }
    lbls = faction_labels.get(lang, faction_labels["uz"])

    def faction_block(title: str, group: list) -> list:
        if not group:
            return []
        roles_str = ", ".join(role_display(p.role, lang=lang) for p in group)
        return [f"\n<b>{title} - {len(group)}:</b> {roles_str}"]

    lines.append("")
    lines.extend(faction_block(lbls["tinch"], tinch))
    lines.extend(faction_block(lbls["mafia"], mafia))
    lines.extend(faction_block(lbls["yakka"], yakka))
    lines.append(f"\n<b>{lbls['total']}:</b> {len(players)} {lbls['total_unit']}")
    lines.append(lbls["footer"])
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
    """
    from utils.redis_game.game_models_schema import GamePhaseState
    
    night_phase = GamePhaseState(
        game_id=game_id,
        phase_num=night_number,
        phase_type="night",
        is_end=False,
        created_at=datetime.now(timezone.utc)
    )
    
    if paralar and "para" in (await game_repo.load_game(game_id)).mode:
        pass
    
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
        from utils.i18n import get_chat_lang
        chat_lang = await get_chat_lang(chat.chat_id)
        players_text = await _alive_players_text(players, lang=chat_lang)

        timer_texts = {
            "uz": f"\n\nTonggacha ⏳ {game_times.night_time} sekund qoldi",
            "ru": f"\n\nДо рассвета осталось ⏳ {game_times.night_time} сек.",
            "en": f"\n\n⏳ {game_times.night_time} seconds until dawn",
            "tr": f"\n\nŞafağa ⏳ {game_times.night_time} saniye kaldı"
        }
        players_text += timer_texts.get(chat_lang, timer_texts["uz"])
        await bot.send_message(chat.chat_id, players_text, parse_mode="HTML", reply_markup=bot_link_markup)
    except Exception as e:
        print(f"O'yinchilar ro'yxatini ko'rsatishda xato: {e}")
    
    try:
        from utils.redis_game.night_engine import send_night_actions
        await send_night_actions(int(game_id), night_number, players, bot, chat)
    except Exception as e:
        print(f"Tungi harakatlarni yuborishda xato: {e}")
    
    # Dynamic early-finish night timer loop: hamma faol rol harakatini bajarsa darhol tong otadi
    exp_key = f"game:{game_id}:night:{night_number}:expected_users"
    comp_key = f"game:{game_id}:night:{night_number}:completed_users"
    total_seconds = int(getattr(game_times, "night_time", 45))

    for elapsed in range(total_seconds):
        await asyncio.sleep(1)
        g_check = await game_repo.load_game(game_id)
        if not g_check or not g_check.is_active:
            return
        try:
            exp_raw = await r.smembers(exp_key)
            if exp_raw is not None:
                exp_set = {x.decode() if isinstance(x, bytes) else str(x) for x in exp_raw}
                if not exp_set and elapsed >= 3:
                    break
                comp_raw = await r.smembers(comp_key)
                comp_set = {x.decode() if isinstance(x, bytes) else str(x) for x in comp_raw} if comp_raw else set()
                if exp_set and exp_set.issubset(comp_set):
                    await asyncio.sleep(1)
                    break
        except Exception:
            pass

    game_state = await game_repo.load_game(game_id)
    if not game_state or not game_state.is_active:
        return
    
    try:
        from utils.redis_game.night_engine import process_night_results
        await process_night_results(int(game_id), night_number, players, bot, chat)
    except Exception as e:
        print(f"Tungi natijalarni qo'llashda xato: {e}")
    
    night_phase.is_end = True


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
    """
    from utils.redis_game.game_models_schema import GamePhaseState
    
    morning_phase = GamePhaseState(
        game_id=game_id,
        phase_num=day_number,
        phase_type="morning",
        is_end=False,
        created_at=datetime.now(timezone.utc)
    )

    try:
        from utils.redis_game.presentation import send_day_presentation
        await send_day_presentation(bot, chat.chat_id, int(game_id), day_number)
    except Exception as e:
        print(f"Kunni taqdim etishda xato: {e}")

    try:
        from utils.redis_game.night_engine import flush_pending_deaths
        await flush_pending_deaths(int(game_id), bot, chat)
    except Exception as e:
        print(f"Tunda o'lganlar xabarini yuborishda xato: {e}")

    if paralar and "para" in (await game_repo.load_game(game_id)).mode:
        pass
    
    more_set, _ = await GroupMoreSet.get_or_create(chat_id=chat.chat_id)
    weapons_set, _ = await GameSetWeapons.get_or_create(chat_id=chat.chat_id)
    
    # Show players list
    try:
        from utils.i18n import get_chat_lang
        chat_lang = await get_chat_lang(chat.chat_id)
        players_text = await _alive_players_text(players, dawn=True, lang=chat_lang)
        await bot.send_message(chat.chat_id, players_text, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        print(f"O'yinchilar ro'yxatini ko'rsatishda xato: {e}")
    
    if weapons_set.geroy:
        try:
            pass
        except Exception as e:
            print(f"Geroy xabarini yuborishda xato: {e}")
    
    await asyncio.sleep(game_times.day_time)
    
    game_state = await game_repo.load_game(game_id)
    if not game_state or not game_state.is_active:
        return
    
    morning_phase.is_end = True
    
    if "para" not in (await game_repo.load_game(game_id)).mode:
        try:
            pass
        except Exception as e:
            print(f"Geroy natijalarini ko'rsatishda xato: {e}")
    
    # Voting message
    vote_url = BOT_URL if BOT_URL and BOT_URL.startswith("http") else "https://t.me/Empire_testbot"
    from utils.i18n import get_chat_lang
    chat_lang = await get_chat_lang(chat.chat_id)
    vote_texts = {
        "uz": f"<b>Aybdorlarni aniqlash va jazolash vaqti keldi.</b>\nOvoz berish uchun {game_times.vote_time} sekund\n<a href='{vote_url}'>Ovoz berish</a>",
        "ru": f"<b>Время найти и наказать виновных.</b>\nНа голосование даётся {game_times.vote_time} сек.\n<a href='{vote_url}'>Голосовать</a>",
        "en": f"<b>It is time to find and punish the guilty.</b>\nVoting time: {game_times.vote_time} seconds\n<a href='{vote_url}'>Vote</a>",
        "tr": f"<b>Suçluları bulma ve cezalandırma zamanı.</b>\nOy verme süresi: {game_times.vote_time} saniye\n<a href='{vote_url}'>Oy Ver</a>"
    }
    await bot.send_message(
        chat.chat_id,
        vote_texts.get(chat_lang, vote_texts["uz"]),
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
