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
        await announce_game_result_redis(game_id, bot, chat, winner_roles=[
            RoleNames.KOMISSAR, RoleNames.DOKTOR, RoleNames.FUQARO
        ])
        return True
    
    # Mafiyalar g'alaba qilgan
    if len(mafiyalar) > len(fuqarolar) and mafiyalar and not qotil and not zombilar:
        await announce_game_result_redis(game_id, bot, chat, winner_roles=[
            RoleNames.DON, RoleNames.MAFIA
        ])
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
        await announce_game_result_redis(game_id, bot, chat, winner_roles=[
            RoleNames.KOMISSAR, RoleNames.DOKTOR, RoleNames.FUQARO
        ])
        return True
    
    # Mafiyalar g'alaba qilgan
    if len(mafiyalar) >= len(fuqarolar) and mafiyalar and not qotil:
        await announce_game_result_redis(game_id, bot, chat, winner_roles=[
            RoleNames.DON, RoleNames.MAFIA
        ])
        return True
    
    # 2 ta o'yinchi qolgan va 1 ta mafia
    if len(players) == 2 and len(mafiyalar) == 1:
        await announce_game_result_redis(game_id, bot, chat, winner_roles=[
            RoleNames.DON, RoleNames.MAFIA
        ])
        return True
    
    return False


def check_mafialar_list(mafiyalar: list) -> bool:
    """Mafiyalar orasida Don bor yoki yo'qligini tekshirish."""
    if not mafiyalar:
        return False
    for player in mafiyalar:
        if player.role == RoleNames.DON:
            return True
    return False


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


async def announce_game_result_redis(
    game_id: str,
    bot: Bot,
    chat: Chat,
    winner_roles: list,
    zombilar=False,
    para=False,
    para_winners=None,
    vsgame=False,
    winning_team=None,
    real_mode=False
):
    """O'yin natijalarini e'lon qilish: g'oliblar + qolganlar + davomiylik."""
    try:
        from utils.redis_game.night_engine import flush_pending_deaths
        await flush_pending_deaths(game_id, bot, chat)
    except Exception:
        pass

    game_state = await game_repo.load_game(game_id)
    if game_state:
        game_state.phase = "end"
        game_state.is_active = False
        await game_repo.save_game(game_state, ttl_sec=_ENDED_TTL)

    await _clear_active_indexes(game_id, getattr(chat, "chat_id", None))

    all_players = await player_repo.get_all_players(game_id)
    if para and para_winners:
        winner_ids = {p.user_id for p in para_winners}
        winners = [p for p in all_players if p.user_id in winner_ids]
    elif vsgame and winning_team is not None:
        winners = [p for p in all_players if p.team == winning_team]
    else:
        winner_set = set(winner_roles or [])
        winners = [p for p in all_players if p.role in winner_set]

    winner_id_set = {p.user_id for p in winners}
    others = [p for p in all_players if p.user_id not in winner_id_set]
    mentions = await _player_mentions([p.user_id for p in all_players])

    from utils.i18n import get_chat_lang
    chat_lang = await get_chat_lang(getattr(chat, "chat_id", 0))
    strs = WIN_RESULT_STRINGS.get(chat_lang, WIN_RESULT_STRINGS["uz"])

    lines = [strs["title"], strs["winners"]]
    n = 1
    if winners:
        for p in winners:
            lines.append(f"{n}. {mentions.get(p.user_id, p.user_id)} - {role_display(p.role, lang=chat_lang)}")
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
            lines.append(f"{n}. {mentions.get(p.user_id, p.user_id)} - {role_display(p.role, lang=chat_lang)}")
            n += 1

    started = getattr(game_state, "started_at", None) or getattr(game_state, "created_at", None) if game_state else None
    duration = _duration_text(started, lang=chat_lang)
    if duration:
        lines.append("")
        lines.append(f"{strs['duration']} {duration}")

    await bot.send_message(
        chat.chat_id,
        "\n".join(lines),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )

    # Shaxsiy lichkaga har bir o'yinchiga g'alaba/mag'lubiyat profili va mukofotini yuborish
    for p in winners:
        await _send_player_end_game_profile_dm(bot, p.user_id, is_winner=True, win_reward=15)

    for p in others:
        await _send_player_end_game_profile_dm(bot, p.user_id, is_winner=False, lose_reward=5)


async def _send_player_end_game_profile_dm(bot: Bot, uid: int, is_winner: bool, win_reward: int = 15, lose_reward: int = 5):
    try:
        from models.user import User, Profile, Paralar, ActiveRole, VipUser
        from utils.i18n import get_chat_lang, clean_lang
        from keyboards.user_keyboards import profile_keyboards_on_private

        p_lang = clean_lang(await get_chat_lang(uid))
        user = await User.filter(user_id=uid).first()
        if not user:
            return

        profile, _ = await Profile.get_or_create(user=user)
        reward = win_reward if is_winner else lose_reward

        # Update profile stats
        profile.dollar += reward
        if is_winner:
            profile.wins += 1
        await profile.save()

        # Check Para
        para = await Paralar.filter(user1=user).first()
        if not para:
            para = await Paralar.filter(user2=user).first()
        
        if para:
            partner_user = para.user2 if para.user1_id == user.id else para.user1
            partner_name = html.escape(partner_user.full_name or partner_user.username or str(partner_user.user_id))
            para_str = f'<a href="tg://user?id={partner_user.user_id}">{partner_name}</a>'
        else:
            para_str = {"uz": "Yo'q", "ru": "Нет", "en": "None", "tr": "Yok", "kk": "Жоқ"}.get(p_lang, "Yo'q")

        # Check Active Roles
        active_roles_list = await ActiveRole.filter(profile=profile, is_active=True).all()
        if active_roles_list:
            roles_names = [role_display(r.role, lang=p_lang) for r in active_roles_list]
            active_roles_str = ", ".join(roles_names)
        else:
            active_roles_str = {"uz": "Yo'q", "ru": "Нет", "en": "None", "tr": "Yok", "kk": "Жоқ"}.get(p_lang, "Yo'q")

        if is_winner:
            headers = {
                "uz": f"🏆 <b>O'yin tugadi!</b>\n✅ <b>Siz g'alaba qozondingiz! G'alaba uchun {reward} 💵 berildi!</b>",
                "ru": f"🏆 <b>Игра окончена!</b>\n✅ <b>Вы выиграли! За победу получено {reward} 💵!</b>",
                "en": f"🏆 <b>Game over!</b>\n✅ <b>You won! Received {reward} 💵 for victory!</b>",
                "tr": f"🏆 <b>Oyun bitti!</b>\n✅ <b>Kazandınız! Zafer için {reward} 💵 alındı!</b>",
                "kk": f"🏆 <b>Ойын аяқталды!</b>\n✅ <b>Сіз жеңдіңіз! Жеңіс үшін {reward} 💵 берілді!</b>"
            }
        else:
            headers = {
                "uz": f"💀 <b>O'yin tugadi!</b>\n❌ <b>Siz mag'lub bo'ldingiz! Mag'lubiyat uchun {reward} 💵 berildi!</b>",
                "ru": f"💀 <b>Игра окончена!</b>\n❌ <b>Вы проиграли! За участие получено {reward} 💵!</b>",
                "en": f"💀 <b>Game over!</b>\n❌ <b>You lost! Received {reward} 💵 for participation!</b>",
                "tr": f"💀 <b>Oyun bitti!</b>\n❌ <b>Kaybettiniz! Katılım için {reward} 💵 alındı!</b>",
                "kk": f"💀 <b>Ойын аяқталды!</b>\n❌ <b>Сіз жеңілдіңіз! Қатысу үшін {reward} 💵 берілді!</b>"
            }

        labels = {
            "uz": {
                "dollar": "Dollar", "diamond": "Olmos", "himoya": "Himoya", "hujjat": "Hujjat",
                "osish": "Osishdan himoya qilish", "qotil": "Qotildan himoya", "miltiq": "Miltiq",
                "dori": "Doridan himoya", "maska": "Maska", "slip": "Sirpanishdan himoya",
                "geroy": "Geroydan himoya", "wins": "G'alaba", "games": "Barcha o'yinlar",
                "para": "Sizning parangiz", "active": "Faol rollar"
            },
            "ru": {
                "dollar": "Доллары", "diamond": "Алмазы", "himoya": "Защита", "hujjat": "Документ",
                "osish": "Защита от повешения", "qotil": "Защита от киллера", "miltiq": "Винтовка",
                "dori": "Защита от лекарства", "maska": "Маска", "slip": "Защита от скольжения",
                "geroy": "Защита от героя", "wins": "Победы", "games": "Все игры",
                "para": "Ваша пара", "active": "Активные роли"
            },
            "en": {
                "dollar": "Dollar", "diamond": "Diamonds", "himoya": "Protection", "hujjat": "Document",
                "osish": "Hang protection", "qotil": "Killer protection", "miltiq": "Rifle",
                "dori": "Medicine protection", "maska": "Mask", "slip": "Slip protection",
                "geroy": "Hero protection", "wins": "Wins", "games": "All games",
                "para": "Your partner", "active": "Active roles"
            },
            "tr": {
                "dollar": "Dolar", "diamond": "Elmaslar", "himoya": "Koruma", "hujjat": "Belge",
                "osish": "Asılma koruması", "qotil": "Katilden koruma", "miltiq": "Tüfek",
                "dori": "İlaç koruması", "maska": "Maske", "slip": "Kayma koruması",
                "geroy": "Kahraman koruması", "wins": "Galibiyetler", "games": "Tüm oyunlar",
                "para": "Partneriniz", "active": "Aktif roller"
            },
            "kk": {
                "dollar": "Доллар", "diamond": "Алмастар", "himoya": "Қорғау", "hujjat": "Құжат",
                "osish": "Асылудан қорғау", "qotil": "Қанішерден қорғау", "miltiq": "Мылтық",
                "dori": "Дәріден қорғау", "maska": "Маска", "slip": "Сырғанаудан қорғау",
                "geroy": "Батырдан қорғау", "wins": "Жеңістер", "games": "Барлық ойындар",
                "para": "Сіздің жұбыңыз", "active": "Белсенді рөлдер"
            }
        }
        l = labels.get(p_lang, labels["uz"])
        user_name = html.escape(user.full_name or user.username or f"User_{uid}")

        card_text = (
            f"{headers.get(p_lang, headers['uz'])}\n\n"
            f"👤 <b>{user_name}</b>\n\n"
            f"💵 {l['dollar']}: <b>{profile.dollar:,}</b>\n"
            f"💎 {l['diamond']}: <b>{profile.diamond:,}</b>\n\n"
            f"🛡 {l['himoya']}: <b>{profile.himoya}</b>\n"
            f"📜 {l['hujjat']}: <b>{profile.hujjat}</b>\n"
            f"🔒 {l['osish']}: <b>{profile.osishdan_himoya}</b>\n"
            f"📦 {l['qotil']}: <b>{profile.qotildan_himoya}</b>\n"
            f"🔫 {l['miltiq']}: <b>{profile.miltiq}</b>\n"
            f"💊 {l['dori']}: <b>{profile.doridan_himoya}</b>\n"
            f"🎭 {l['maska']}: <b>{profile.maska}</b>\n"
            f"📜 {l['slip']}: <b>{profile.slip_himoya}</b>\n"
            f"📦 {l['geroy']}: <b>{profile.geroy_himoya}</b>\n\n"
            f"🎯 {l['wins']}: <b>{profile.wins}</b>\n"
            f"📜 {l['games']}: <b>{profile.games_count}</b>\n\n"
            f"{l['para']}: {para_str}\n"
            f"🏢 {l['active']}: {active_roles_str}"
        )

        try:
            vip_obj = await VipUser.get_or_none(user=user)
            is_vip = bool(vip_obj)
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
    
    # TODO: Clean up phases and actions
    # TODO: Remove from active games list
