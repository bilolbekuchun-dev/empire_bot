"""
Win conditions checker for Redis-based game.
"""
import html
from datetime import datetime, timezone
from typing import Optional

from aiogram import Bot
from models.game_data import Chat
from models.user import User
from utils.redis_game.repositories.game_repository import game_repository as game_repo
from utils.redis_game.repositories.player_repository import player_repository as player_repo
from utils.database import redis_client as _redis
from utils.role_names import RoleNames
from utils.premium_emojis import role_display
from collections import defaultdict
from config import tinch_rollar as tinchlar, mafia_rollar as mafialar, yakka_rollar as yakkalar


# After a game ends its Redis records are kept briefly (so the final screen and
# any stats read them) and then auto-expire. Without a TTL the game state and
# player records of every finished game would live forever.
_ENDED_TTL = 86400


async def _clear_active_indexes(game_id, chat_id=None):
    """Remove a finished game from every active-game index (idempotent, best-effort).

    Without this, ended games leak forever in ``chat:{id}:active_games`` and the
    process-wide ``global:active_games`` set, making ``find_player_active_game``
    scan an ever-growing list of dead games.
    """
    try:
        if chat_id is None:
            game_state = await game_repo.load_game(game_id)
            chat_id = game_state.chat_id if game_state else None
        if chat_id is not None:
            await _redis.srem(f"chat:{chat_id}:active_games", str(game_id))
        await _redis.srem("global:active_games", str(game_id))
    except Exception:
        # Index cleanup must never break game ending.
        pass

async def check_win_conditions_redis(
    game_id: str,
    players: list,
    game_state,
    bot: Bot,
    chat: Chat
) -> bool:
    """
    O'yin tugash shartlarini tekshirish.
    
    Args:
        game_id: O'yin ID
        players: Tirik o'yinchilar ro'yxati
        game_state: O'yin holati
        bot: Bot instance
        chat: Chat object
    
    Returns:
        True - o'yin tugadi
        False - o'yin davom etadi
    """
    mode = game_state.mode
    
    # Categorize players by role
    
    
    # Categorize current players
    mafiyalar = [p for p in players if p.role in mafialar]
    fuqarolar = [p for p in players if p.role in tinchlar]
    yakka_taraflar = [p for p in players if p.role in yakkalar]
    qotil = [p for p in players if p.role == RoleNames.QOTIL]
    zombilar = [p for p in players if p.role == RoleNames.ZOMBI]
    
    # Handle SUIDSID special case
    suidsid_players = [p for p in players if p.role == RoleNames.SUIDSID]
    for suid in suidsid_players:
        if getattr(suid, 'osildi', False):
            mafiyalar.append(suid)
        else:
            fuqarolar.append(suid)
    
    # Check win conditions based on mode
    if mode == "real":
        return await check_real_mode_win(game_id, players, fuqarolar, mafiyalar, yakka_taraflar, bot, chat)
    
    elif "vsgame" in mode:
        return await check_vsgame_win(game_id, players, game_state, bot, chat)
    
    elif mode in ["zombie x classic 1", "zombie x super 1", "zombie x mega 1"]:
        return await check_zombie_mode_win(game_id, players, zombilar, yakkalar, fuqarolar, mafiyalar, qotil, bot, chat)
    
    elif mode in ["para x classic", "para x super", "para x mega"]:
        return await check_para_mode_win(game_id, players, bot, chat)
    
    elif mode in ["classic", "super", "mega"]:
        return await check_classic_mode_win(game_id, players, fuqarolar, mafiyalar, qotil, bot, chat)
    
    return False


async def check_real_mode_win(game_id, players, fuqarolar, mafiyalar, yakka_taraflar, bot, chat):
    """Real mode g'alabat shartlari."""
    # Faqat tinchlar qolgan (Mafia va Yakkalar yo'q bo'lsa)
    if len(players) > 0 and (len(players) == len(fuqarolar) or (len(mafiyalar) == 0 and len(yakka_taraflar) == 0)):
        await announce_game_result_redis(game_id, bot, chat, winner_roles=tinchlar, real_mode=True)
        return True
    
    # Faqat mafiyalar qolgan yoki Mafiyalar ustunligi
    if len(players) > 0 and (len(players) == len(mafiyalar) or (len(fuqarolar) == 0 and len(yakka_taraflar) == 0) or (len(mafiyalar) >= len(fuqarolar) and len(yakka_taraflar) == 0 and len(mafiyalar) > 0)):
        await announce_game_result_redis(game_id, bot, chat, winner_roles=mafialar, real_mode=True)
        return True
    
    # Faqat yakkalar qolgan
    if len(players) > 0 and (len(players) == len(yakka_taraflar) or (len(fuqarolar) == 0 and len(mafiyalar) == 0)):
        await announce_game_result_redis(game_id, bot, chat, winner_roles=yakkalar, real_mode=True)
        return True
    
    # 2 ta o'yinchi qolgan - special cases
    if len(players) == 2:
        player_1, player_2 = players[0], players[1]
        
        # Don vs non-Komissar
        if player_1.role == RoleNames.DON and player_2.role != RoleNames.KOMISSAR:
            await announce_game_result_redis(game_id, bot, chat, winner_roles=mafialar, real_mode=True)
            return True
        
        # Komissar vs non-Don
        if player_1.role == RoleNames.KOMISSAR and player_2.role != RoleNames.DON:
            await announce_game_result_redis(game_id, bot, chat, winner_roles=[RoleNames.KOMISSAR], real_mode=True)
            return True
        
        # Qotil vs anyone
        if RoleNames.QOTIL in [player_1.role, player_2.role]:
            await announce_game_result_redis(game_id, bot, chat, winner_roles=[RoleNames.QOTIL], real_mode=True)
            return True
    
    return False


async def check_vsgame_win(game_id, players, game_state, bot, chat):
    """VS game mode g'alaba shartlari."""
    teams = defaultdict(list)
    for player in players:
        teams[player.team].append(player)
    
    # Faqat bitta jamoa qolgan
    if len(teams) == 1 and players:
        winning_team = list(teams.keys())[0]
        winning_roles = list({p.role for p in teams[winning_team]})
        await announce_game_result_redis(
            game_id, bot, chat,
            winner_roles=winning_roles,
            vsgame=True,
            winning_team=winning_team
        )
        return True
    
    return False


async def check_zombie_mode_win(game_id, players, zombilar, yakkalar, fuqarolar, mafiyalar, qotil, bot, chat):
    """Zombie mode g'alaba shartlari."""
    # Barcha zombie bo'lib qolgan
    if len(zombilar) == len(players) and zombilar:
        await announce_game_result_redis(game_id, bot, chat, winner_roles=[RoleNames.ZOMBI], zombilar=True)
        return True
    
    # Yakkalar g'alaba qilgan (zombiesiz)
    if len(yakkalar) == len(players) and not zombilar:
        await announce_game_result_redis(game_id, bot, chat, winner_roles=[
            RoleNames.QOTIL, RoleNames.SUIDSID, RoleNames.QASOSKOR, RoleNames.GAZABDOR
        ])
        return True
    
    # Faqat qotil qolgan
    if not fuqarolar and not mafiyalar and qotil and not zombilar:
        await announce_game_result_redis(game_id, bot, chat, winner_roles=[
            RoleNames.QOTIL, RoleNames.SUIDSID, RoleNames.QASOSKOR, RoleNames.GAZABDOR
        ])
        return True
    
    # Qotil fuqaro va mafiyadan ko'proq
    if len(qotil) >= len(fuqarolar + mafiyalar) and not zombilar:
        await announce_game_result_redis(game_id, bot, chat, winner_roles=[
            RoleNames.QOTIL, RoleNames.SUIDSID, RoleNames.QASOSKOR, RoleNames.GAZABDOR
        ])
        return True
    
    # Tinchlar g'alaba qilgan
    if not check_mafialar_list(mafiyalar) and fuqarolar and not qotil and not zombilar:
        await announce_game_result_redis(game_id, bot, chat, winner_roles=tinchlar)
        return True
    
    # Mafiyalar g'alaba qilgan
    if len(mafiyalar) > len(fuqarolar) and mafiyalar and not qotil and not zombilar:
        await announce_game_result_redis(game_id, bot, chat, winner_roles=mafialar)
        return True
    
    return False


async def check_para_mode_win(game_id, players, bot, chat):
    """Para mode g'alaba shartlari."""
    from models.user import Paralar, User
    
    # 2 ta o'yinchi qolgan
    if len(players) == 2:
        user1 = await User.get(user_id=players[0].user_id)
        user2 = await User.get(user_id=players[1].user_id)
        
        # Para bor yoki yo'qligini tekshirish
        para = await Paralar.get_or_none(user1=user1, user2=user2)
        if not para:
            para = await Paralar.get_or_none(user1=user2, user2=user1)
        
        if para:
            await announce_game_result_redis(
                game_id, bot, chat,
                winner_roles=[players[0].role, players[1].role],
                para=True,
                para_winners=players
            )
            return True
    
    # 1 ta o'yinchi qolgan
    elif len(players) == 1:
        user1 = await User.get(user_id=players[0].user_id)
        para = await Paralar.get_or_none(user1=user1)
        if not para:
            para = await Paralar.get_or_none(user2=user1)
        
        if para:
            await announce_game_result_redis(
                game_id, bot, chat,
                winner_roles=[players[0].role],
                para=True,
                para_winners=[players[0]]
            )
            return True
    
    return False


async def check_classic_mode_win(game_id, players, fuqarolar, mafiyalar, qotil, bot, chat):
    """Classic/Super/Mega mode g'alaba shartlari."""
    # 1 ta o'yinchi qolgan
    if len(players) == 1:
        await announce_game_result_redis(game_id, bot, chat, winner_roles=[
            RoleNames.SUIDSID, RoleNames.QASOSKOR, RoleNames.GAZABDOR, players[0].role
        ])
        return True
    
    # Faqat qotil qolgan
    if not fuqarolar and not mafiyalar and qotil:
        await announce_game_result_redis(game_id, bot, chat, winner_roles=[
            RoleNames.QOTIL, RoleNames.SUIDSID, RoleNames.QASOSKOR, RoleNames.GAZABDOR
        ])
        return True
    
    # Qotil fuqaro va mafiyadan ko'proq yoki teng
    if qotil and len(qotil) >= len(fuqarolar + mafiyalar):
        await announce_game_result_redis(game_id, bot, chat, winner_roles=[
            RoleNames.QOTIL, RoleNames.SUIDSID, RoleNames.QASOSKOR, RoleNames.GAZABDOR
        ])
        return True
    
    # Tinchlar g'alaba qilgan
    if not check_mafialar_list(mafiyalar) and fuqarolar and not qotil:
        await announce_game_result_redis(game_id, bot, chat, winner_roles=tinchlar)
        return True
    
    # Mafiyalar g'alaba qilgan
    if len(mafiyalar) >= len(fuqarolar) and mafiyalar and not qotil:
        await announce_game_result_redis(game_id, bot, chat, winner_roles=mafialar)
        return True
    
    # 2 ta o'yinchi qolgan va 1 ta mafia
    if len(players) == 2 and len(mafiyalar) == 1:
        await announce_game_result_redis(game_id, bot, chat, winner_roles=mafialar)
        return True
    
    return False


def check_mafialar_list(mafiyalar: list) -> bool:
    """Mafiyalar orasida tirik mafia bor yoki yo'qligini tekshirish."""
    return len(mafiyalar) > 0


WIN_RESULT_STRINGS = {
    "uz": {
        "title": "<b>🎉 O'yin tugadi!</b>",
        "winners": "<b>G'oliblar:</b>",
        "others": "<b>Qolgan o'yinchilar:</b>",
        "duration": "<b>O'yin davomiyligi:</b>",
        "units": {"hours": "soat", "mins": "daqiqa", "secs": "soniya"}
    },
    "ru": {
        "title": "<b>🎉 Игра окончена!</b>",
        "winners": "<b>Победители:</b>",
        "others": "<b>Остальные игроки:</b>",
        "duration": "<b>Длительность игры:</b>",
        "units": {"hours": "ч.", "mins": "мин.", "secs": "сек."}
    },
    "en": {
        "title": "<b>🎉 Game over!</b>",
        "winners": "<b>Winners:</b>",
        "others": "<b>Other players:</b>",
        "duration": "<b>Game duration:</b>",
        "units": {"hours": "hours", "mins": "mins", "secs": "secs"}
    },
    "tr": {
        "title": "<b>🎉 Oyun bitti!</b>",
        "winners": "<b>Kazananlar:</b>",
        "others": "<b>Diğer oyuncular:</b>",
        "duration": "<b>Oyun süresi:</b>",
        "units": {"hours": "saat", "mins": "dakika", "secs": "saniye"}
    },
    "kk": {
        "title": "<b>🎉 Ойын аяқталды!</b>",
        "winners": "<b>Жеңімпаздар:</b>",
        "others": "<b>Басқа ойыншылар:</b>",
        "duration": "<b>Ойын ұзақтығы:</b>",
        "units": {"hours": "сағат", "mins": "минут", "secs": "секунд"}
    }
}

def _duration_text(started_at, lang: str = "uz") -> Optional[str]:
    if not started_at:
        return None
    from utils.i18n import clean_lang
    lang = clean_lang(lang)
    units = WIN_RESULT_STRINGS.get(lang, WIN_RESULT_STRINGS["uz"])["units"]

    start = started_at
    if getattr(start, "tzinfo", None) is None:
        start = start.replace(tzinfo=timezone.utc)
    total = max(0, int((datetime.now(timezone.utc) - start).total_seconds()))
    hours, rem = divmod(total, 3600)
    mins, secs = divmod(rem, 60)
    parts = []
    if hours:
        parts.append(f"{hours} {units['hours']}")
    if mins or hours:
        parts.append(f"{mins} {units['mins']}")
    parts.append(f"{secs} {units['secs']}")
    return " ".join(parts)


async def _player_mentions(user_ids: list) -> dict:
    result = {}
    ids = list({int(u) for u in user_ids if u is not None})
    if not ids:
        return result
    users = await User.filter(user_id__in=ids)
    for u in users:
        name = html.escape(u.full_name or u.username or str(u.user_id))
        result[u.user_id] = f'<a href="tg://user?id={u.user_id}">{name}</a>'
    for uid in ids:
        result.setdefault(uid, f'<a href="tg://user?id={uid}">{uid}</a>')
    return result


def _get_chat_id(chat) -> int:
    if isinstance(chat, int):
        return chat
    if hasattr(chat, "chat_id"):
        return getattr(chat, "chat_id")
    if hasattr(chat, "id"):
        return getattr(chat, "id")
    try:
        return int(chat)
    except Exception:
        return 0


async def announce_game_result_redis(
    game_id: str,
    bot: Bot,
    chat,
    winner_roles: list,
    zombilar=False,
    para=False,
    para_winners=None,
    vsgame=False,
    winning_team=None,
    real_mode=False
):
    """O'yin natijalarini e'lon qilish: g'oliblar + qolganlar + davomiylik."""
    target_chat_id = _get_chat_id(chat)

    game_state = await game_repo.load_game(game_id)
    if game_state:
        game_state.phase = "end"
        game_state.is_active = False
        await game_repo.save_game(game_state, ttl_sec=_ENDED_TTL)

    if target_chat_id:
        await _clear_active_indexes(game_id, target_chat_id)

    all_players = await player_repo.get_all_players(game_id)
    if para and para_winners:
        winner_ids = {p.user_id for p in para_winners}
        winners = [p for p in all_players if p.user_id in winner_ids and (p.is_alive or (p.role == RoleNames.SUIDSID and getattr(p, 'osildi', False)))]
    elif vsgame and winning_team is not None:
        winners = [p for p in all_players if p.team == winning_team and (p.is_alive or (p.role == RoleNames.SUIDSID and getattr(p, 'osildi', False)))]
    else:
        winner_set = set(winner_roles or [])
        winners = [p for p in all_players if p.role in winner_set and (p.is_alive or (p.role == RoleNames.SUIDSID and getattr(p, 'osildi', False)))]

    # Kezuvchi maxsus g'alaba sharti:
    # Faqatgina tinch aholi yutgan bo'lsa VA Kezuvchi tirik (is_alive) bo'lsa g'alaba qozonadi.
    # Agar Kezuvchi o'lgan bo'lsa yoki tinch aholi yutqazgan bo'lsa, Kezuvchi yutqazadi.
    civilians_won = any(r in (winner_roles or []) for r in (RoleNames.FUQARO, RoleNames.KOMISSAR))
    filtered_winners = []
    for p in winners:
        if p.role == RoleNames.KEZUVCHI:
            if civilians_won and p.is_alive:
                filtered_winners.append(p)
        else:
            filtered_winners.append(p)
    winners = filtered_winners

    winner_id_set = {p.user_id for p in winners}
    others = [p for p in all_players if p.user_id not in winner_id_set]
    mentions = await _player_mentions([p.user_id for p in all_players])

    from utils.i18n import get_chat_lang
    chat_lang = await get_chat_lang(target_chat_id)
    strs = WIN_RESULT_STRINGS.get(chat_lang, WIN_RESULT_STRINGS["uz"])

    win_reward = 20
    lose_reward = 5

    lines = [strs["title"], strs["winners"]]
    n = 1
    if winners:
        for p in winners:
            lines.append(f"{n}. {mentions.get(p.user_id, p.user_id)} - {role_display(p.role, lang=chat_lang)} (+{win_reward}$)")
            n += 1
            p.win = True
            try:
                await player_repo.save_player(p, ttl_sec=_ENDED_TTL)
            except Exception:
                pass
    else:
        lines.append("—")

    if others:
        lines.append("")
        lines.append(strs["others"])
        for p in others:
            lines.append(f"{n}. {mentions.get(p.user_id, p.user_id)} - {role_display(p.role, lang=chat_lang)} (+{lose_reward}$)")
            n += 1

    started = getattr(game_state, "started_at", None) or getattr(game_state, "created_at", None) if game_state else None
    duration = _duration_text(started, lang=chat_lang)
    if duration:
        lines.append("")
        lines.append(f"{strs['duration']} {duration}")

    if target_chat_id:
        try:
            await bot.send_message(
                target_chat_id,
                "\n".join(lines),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        except Exception as e:
            print(f"Failed to send end game result to chat {target_chat_id}: {e}")

    # Shaxsiy lichkaga har bir o'yinchiga g'alaba/mag'lubiyat profili va mukofotini yuborish
    for p in winners:
        await _send_player_end_game_profile_dm(bot, p.user_id, is_winner=True, win_reward=win_reward)

    for p in others:
        await _send_player_end_game_profile_dm(bot, p.user_id, is_winner=False, lose_reward=lose_reward)


async def _send_player_end_game_profile_dm(bot: Bot, uid: int, is_winner: bool, win_reward: int = 20, lose_reward: int = 5):
    try:
        from models.user import User, Profile, Paralar, ActiveRole, VipUser
        from utils.i18n import get_chat_lang, clean_lang
        from utils.premium_emojis import get_diamond_display, get_dollar_display, role_display
        from keyboards.user_keyboards import profile_keyboards_on_private

        p_lang = clean_lang(await get_chat_lang(uid))
        user = await User.filter(user_id=uid).first()
        if not user:
            return

        profile, _ = await Profile.get_or_create(user=user)
        reward = win_reward if is_winner else lose_reward

        # Update profile stats
        profile.dollar += reward
        profile.games_count += 1
        if is_winner:
            profile.wins += 1
        await profile.save()

        # VIP status
        vip_obj = await VipUser.get_or_none(user=user)
        is_vip = bool(vip_obj)
        vip_status = f" ({vip_obj.emoji_char})" if (vip_obj and vip_obj.emoji_char) else ""
        vip_text = f" ⭐ VIP{vip_status}" if is_vip else ""

        # Check Para
        para = await Paralar.filter(user1=user).prefetch_related("user1", "user2").first()
        if not para:
            para = await Paralar.filter(user2=user).prefetch_related("user1", "user2").first()
        
        if para:
            partner_user = para.user2 if para.user1_id == user.id else para.user1
            partner_name = html.escape(partner_user.full_name or partner_user.username or str(partner_user.user_id))
            para_str = f'<a href="tg://user?id={partner_user.user_id}">{partner_name}</a>'
        else:
            para_str = {"uz": "<i>Yo'q</i>", "ru": "<i>Нет</i>", "en": "<i>None</i>", "tr": "<i>Yok</i>", "kk": "<i>Жоқ</i>"}.get(p_lang, "<i>Yo'q</i>")

        # Check Active Roles
        active_roles_list = await ActiveRole.filter(profile=profile, is_active=True).all()
        if active_roles_list:
            roles_names = [role_display(r.role, lang=p_lang) for r in active_roles_list]
            active_roles_str = ", ".join(roles_names)
        else:
            active_roles_str = {"uz": "<i>Yo'q</i>", "ru": "<i>Нет</i>", "en": "<i>None</i>", "tr": "<i>Yok</i>", "kk": "<i>Жоқ</i>"}.get(p_lang, "<i>Yo'q</i>")

        if is_winner:
            headers = {
                "uz": f"🏆 <b>O'yin tugadi!</b>\n✅ <b>Yutganingiz uchun sizga {reward}$ pul va 0 olmos berildi!</b>",
                "ru": f"🏆 <b>Игра окончена!</b>\n✅ <b>За победу вам выдано {reward}$ и 0 алмазов!</b>",
                "en": f"🏆 <b>Game over!</b>\n✅ <b>You won! Received {reward}$ and 0 diamonds!</b>",
                "tr": f"🏆 <b>Oyun bitti!</b>\n✅ <b>Kazandığınız için size {reward}$ ve 0 elmas verildi!</b>",
                "kk": f"🏆 <b>Ойын аяқталды!</b>\n✅ <b>Жеңгеніңіз үшін сізге {reward}$ және 0 алмас берілді!</b>"
            }
        else:
            headers = {
                "uz": f"💀 <b>O'yin tugadi!</b>\n❌ <b>Mag'lubiyatingiz uchun sizga {reward}$ pul va 0 olmos berildi!</b>",
                "ru": f"💀 <b>Игра окончена!</b>\n❌ <b>Вам выдано {reward}$ и 0 алмазов!</b>",
                "en": f"💀 <b>Game over!</b>\n❌ <b>Received {reward}$ and 0 diamonds!</b>",
                "tr": f"💀 <b>Oyun bitti!</b>\n❌ <b>Size {reward}$ ve 0 elmas verildi!</b>",
                "kk": f"💀 <b>Ойын аяқталды!</b>\n❌ <b>Сізге {reward}$ және 0 алмас берілді!</b>"
            }

        d_disp = get_diamond_display()
        m_disp = get_dollar_display()

        user_name = html.escape(user.full_name or user.username or f"User_{uid}")

        card_text = (
            f"{headers.get(p_lang, headers['uz'])}\n\n"
            f"👤 <b>{user_name}</b>{vip_text}\n\n"
            f"{m_disp} Dollar: <b>{profile.dollar:,}</b>\n"
            f"{d_disp} Olmos: <b>{profile.diamond:,}</b>\n\n"
            f"🛡 Himoya: <b>{profile.himoya}</b>\n"
            f"📜 Hujjat: <b>{profile.hujjat}</b>\n"
            f"🔒 Osishdan himoya qilish: <b>{profile.osishdan_himoya}</b>\n"
            f"📦 Qotildan himoya: <b>{profile.qotildan_himoya}</b>\n"
            f"🔫 Miltiq: <b>{profile.miltiq}</b>\n"
            f"💊 Doridan himoya: <b>{profile.doridan_himoya}</b>\n"
            f"🎭 Maska: <b>{profile.maska}</b>\n"
            f"📜 Sirpanishdan himoya: <b>{profile.slip_himoya}</b>\n"
            f"📦 Geroydan himoya: <b>{profile.geroy_himoya}</b>\n\n"
            f"🎯 G'alaba: <b>{profile.wins}</b>\n"
            f"📜 Barcha o'yinlar: <b>{profile.games_count}</b>\n\n"
            f"Sizning parangiz: {para_str}\n\n"
            f"🏙 Faol rollar: {active_roles_str}"
        )

        try:
            await bot.send_message(uid, card_text, parse_mode="HTML", reply_markup=profile_keyboards_on_private(profile, is_vip=is_vip))
        except Exception:
            try:
                await bot.send_message(uid, card_text, parse_mode="HTML")
            except Exception:
                pass
    except Exception as e:
        print(f"End game profile DM error for {uid}: {e}")


async def cleanup_game_redis(game_id: str):
    """
    O'yin tugagandan keyin tozalash.
    
    Args:
        game_id: O'yin ID
    """
    # Remove from active indexes first (idempotent), so a partially-failed
    # cleanup below can never leave the game stuck in the active list.
    await _clear_active_indexes(game_id)

    # Mark all players as dead
    from utils.redis_game.repositories.player_repository import player_repository as player_repo
    
    players = await player_repo.get_all_players(game_id)
    for player in players:
        player.is_alive = False
        await player_repo.save_player(player, ttl_sec=_ENDED_TTL)
    
    # Set TTL on game state key
    try:
        from utils.database import redis_client
        await redis_client.expire(f"game:{game_id}:state", _ENDED_TTL)
    except Exception:
        pass
