import logging
import html
from aiogram.types import ChatMemberAdministrator, ChatMemberOwner
from aiogram import Bot
logger = logging.getLogger(__name__)

async def safe_send_message(bot, chat_id, text, **kwargs):
    try:
        return await bot.send_message(chat_id, text, **kwargs)
    except Exception as e:
        logger.error(f"Failed to send message to {chat_id}: {e} | text={text[:500]!r}")
        return None

async def safe_send_photo(bot, chat_id, photo, **kwargs):
    try:
        return await bot.send_photo(chat_id, photo, **kwargs)
    except Exception as e:
        logger.error(f"Failed to send photo to {chat_id}: {e}")
        return None

async def safe_answer(call, *args, **kwargs):
    try:
        await call.answer(*args, **kwargs)
    except Exception as e:
        logger.warning(f"Failed to answer callback query {call.id}: {e}")

from aiogram.types import Message, CallbackQuery
from datetime import datetime, timezone
from utils.database import redis_client
from utils.game_redis_utils import create_or_get_game_redis, remove_game_redis
from keyboards.game_keyboard import join_vsgame_button, qaroqchi_action_button, konchi_button, join_game_button, joker_death_select_buttons, action_buttons, vote_buttons, sehr_action_button, go_group_button, joker_buttons
from keyboards.main_keyboard import bot_link_markup
from models.game_data import Chat, Game, GamePlayer, GamePhase, Action, Vote, VoteLike, GazabdorPick, PlayersGameBall
from models.game_set import GamingOnChat, GameModeSet, GameSetTime, GameSetListRoles, GameSetPermissions, GroupMoreSet, CommandPermissionsChat, GameSetWeapons
from utils.role_names import RoleNames
from utils.konchi_utils import get_konchi_konlari
from models.user import User, Profile, ActiveRole, Paralar, VipUser
from utils.premium_emojis import build_vip_prefix, role_display, kezuvchi_display_name
from .geroylar_game import send_geroys_action_message, geroys_action_result, assign_new_role
from aiogram.enums import ChatMemberStatus
from utils.role_replacement import check_and_replace_missing_roles
from models.game_set import WolfOrFoxSet
from utils.role_configuration import RoleConfiguration
from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import random
from collections import defaultdict
from utils.others import get_profile, send_game_over_profile
from aiogram.enums import ChatMemberStatus
from collections import Counter
from tortoise.exceptions import DoesNotExist
from utils.role_names import RoleNames
from tortoise.functions import Count
from utils.roles_text import Roles
from config import mafia_rollar, yakka_rollar, tinch_rollar, BOT_URL
from utils.vsgame import TeamCOlors
from datetime import datetime
from config import ADMINS
from asyncio import create_task
from aiogram.fsm.storage.base import StorageKey
import asyncio
from tortoise.transactions import in_transaction
from tortoise.functions import Count
from datetime import datetime
from config import MAX_PLAYERS
from aiogram.fsm.context import FSMContext
from aiogram.enums import ChatMemberStatus
from datetime import datetime
import re
import time

game_timers = {}  # {chat_id: {'expiry': timestamp, 'warned': False, 'game_id': game_id, 'message': message}}

async def handle_vote_like(call: CallbackQuery, bot: Bot, state: FSMContext = None):
    """Sud ovoz berish jarayonida Like/Dislike qabul qilish"""
    try:
        parts = call.data.split("_")
        action = parts[0]  # "like" or "dislike"
        target_id = int(parts[1])
        phase_id = int(parts[2])

        user = await User.filter(user_id=call.from_user.id).first()
        if not user:
            await call.answer("❌ Foydalanuvchi topilmadi!", show_alert=True)
            return

        voter = await GamePlayer.filter(user=user, is_alive=True).first()
        if not voter:
            await call.answer("❌ Faqat tirik o'yinchilar ovoz berishi mumkin!", show_alert=True)
            return

        phase = await GamePhase.filter(id=phase_id).first()
        if not phase or phase.is_end:
            await call.answer("❌ Sud jarayoni yakunlangan!", show_alert=True)
            return

        target = await GamePlayer.filter(id=target_id).first()
        if not target:
            await call.answer("❌ Nishon topilmadi!", show_alert=True)
            return

        is_like = (action == "like")

        existing = await VoteLike.filter(phase=phase, voter=voter).first()
        if existing:
            existing.is_like = is_like
            existing.target = target
            await existing.save()
            await call.answer("🔄 Ovozingiz o'zgartirildi!", show_alert=False)
        else:
            await VoteLike.create(
                phase=phase,
                target=target,
                voter=voter,
                is_like=is_like
            )
            await call.answer("✅ Ovozingiz qabul qilindi!", show_alert=False)

        # Real-time tugmalardagi sonlarni yangilash
        from keyboards.game_keyboard import build_vote_like_keyboard
        likes = await VoteLike.filter(phase=phase, target=target, is_like=True).count()
        dislikes = await VoteLike.filter(phase=phase, target=target, is_like=False).count()
        kb = build_vote_like_keyboard(target_id=target_id, phase_id=phase_id, likes=likes, dislikes=dislikes)
        try:
            await call.message.edit_reply_markup(reply_markup=kb)
        except Exception:
            pass
    except Exception as e:
        print(f"handle_vote_like error: {e}")
        await call.answer("❌ Ovozni saqlashda xato!", show_alert=True)

async def auto_start_timer(chat_id: int, game_id: int, bot: Bot):
    """O'yin kutish vaqti tugaganda o'yinni avtomatik boshlash taymeri"""
    while chat_id in game_timers and game_timers[chat_id].get('game_id') == game_id:
        tdata = game_timers[chat_id]
        now = asyncio.get_event_loop().time()
        remaining = tdata['expiry'] - now

        if tdata.get('paused', False):
            await asyncio.sleep(2)
            continue

        if remaining <= 30 and not tdata.get('warned', False):
            tdata['warned'] = True
            await safe_send_message(bot, chat_id, "⚠️ Ro'yxatdan o'tish tugashiga 30 soniya qoldi!", parse_mode="HTML")

        if remaining <= 0:
            del game_timers[chat_id]
            game = await Game.filter(id=game_id, is_active=True, phase="waiting").prefetch_related("chat").first()
            if game:
                players_count = await GamePlayer.filter(game=game, is_alive=True).count()
                if players_count < 4:
                    game.is_active = False
                    game.phase = "end"
                    await game.save()
                    await safe_send_message(
                        bot,
                        chat_id,
                        f"⚠️ O'yin boshlanishi uchun yetarli o'yinchilar (kamida 4 kishi) yig'ilmadi ({players_count}/4). O'yin bekor qilindi.",
                        parse_mode="HTML"
                    )
                else:
                    msg = tdata.get('message')
                    await starting_game(game=game, message=msg, start=True, bot=bot)
            break

        await asyncio.sleep(min(remaining, 5))

async def reset_player_flags(game: Game):
    """
    Har bir faza (Kun/Tun) boshida faqat is_actioned flagini reset qilish.
    Qurol-aslahalar va rollarning maxsus kuchlari butun o'yin davomida 1 martadan ishlatiladi!
    """
    await GamePlayer.filter(game=game, is_alive=True).update(
        is_actioned=False
    )

async def kick_player(message: Message, bot: Bot):
    admin = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if admin.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
        return 
    parts = message.text.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        return 

    try:
        target_number = int(parts[1])
    except ValueError:
        return 

    chat = await Chat.filter(chat_id=message.chat.id).first()
    if not chat:
        return 

    game = await Game.filter(chat=chat, is_active=True).first()
    if not game:
        return 
    player = await GamePlayer.filter(game=game, maxsus_raqam=target_number, is_alive=True).prefetch_related("user", "game__chat").first()
    if not player:
        return 

    player.is_alive = False
    player.deaded_at = datetime.now(timezone.utc)
    player.is_sayed_last_word = True
    await player.save()
    colors_dct = TeamCOlors.all_colors_dict()
    if game.phase == "waiting":
        await update_players_list(game, bot)
        players = await GamePlayer.filter(game=game, is_alive=True).all()
        more_set, _ = await GroupMoreSet.get_or_create(chat_id=chat.chat_id)
        if len(players) >= more_set.max_players:
            await starting_game(game=game, message=message, start=True, bot=bot)
    else:

        phase = await GamePhase.filter(game=game).last()
        try:
            if len(game.mode.split(":")) == 2:
                await safe_send_message(bot, 
                    chat.chat_id,
                    f"{colors_dct[player.team]}{player.user.mention} o'yindan admin tomonidan chiqarildi.\nU edi {role_display(player.role)}",
                    parse_mode="HTML"
                )
            else:
                await safe_send_message(bot, 
                chat.chat_id,
                f"{player.user.mention} o'yindan admin tomonidan chiqarildi.\nU edi {role_display(player.role)}",
                parse_mode="HTML"
            )
        except: pass
        await assign_new_role(player, phase, bot, chat, game)

async def check_paralar_lst(bot: Bot, chat: Chat, paralar: list[tuple[int, int]], phase: GamePhase):
    ids = {pid for para in paralar for pid in para}
    players = await GamePlayer.filter(id__in=ids).prefetch_related("user").all()
    players_dict = {p.id: p for p in players}

    yangi_paralar = []

    async def chiqar(player, chat_id):
        player.is_alive = False
        player.deaded_at = datetime.now(timezone.utc)
        player.is_sayed_last_word = True
        await player.save()
        if player.role in [RoleNames.DON, RoleNames.KOMISSAR, RoleNames.DOKTOR]:
            await assign_new_role(player, phase, bot, chat)
        try:
            await safe_send_message(bot, 
                chat_id,
                f"{player.user.mention} o'yindan sherigi o'lganligi uchun chiqdi.\nU edi {role_display(player.role)}",
                parse_mode="HTML"
            )
        except Exception as e:
            # faqat telegram errorlarni ushlash mumkin
            print(f"Xatolik: {e}")

    # Juftliklarni tekshirish
    for p1_id, p2_id in paralar:
        try:
            player1, player2 = players_dict[p1_id], players_dict[p2_id]

            if not player1.is_alive or not player2.is_alive:
                if player1.is_alive and player2.role not in [RoleNames.SUIDSID, RoleNames.QASOSKOR, RoleNames.GAZABDOR]:
                    await chiqar(player1, chat.chat_id)
                    continue
                elif player2.is_alive and player1.role not in [RoleNames.SUIDSID, RoleNames.QASOSKOR, RoleNames.GAZABDOR]:
                    await chiqar(player2, chat.chat_id)
                    continue
            # Agar ikkalasi ham tirik bo'lsa – yangi ro'yxatga qo'shamiz
            yangi_paralar.append((p1_id, p2_id))
        except:
            yangi_paralar.append((p1_id, p2_id))
    return yangi_paralar

async def starting_game(game: Game, message: Message, bot: Bot, start=False, paralar=None):
    """
    starting_game ni butun umr davomida (tun/kun tsikli) himoyalovchi tashqi qatlam.
    Ichkarida qayerdadir (masalan Telegram flood-control, kutilmagan xato) exception
    chiqsa ham, o'yin butunlay "qotib qolmasin" uchun bu yerda ushlab, guruhga xabar
    berib, o'yinni to'g'ri yakunlaymiz.
    """
    try:
        await _starting_game_impl(game, message, bot, start=start, paralar=paralar)
    except Exception as e:
        logger.error(f"starting_game ichida kutilmagan xato (game_id={getattr(game, 'id', '?')}): {e}")
        was_active = False
        try:
            game_obj = await Game.get_or_none(id=game.id)
            if game_obj and game_obj.is_active:
                was_active = True
                game_obj.is_active = False
                game_obj.phase = "end"
                await game_obj.save()
        except Exception:
            pass
        if was_active:
            try:
                await game.fetch_related("chat")
                await safe_send_message(
                    bot, game.chat.chat_id,
                    "⚠️ O'yinda kutilmagan texnik xatolik yuz berdi, o'yin to'xtatildi. Iltimos, /game bilan qayta boshlang."
                )
            except Exception:
                pass

async def resume_active_games(bot: Bot):
    """
    Bot qayta ishga tushganda (deploy/restart) tun/kun tsiklini yurituvchi
    barcha asyncio tasklar yo'qoladi, lekin DB'da o'yin "faol" (is_active=True)
    bo'lib qolaveradi — o'yin "qotib qoladi", odamlar /stop qilishga majbur
    bo'lishardi. Shu funksiya botni ishga tushirishda faol (night/day
    bosqichidagi) o'yinlarni topib, joriy bosqichni "orqaga qaytarib" (qaytadan
    boshidan) davom ettiradi — rollarni qayta taqsimlamaydi, faqat joriy
    tun/kunni qaytadan yuritadi.
    Shuningdek, "waiting" (ro'yxatdan o'tish) holatidagi o'yinlar uchun ham
    auto_start_timer qayta tiklanadi.
    """
    try:
        games = await Game.filter(is_active=True, phase__in=["night", "day"]).all()
    except Exception as e:
        logger.error(f"resume_active_games: faol o'yinlarni olishda xato: {e}")
        return

    for game in games:
        try:
            await game.fetch_related("chat")
            create_task(starting_game(game=game, message=None, bot=bot, start=False))
            logger.info(f"O'yin qayta tiklandi: game_id={game.id}, chat_id={game.chat.chat_id}, phase={game.phase}")
            await safe_send_message(
                bot, game.chat.chat_id,
                f"🔄 Bot qayta ishga tushdi, o'yin davom etmoqda — joriy {'tun' if game.phase == 'night' else 'kun'} qaytadan boshlanadi."
            )
        except Exception as e:
            logger.error(f"O'yinni qayta tiklashda xato (game_id={getattr(game, 'id', '?')}): {e}")

    try:
        waiting_games = await Game.filter(is_active=True, phase="waiting").all()
        for wg in waiting_games:
            await wg.fetch_related("chat")
            game_times, _ = await GameSetTime.get_or_create(chat_id=wg.chat.chat_id)
            expiry = asyncio.get_event_loop().time() + game_times.reg_time
            game_timers[wg.chat.chat_id] = {
                'expiry': expiry,
                'warned': False,
                'paused': False,
                'game_id': wg.id,
                'message': None
            }
            create_task(auto_start_timer(wg.chat.chat_id, wg.id, bot))
            logger.info(f"Kutish holatidagi o'yin taymeri tiklandi: game_id={wg.id}, chat_id={wg.chat.chat_id}")
    except Exception as e:
        logger.error(f"resume_active_games: waiting o'yinlarni tiklashda xato: {e}")


async def _starting_game_impl(game: Game, message: Message, bot: Bot, start=False, paralar=None):
    await game.fetch_related("chat")
    chat = game.chat
    if chat.chat_id in game_timers:
        del game_timers[chat.chat_id]
    
    game_times, _ = await GameSetTime.get_or_create(chat_id=chat.chat_id)
    if start:
        players = await GamePlayer.filter(game=game, is_alive=True).prefetch_related("user").all()
        if len(players) < 4:
            game.is_active = False
            game.phase = "end"
            await game.save()
            await safe_send_message(
                bot,
                chat_id=chat.chat_id,
                text=f"⚠️ O'yin boshlanishi uchun kamida 4 ta o'yinchi bo'lishi kerak! (Hozir: {len(players)} ta). O'yin bekor qilindi.",
                parse_mode="HTML"
            )
            return

        game.phase = "night"
        await game.save()
        try: await bot.delete_message(chat.chat_id, message_id=game.message_id)
        except: pass 
        await safe_send_message(bot, 
            chat_id=chat.chat_id,
            text=f"<b>O'yin boshlandi!</b>\nMode: {game.mode.split('>')[0]}",
            parse_mode="HTML",
            reply_markup=bot_link_markup
            )

        await rol_taqsimlash(players=players, bot=bot, chat=chat, game=game)
        
        # Rol almashtirishni tekshirish va amalga oshirish
        await check_and_replace_missing_roles(players, bot, chat, game)

    night = 0
    day = 0
    game.created_at = datetime.now(timezone.utc)
    await game.save()
    day_phase, morning_phase, night_phase, afternoon_phase = None, None, None, None
    while game.phase != "end" and game.is_active:
        weapons_set, _ = await GameSetWeapons.get_or_create(chat_id=chat.chat_id)
        if game.mode in ["para x classic", "para x super", "para x mega"]:
            paralar = await check_paralar_lst(bot, chat, paralar, afternoon_phase)
        players = await GamePlayer.filter(
            game=game,
            is_alive=True,
        ).prefetch_related("user").all()
        await check_and_replace_missing_roles(players, bot, chat, game)
        
        for player in players:
            player.is_actioned = False
            await player.save()

        suidsid_players = [p for p in players if p.role == RoleNames.SUIDSID]
        
        tinchlar = [
            RoleNames.KOMISSAR, RoleNames.SERJANT, RoleNames.DAYDI,
            RoleNames.DOKTOR, RoleNames.KEZUVCHI, RoleNames.FUQARO,
            RoleNames.HAMSHIRA, RoleNames.SOTQIN, RoleNames.JANOB,
            RoleNames.OMADLI, RoleNames.XOYIN, RoleNames.QORIQCHI,
            RoleNames.ZANJIR, RoleNames.QASOSKOR
        ]
        mafialar = [
            RoleNames.DON, RoleNames.MAFIA, RoleNames.ADVOKAT,
            RoleNames.OVCHI, RoleNames.JURNALIST, RoleNames.AYGOQCHI
        ]
        yakkalar = [
            RoleNames.AFERIST, RoleNames.BORI, RoleNames.GAZABDOR,
            RoleNames.QOTIL, RoleNames.SEHRGAR, RoleNames.SUIDSID,
            RoleNames.QAROQCHI, RoleNames.AKTYOR, RoleNames.JIN, RoleNames.KONCHI
        ]

        mafiyalar = [p for p in players if p.role in mafialar]
        fuqarolar = [p for p in players if p.role in tinchlar]
        qotil = [p for p in players if p.role == RoleNames.QOTIL]
        mafialar_2 = [p for p in players if p.role in [RoleNames.OVCHI]]
        yakka_taraflar = [p for p in players if p.role in yakkalar]

        if game.mode.startswith("super") or "classic" in game.mode or "mega" in game.mode:
            # 1. Tinchlar g'alabasi: Mafiyalar va yakkalar qolmagan bo'lsa va tirik fuqarolar bo'lsa
            if len(players) > 0 and (len(players) == len(fuqarolar) or (len(mafiyalar) == 0 and len(yakka_taraflar) == 0)):
                await announce_game_result(
                    game, bot, chat,
                    tinchlar, real_mode=True
                )
                game.phase = "end"
                game.is_active = False
                await game.save()
                break

            # 2. Mafiyalar g'alabasi: Tinchlar va yakkalar yo'q bo'lsa, yoki Mafiyalar soni tinchlardan ko'p/teng bo'lib yakkalar bo'lmasa
            elif len(players) > 0 and (len(players) == len(mafiyalar) or (len(fuqarolar) == 0 and len(yakka_taraflar) == 0) or (len(mafiyalar) >= len(fuqarolar) and len(yakka_taraflar) == 0 and len(mafiyalar) > 0)):
                await announce_game_result(
                    game, bot, chat,
                    mafialar, real_mode=True
                )
                game.phase = "end"
                game.is_active = False
                await game.save()
                break

            # 3. Yakkalar g'alabasi: Faqat yakkalar qolgan bo'lsa
            elif len(players) > 0 and (len(players) == len(yakka_taraflar) or (len(fuqarolar) == 0 and len(mafiyalar) == 0)):
                await announce_game_result(
                    game, bot, chat,
                    yakkalar, real_mode=True
                )
                game.phase = "end"
                game.is_active = False
                await game.save()
                break

            # 4. 2 ta o'yinchi qolgandagi holatlar
            elif len(players) == 2:
                player_1 = players[0]
                player_2 = players[1]
                if player_1.role == RoleNames.DON and player_2.role != RoleNames.KOMISSAR:
                    await announce_game_result(
                        game, bot, chat,
                        mafialar, real_mode=True
                    )
                    game.phase = "end"
                    game.is_active = False
                    await game.save()
                    break

                elif player_1.role == RoleNames.KOMISSAR and player_2.role != RoleNames.DON:
                    await announce_game_result(
                        game, bot, chat,
                        tinchlar, real_mode=True
                    )
                    game.phase = "end"
                    game.is_active = False
                    await game.save()
                    break
                
                elif RoleNames.QOTIL in [player_1.role, player_2.role]:
                    await announce_game_result(
                        game, bot, chat,
                        [RoleNames.QOTIL], real_mode=True
                    )
                    game.phase = "end"
                    game.is_active = False
                    await game.save()
                    break
        if "vsgame" in game.mode:
            teams = defaultdict(list)
            for player in players:
                teams[player.team].append(player)
            if len(teams) == 1 and players:
                winning_team = list(teams.keys())[0]
                winning_roles = list({p.role for p in teams[winning_team]})
                await announce_game_result(
                    game, bot, chat,
                    winner_roles=winning_roles,
                    vsgame=True,
                    winning_team=winning_team
                )
                game.phase = "end"
                game.is_active = False
                await game.save()
                break
        if game.mode in ["zombie x classic 1", "zombie x super 1", "zombie x mega 1"]:
            if len(zombilar) == len(players) and zombilar:
                await announce_game_result(
                    game, bot, chat,
                    winner_roles=[
                        RoleNames.ZOMBI
                    ], zombilar=True
                )
                game.phase = "end"
                game.is_active = False
                await game.save()
                break
            if len(yakkalar) == len(players) and not zombilar:
                await announce_game_result(
                    game, bot, chat,
                    winner_roles=[
                        RoleNames.QOTIL,
                        RoleNames.SUIDSID,
                        RoleNames.QASOSKOR,
                        RoleNames.GAZABDOR,
                    ]
                )
                game.phase = "end"
                game.is_active = False
                await game.save()
                break
            if not fuqarolar and not mafiyalar and not mafialar_2 and qotil and not zombilar:
                await announce_game_result(
                    game, bot, chat,
                    winner_roles=[
                        RoleNames.QOTIL,
                        RoleNames.SUIDSID,
                        RoleNames.QASOSKOR,
                        RoleNames.GAZABDOR,
                    ]
                )
                game.phase = "end"
                game.is_active = False
                await game.save()
                break
            if len(qotil) == len(fuqarolar + mafiyalar) and not zombilar:
                await announce_game_result(
                    game, bot, chat,
                    winner_roles=[
                        RoleNames.QOTIL,
                        RoleNames.SUIDSID,
                        RoleNames.QASOSKOR,
                        RoleNames.GAZABDOR,
                    ]
                )
                game.phase = "end"
                game.is_active = False
                await game.save()
                break
            if (not check_mafialar_list(mafiyalar) and not mafialar_2 and fuqarolar and not qotil) and not zombilar:
                await announce_game_result(
                    game, bot, chat,
                    winner_roles=tinchlar
                )
                game.phase = "end"
                game.is_active = False
                await game.save()
                break

            if ((len(mafiyalar) > len(fuqarolar) and mafiyalar and not qotil) or len(players) == 2 and len(mafiyalar) == 1) and not zombilar:
                await announce_game_result(
                    game, bot, chat,
                    winner_roles=mafialar
                )
                game.phase = "end"
                game.is_active = False
                await game.save()
                break
        if game.mode in ["para x classic", "para x super", "para x mega"]:
            if len(players) == 2:
                user1 = players[0].user
                user2 = players[1].user
                para = await Paralar.filter(
                    user1=user1, user2=user2
                ).first()
                if not para:
                    para = await Paralar.filter(
                        user1=user2, user2=user1
                    ).first()
                if para:
                    await announce_game_result(
                        game, bot, chat,
                        winner_roles=[
                            players[0].role, players[1].role
                        ], para=True, para_winners=[players[0], players[1]]
                    )
                    game.phase = "end"
                    game.is_active = False
                    await game.save()
                    break
            elif len(players) == 1:
                user1 = players[0].user
                para = await Paralar.filter(user1=user1).first()
                if not para:
                    para = await Paralar.filter(user2=user1).first()
                if para:
                    await announce_game_result(
                        game, bot, chat,
                        winner_roles=[
                            players[0].role
                        ], para=True, para_winners=[players[0]]
                    )
                    game.phase = "end"
                    game.is_active = False
                    await game.save()
                    break
        if ("super" in game.mode or "classic" in game.mode or "mega" in game.mode) and "vsgame" not in game.mode:
            if len(players) == 1:
                await announce_game_result(
                    game, bot, chat,
                    winner_roles=[
                        RoleNames.SUIDSID,
                        RoleNames.QASOSKOR,
                        RoleNames.GAZABDOR,
                        players[0].role
                    ]
                )
                game.phase = "end"
                game.is_active = False
                await game.save()
                break
            if not fuqarolar and not mafiyalar and not mafialar_2 and qotil:
                await announce_game_result(
                    game, bot, chat,
                    winner_roles=yakka_rollar
                    
                )
                game.phase = "end"
                game.is_active = False
                await game.save()
                break
            if len(qotil) == len(fuqarolar + mafiyalar):
                await announce_game_result(
                    game, bot, chat,
                    winner_roles=yakka_rollar
                )
                game.phase = "end"
                game.is_active = False
                await game.save()
                break
            if (not check_mafialar_list(mafiyalar) and not mafialar_2 and fuqarolar and not qotil):
                await announce_game_result(
                    game, bot, chat,
                    tinchlar
                )
                game.phase = "end"
                game.is_active = False
                await game.save()
                break

            if ((len(mafiyalar) > len(fuqarolar) and mafiyalar and not qotil) or len(players) == 2 and len(mafiyalar) == 1):
                await announce_game_result(
                    game, bot, chat,
                    mafialar
                )
                game.phase = "end"
                game.is_active = False
                await game.save()
                break
        if len(players) == 0:
            await announce_game_result(
                game, bot, chat,
                winner_roles=[
                    RoleNames.SUIDSID,
                    RoleNames.QASOSKOR,
                    RoleNames.GAZABDOR
                ]
            )
            game.phase = "end"
            game.is_active = False
            await game.save()
            break
        game = await Game.get(id=game.id)
        if not game.is_active:
            break

            
        if game.phase == "night":
            
            night += 1
            night_phase = await GamePhase.create(game=game, number=night, phase_type="night")
            await reset_player_flags(game)
            if game.mode in ["para x classic", "para x super", "para x mega"]:
                paralar = await check_paralar_lst(bot, chat, paralar, night_phase)
            
            await safe_send_photo(bot,
                chat_id=chat.chat_id,
                photo="https://i2.paste.pics/20ba68d2f84c3ca290a6bdac678b3f72.png?trs=9c5f6eda4ea541b02dd993eee1ba56e17e03c2e963a30fd7a7837782cb4852e8&rand=xqmQoDYsJu",
                caption="🌚 🌃<b>Tun</b>\nKo'chaga faqat jasur va qo'rqmas odamlar chiqishdi. Ertalab tirik qolganlarni sanaymiz...",
                parse_mode="HTML",
                reply_markup=bot_link_markup
            )
            try:
                players_text = await view_players_list(players=players, caption=f"Tonggacha ⏳ {game_times.night_time} sekund qoldi", gmode=game.mode)
                await safe_send_message(bot, chat.chat_id, players_text, parse_mode="HTML", reply_markup=bot_link_markup)
            except Exception as e:
                print(f"O'yinchilar ro'yxatini ko'rsatishda xato: {e}")
            await tungi_harakat(message=message, phase=night_phase, bot=bot, vsgame="vsgame" in game.mode, nik=game.mode.split(">")[1] if len(game.mode.split(">")) > 1 else None)
            await asyncio.sleep(game_times.night_time)
            game = await Game.get(id=game.id)
            if not game.is_active:
                break
            await stop_voting_mafias(phase=night_phase, bot=bot, chat=chat)

            await safe_send_photo(bot,
                chat_id=chat.chat_id,
                photo="https://i2.paste.pics/3b5539fcec39e34050bc1365701a66b7.png?trs=9c5f6eda4ea541b02dd993eee1ba56e17e03c2e963a30fd7a7837782cb4852e8&rand=klFwCxWhTJ",
                caption=f"Xayrli tong🌝\n🌄<b>Kun</b>: {day}\nShamollar tundagi mish-mishlarni butun shaharga yetkazmoqda..",
                parse_mode="HTML",
            )
            try:
                await view_night_results(phase=night_phase, game=game, bot=bot, chat=chat, vsgame="vsgame" in game.mode)
            except Exception as e:
                print(f"Tungi natijalarni ko'rsatishda xato: {e}")

            night_phase.is_end = True
            await night_phase.save()

            game.phase = "day"
            await game.save()
                    
        elif game.phase == "day":
            day += 1
            morning_phase = await GamePhase.create(game=game, number=day, phase_type="morning")
            if game.mode in ["para x classic", "para x super", "para x mega"]:
                paralar = await check_paralar_lst(bot, chat, paralar, morning_phase)
            more_set, _ = await GroupMoreSet.get_or_create(chat_id=chat.chat_id)
            try:
                players_text = await view_players_list(players=players, caption="Endi kechaning natijalarini muhokama qilamiz...", guruhlash=more_set.rollarni_guruhlash, add_roles_text=True, view_life=True, gmode=game.mode)
                sent = await safe_send_message(bot, chat.chat_id, players_text, parse_mode="HTML")
                if sent is None:
                    # To'liq matn yuborilmadi (masalan, MESSAGE_TOO_LONG) — rol
                    # tafsilotlarisiz qisqaroq variantda qayta urinamiz, aks holda
                    # guruh tirik o'yinchilar ro'yxatini butunlay ko'rmay qoladi.
                    short_text = await view_players_list(players=players, caption="Endi kechaning natijalarini muhokama qilamiz...", gmode=game.mode)
                    await safe_send_message(bot, chat.chat_id, short_text, parse_mode="HTML")
            except Exception as e:
                print(f"O'yinchilar ro'yxatini ko'rsatishda xato: {e}")
            
            if weapons_set.geroy:
                try: await send_geroys_action_message(players, bot, morning_phase)
                except Exception as e: print(f"Xabar yuborishda xato: {e}")
            await asyncio.sleep(game_times.day_time)
            game = await Game.get(id=game.id)
            if not game.is_active:
                break
            time_set, _ = await GameSetTime.get_or_create(chat_id=chat.chat_id)

            morning_phase.is_end = True
            await morning_phase.save()
            if game.mode not in ["para x classic", "para x super", "para x mega"]:
                try: await geroys_action_result(players, morning_phase, bot, chat)
                except Exception as e: print(f"Xabar yuborishda xato: {e}")
            await safe_send_message(bot, 
                chat.chat_id,
                f"<b>Aybdorlarni aniqlash va jazolash vaqti keldi.</b>\nOvoz berish uchun  {time_set.vote_time} sekund\n<a href='{BOT_URL}'>Ovoz berish</a>",
                parse_mode="HTML",
                reply_markup=bot_link_markup,
                disable_web_page_preview=True
            )

            day_phase = await GamePhase.create(game=game, number=day, phase_type="day")
            await reset_player_flags(game)

            if game.mode in ["para x classic", "para x super", "para x mega"]:
                paralar = await check_paralar_lst(bot, chat, paralar, day_phase)
            try:
                from utils.day_actions import day_action
                await day_action(message, players, phase=day_phase, bot=bot)
            except Exception as e:
                print(f"Kunduzgi harakatlarni boshlashda xato: {e}")
            await asyncio.sleep(game_times.vote_time)
            game = await Game.get(id=game.id).prefetch_related("chat")
            if not game.is_active:
                break

            day_phase.is_end = True
            await day_phase.save()
            afternoon_phase = await GamePhase.create(game=game, number=day, phase_type="afternoon")
            joker_selected = await GamePlayer.filter(game=game, should_choose_card=True).first()
            
            if joker_selected and joker_selected.role == RoleNames.OVCHI:
                joker_selected.should_choose_card = False
                await joker_selected.save()
                await safe_send_message(bot, 
                    chat.chat_id,
                    f"🤡 Jokerni xafa qilishdi!",
                    parse_mode="HTML"
                )
            try:
                from utils.day_actions import vote_like_action
                await vote_like_action(phase=day_phase, bot=bot, chat=chat, new_phase=afternoon_phase)
            except Exception as e:
                print(f"Ovoz berish natijalarini ko'rsatishda xato: {e}")
            game = await Game.get(id=game.id).prefetch_related("chat")
            if not game.is_active:
                break
            
            afternoon_phase.is_end = True
            await afternoon_phase.save()
            

            game.phase = "night"
            await game.save()
            await GamePlayer.filter(game=game, is_alive=True, is_sleep=True).update(is_sleep=False)
            joker_selected = await GamePlayer.filter(game=game, should_choose_card=True, is_alive=True).first()
            if joker_selected:
                await joker_selected.fetch_related("user")
                await safe_send_message(bot, 
                    joker_selected.user.user_id,
                    f"🤡 Siz joker yuborgan kartalardan birini tanlashingiz kerak edi. Lekin, tanlamadingiz! Keyin, jokerning jahli chiqdi va sizni o'ldirdi!",
                    parse_mode="HTML",
                )
                await safe_send_message(bot, 
                    chat.chat_id,
                    f"🤡 {joker_selected.user.mention} joker kartasini tanlamadi va o'ldirildi!\n\nU edi {role_display(joker_selected.role)}!",
                    parse_mode="HTML",
                )
                joker_selected.should_choose_card = False
                joker_selected.is_alive = False
                joker_selected.deaded_at = datetime.now(timezone.utc)
                await joker_selected.save()
                await assign_new_role(joker_selected, afternoon_phase, bot, chat)

            
    await GamePlayer.filter(game=game).update(is_alive=False)
    all_phases = await GamePhase.filter(game=game).all()
    await remove_game_redis(chat.chat_id)
    for phase in all_phases:
        actions = await Action.filter(phase=phase).all()
        for action in actions:
            await action.delete()
        await phase.delete()
    
def check_mafialar_list(mafiyalar: List[GamePlayer]) -> bool:
    if not mafiyalar:
        return False
    for player in mafiyalar:
        if player.role in [RoleNames.DON]:
            return True
    return False

async def announce_game_result(game: Game, bot: Bot, chat: Chat, winner_roles: List[str], zombilar=False, para=False, para_winners=None, vsgame=False, winning_team=None, real_mode=False):
    all_players = await GamePlayer.filter(game=game).prefetch_related("user")
    
    end_time = datetime.now(timezone.utc)
    created_at = game.created_at
    duration = end_time - created_at
    minutes = max(int(duration.total_seconds() // 60), 0)
    players_ball = await PlayersGameBall.filter(game=game).prefetch_related("player").all()
    players_ball_dict = defaultdict(int)
    for player_ball in players_ball:
        players_ball_dict[player_ball.player] = player_ball.ball
    role_checks = [
        (RoleNames.QASOSKOR, "is_really_winner"),
        (RoleNames.SUIDSID, "osildi"),
        (RoleNames.GAZABDOR, "is_really_winner"),
        (RoleNames.SEHRGAR, None),
        (RoleNames.AFERIST, None),
        (RoleNames.QAROQCHI, None),
    ]
    winners, losers = [], []
            

    if not zombilar and not vsgame and not real_mode:
        if para and len(winner_roles) == 2:
            winners = para_winners

        for role_name, attr in role_checks:
            player = await GamePlayer.filter(game=game, role=role_name).first()
            if player and player not in winners:
                if attr:
                    if getattr(player, attr):
                        winner_roles.append(role_name)
                    else:
                        winner_roles = [r for r in winner_roles if r != role_name]
                else:
                    winner_roles.append(role_name)
            else:
                winner_roles = [r for r in winner_roles if r != role_name]

    random.shuffle(all_players)

    for player in all_players:
        if not vsgame and not real_mode:
            if player.role in winner_roles and player not in winners:
                if player.role in [RoleNames.SUIDSID, RoleNames.QASOSKOR, RoleNames.GAZABDOR]:
                    condition_attr = "osildi" if player.role == RoleNames.SUIDSID else "is_really_winner"
                    (winners if getattr(player, condition_attr) else losers).append(player)
                else:
                    (winners if player.is_alive else losers).append(player)
            else:
                if player not in winners:
                    losers.append(player)
        elif real_mode:
            if player.role in winner_roles and player not in winners:
                if player.role in [RoleNames.SUIDSID, RoleNames.QASOSKOR, RoleNames.GAZABDOR]:
                    condition_attr = "osildi" if player.role == RoleNames.SUIDSID else "is_really_winner"
                    (winners if getattr(player, condition_attr) else losers).append(player)
                else:
                    (winners if player.is_alive else losers).append(player)
            else:
                if player not in winners:
                    losers.append(player)
        else:
            if player.team == winning_team:
                winners.append(player)
            else:
                losers.append(player)

    # Osilgan Suidsid har doim shaxsiy g'olib bo'ladi
    for player in all_players:
        if player.role == RoleNames.SUIDSID and getattr(player, "osildi", False):
            if player in losers:
                losers.remove(player)
            if player not in winners:
                winners.append(player)

    async def update_profile(player, is_winner, ball=0):
        await player.fetch_related("user")
        status = True
        try:
            tg_user = await bot.get_chat_member(chat_id=chat.chat_id, user_id=player.user.user_id)
            status = tg_user.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR, ChatMemberStatus.MEMBER]
        except Exception:
            pass
        
        reward = (20 if status else 10) if is_winner else (5 if status else 0)
        profile, _ = await Profile.get_or_create(user=player.user)
        profile.dollar += reward
        profile.wins += 1 if is_winner else 0
        profile.games_count += 1
        await profile.save()
        
        try:
            from utils.others import send_game_over_profile
            await send_game_over_profile(
                bot=bot,
                user_id=player.user.user_id,
                full_name=player.user.full_name,
                is_winner=is_winner,
                reward=reward
            )
        except Exception as e:
            logger.error(f"Profile yuborishda xato: {e}")


        player.win = is_winner
        await player.save()
    winners_top = []
    for winner in winners:
        winners_top.append((len(all_players) * 2 - len(winners)  + players_ball_dict[winner], winner))
    winners_top.sort(key=lambda x: x[0])
    await asyncio.gather(*(update_profile(p, True, ball)  for ball, p in winners_top))
    await asyncio.gather(*(update_profile(p, False, -len(winners)) for p in losers))
    vip_map_result = {}
    try:
        result_uids = [getattr(p, "user_id", None) for p in all_players]
        result_uids = [u for u in result_uids if u is not None]
        if result_uids:
            vip_rows_result = await VipUser.filter(user_id__in=result_uids).values_list("user_id", "emoji_id", "emoji_char")
            vip_map_result = {row[0]: (row[1], row[2]) for row in vip_rows_result}
    except Exception:
        vip_map_result = {}

    def _vip_name(p):
        prefix = build_vip_prefix(*vip_map_result[p.user_id]) if getattr(p, "user_id", None) in vip_map_result else ""
        return f"{prefix}{p.user.mention}"

    if vsgame:
        colors_dct = TeamCOlors.all_colors_dict()
        winners_text = "\n".join(f"{colors_dct[p[1].team]}{i}. {_vip_name(p[1])} — {role_display(p[1].role)}" for i, p in enumerate(winners_top, 1)) or "—"
        losers_text = "\n".join(f"{colors_dct[p.team]}{i}. {_vip_name(p)} — {role_display(p.role)}" for i, p in enumerate(losers, len(winners) + 1)) or "—"
    else:
        winners_text = "\n".join(f"{i}. {_vip_name(p)} — {role_display(p.role)}" for i, p in enumerate(winners, 1)) or "—"
        losers_text = "\n".join(f"{i}. {_vip_name(p)} — {role_display(p.role)}" for i, p in enumerate(losers, len(winners) + 1)) or "—"

    await safe_send_message(bot, 
        chat.chat_id,
        f"""
<b>O'yin tugadi!</b>

<b>G'oliblar:</b>
{winners_text}

<b>Qolgan o'yinchilar:</b>
{losers_text}

<i>O'yin davomiyligi: {minutes} minut</i>
""",
        parse_mode="HTML"
    )
    try:
        from utils.database import redis_client
        await redis_client.delete(f"game:{game.id}:actors")
    except Exception:
        pass

async def create_vs_game_handler(message: Message, bot: Bot):
    me = await bot.get_me()
    gaming_set, _ = await GamingOnChat.get_or_create(chat_id=message.chat.id, defaults={"bot_id": me.id})
    if not gaming_set.can_gaming:
        await message.answer(f"<b>⚠️ {message.from_user.mention_html()} bu guruhda o'yin o'ynash mumkin emas!</b>", parse_mode="HTML")
        return
    if message.chat.type not in ["group", "supergroup"]:
        return await message.answer("Bu buyruq faqat guruhda ishlaydi.")

    user, _ = await User.get_or_create(
        user_id=message.from_user.id,
        defaults={
            "full_name": message.from_user.full_name if message.from_user.full_name else "",
            "mention": message.from_user.mention_html()
        }
    )
    profile, _ = await Profile.get_or_create(
        user=user, 
        defaults={
            "dollar": 0,
            "diamond": 0,
            "himoya": 0,
            "qotildan_himoya": 0,
            "osishdan_himoya": 0,
            "miltiq": 0,
            "wins": 0,
            "games_count": 0 
        })

    chat, _ = await Chat.get_or_create(
        chat_id=message.chat.id,
        defaults={"title": message.chat.title, "type": message.chat.type}
    )

    cmd_perm, _ = await CommandPermissionsChat.get_or_create(
        chat_id=chat.chat_id,
        defaults={
            "game_cmd": "admin",
            "start_cmd": "admin",
            "stop_cmd": "admin",
            "top1_cmd": "admin",
            "top7_cmd": "admin",
            "top30_cmd": "admin",
            "gtop1_cmd": "admin",
            "gtop7_cmd": "admin",
            "gtop30_cmd": "admin",
            "extend_cmd": "admin"
        }
    )
    game_perm = getattr(cmd_perm, "game_cmd", "admin")
    member = await bot.get_chat_member(chat.chat_id, message.from_user.id)
    allowed = False
    if message.from_user.id in ADMINS or member.status == ChatMemberStatus.CREATOR:
        allowed = True
    elif game_perm == "admin":
        allowed = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    elif game_perm == "member":
        allowed = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR, ChatMemberStatus.MEMBER]
    elif game_perm == "ega":
        allowed = member.status in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]
    if not allowed:
        return
    teams_count = message.text[-1] if message.text[-1].isdigit() else 2
    if int(teams_count) < 2: 
        return
    old_game = await Game.filter(chat=chat, is_active=True).first()
    if old_game:
        if old_game.phase == "waiting":
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=old_game.message_id)
            except Exception:
                pass
            # Reset timer and update list
            game_times, _ = await GameSetTime.get_or_create(chat_id=chat.chat_id)
            need_spawn = (chat.chat_id not in game_timers)
            game_timers[chat.chat_id] = {
                'expiry': asyncio.get_event_loop().time() + game_times.reg_time,
                'warned': False,
                'paused': False,
                'game_id': old_game.id,
                'message': message
            }
            if need_spawn:
                create_task(auto_start_timer(chat.chat_id, old_game.id, bot))
            refresh_txt = f"O'yin yangilandi! Taymer qayta ishga tushdi ({game_times.reg_time} soniya)."
            await update_players_list(old_game, bot, new_msg=True, refresh_msg=refresh_txt)
            return
        else:
            await message.answer("⚠️ Bu guruhda allaqachon faol o'yin ketmoqda! Yangi o'yin boshlash uchun avval /stop bilan uni to'xtating.")
            return
    gmode = await GameModeSet.filter(chat_id=chat.chat_id).first()
    if not gmode:
        gmode = await GameModeSet.create(chat_id=chat.chat_id, mode_name="super")
    elif gmode.mode_name == "classic":
        gmode.mode_name = "super"
        await gmode.save()
    me = await bot.get_me()
    game = await Game.create(chat=chat, creator=user, phase="waiting", message_id=0, mode=f"{gmode.mode_name}:vsgame{teams_count}", bot_id=me.id)
    join_markup = join_vsgame_button(game_id=game.id, team_count=int(teams_count))
    msg = await message.answer(
        f"<b>Ro'yxatdan o'tish boshlandi!</b>",
        reply_markup=join_markup,
        parse_mode="HTML"
    )

    try:
        await msg.pin()
    except Exception:
        pass

    game.message_id = msg.message_id
    await game.save()

    # Start auto-start timer
    game_times, _ = await GameSetTime.get_or_create(chat_id=chat.chat_id)
    expiry = asyncio.get_event_loop().time() + game_times.reg_time
    game_timers[chat.chat_id] = {
        'expiry': expiry,
        'warned': False,
        'paused': False,
        'game_id': game.id,
        'message': message
    }
    create_task(auto_start_timer(chat.chat_id, game.id, bot))

async def create_game_handler(message: Message, bot: Bot):
    me = await bot.get_me()
    gaming_set, _ = await GamingOnChat.get_or_create(chat_id=message.chat.id, defaults={"bot_id": me.id})
    if not gaming_set.can_gaming:
        await message.answer(f"<b>⚠️ {message.from_user.mention_html()} bu guruhda o'yin o'ynash mumkin emas!</b>", parse_mode="HTML")
        return
    if message.chat.type not in ["group", "supergroup"]:
        return await message.answer("Bu buyruq faqat guruhda ishlaydi.")

    user, _ = await User.get_or_create(
        user_id=message.from_user.id,
        defaults={
            "full_name": message.from_user.full_name if message.from_user.full_name else "",
            "mention": message.from_user.mention_html()
        }
    )
    profile, _ = await Profile.get_or_create(
        user=user, 
        defaults={
            "dollar": 0,
            "diamond": 0,
            "himoya": 0,
            "qotildan_himoya": 0,
            "osishdan_himoya": 0,
            "miltiq": 0,
            "wins": 0,
            "games_count": 0 
        })

    chat, _ = await Chat.get_or_create(
        chat_id=message.chat.id,
        defaults={"title": message.chat.title, "type": message.chat.type}
    )

    cmd_perm, _ = await CommandPermissionsChat.get_or_create(
        chat_id=chat.chat_id,
        defaults={
            "game_cmd": "admin",
            "start_cmd": "admin",
            "stop_cmd": "admin",
            "top1_cmd": "admin",
            "top7_cmd": "admin",
            "top30_cmd": "admin",
            "gtop1_cmd": "admin",
            "gtop7_cmd": "admin",
            "gtop30_cmd": "admin",
            "extend_cmd": "admin"
        }
    )
    game_perm = getattr(cmd_perm, "game_cmd", "admin")
    member = await bot.get_chat_member(chat.chat_id, message.from_user.id)
    allowed = False
    if message.from_user.id in ADMINS or member.status == ChatMemberStatus.CREATOR:
        allowed = True
    elif game_perm == "admin":
        allowed = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    elif game_perm == "member":
        allowed = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR, ChatMemberStatus.MEMBER]
    elif game_perm == "ega":
        allowed = member.status in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]
    if not allowed:
        return

    old_game = await Game.filter(chat=chat, is_active=True).first()
    if old_game:
        if old_game.phase == "waiting":
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=old_game.message_id)
            except Exception:
                pass
            # Reset timer and update list
            game_times, _ = await GameSetTime.get_or_create(chat_id=chat.chat_id)
            need_spawn = (chat.chat_id not in game_timers)
            game_timers[chat.chat_id] = {
                'expiry': asyncio.get_event_loop().time() + game_times.reg_time,
                'warned': False,
                'paused': False,
                'game_id': old_game.id,
                'message': message
            }
            if need_spawn:
                create_task(auto_start_timer(chat.chat_id, old_game.id, bot))
            refresh_txt = f"O'yin yangilandi! Taymer qayta ishga tushdi ({game_times.reg_time} soniya)."
            await update_players_list(old_game, bot, new_msg=True, refresh_msg=refresh_txt)
            return
        else:
            await message.answer("⚠️ Bu guruhda allaqachon faol o'yin ketmoqda! Yangi o'yin boshlash uchun avval /stop bilan uni to'xtating.")
            return
    gmode = await GameModeSet.filter(chat_id=chat.chat_id).first()
    if not gmode:
        gmode = await GameModeSet.create(chat_id=chat.chat_id, mode_name="super")
    elif gmode.mode_name == "classic":
        gmode.mode_name = "super"
        await gmode.save()
    
    me = await bot.get_me()
    game = await Game.create(chat=chat, creator=user, phase="waiting", message_id=0, mode=gmode.mode_name, bot_id=me.id)
    join_markup = await join_game_button(game.id)
    msg = await message.answer(
        f"<b>Ro'yxatdan o'tish boshlandi!</b>",
        reply_markup=join_markup,
        parse_mode="HTML"
    )

    try:
        await msg.pin()
    except Exception:
        pass

    game.message_id = msg.message_id
    await game.save()

    # Start auto-start timer
    game_times, _ = await GameSetTime.get_or_create(chat_id=chat.chat_id)
    expiry = asyncio.get_event_loop().time() + game_times.reg_time
    game_timers[chat.chat_id] = {
        'expiry': expiry,
        'warned': False,
        'paused': False,
        'game_id': game.id,
        'message': message
    }
    create_task(auto_start_timer(chat.chat_id, game.id, bot))

async def create_nick_game_handler(message: Message, bot: Bot):
    me = await bot.get_me()
    gaming_set, _ = await GamingOnChat.get_or_create(chat_id=message.chat.id, defaults={"bot_id": me.id})
    if not gaming_set.can_gaming:
        await message.answer(f"<b>⚠️ {message.from_user.mention_html()} bu guruhda o'yin o'ynash mumkin emas!</b>", parse_mode="HTML")
        return
    if message.chat.type not in ["group", "supergroup"]:
        return await message.answer("Bu buyruq faqat guruhda ishlaydi.")
    if len(message.text.split()[1]) > 10:
        return await message.answer("Iltimos, 10 ta belgidan kam bo'lgan nik kiriting.")
    user, _ = await User.get_or_create(
        user_id=message.from_user.id,
        defaults={
            "full_name": message.from_user.full_name if message.from_user.full_name else "",
            "mention": message.from_user.mention_html()
        }
    )
    profile, _ = await Profile.get_or_create(
        user=user, 
        defaults={
            "dollar": 0,
            "diamond": 0,
            "himoya": 0,
            "qotildan_himoya": 0,
            "osishdan_himoya": 0,
            "miltiq": 0,
            "wins": 0,
            "games_count": 0 
        })

    chat, _ = await Chat.get_or_create(
        chat_id=message.chat.id,
        defaults={"title": message.chat.title, "type": message.chat.type}
    )

    cmd_perm, _ = await CommandPermissionsChat.get_or_create(
        chat_id=chat.chat_id,
        defaults={
            "game_cmd": "admin",
            "start_cmd": "admin",
            "stop_cmd": "admin",
            "top1_cmd": "admin",
            "top7_cmd": "admin",
            "top30_cmd": "admin",
            "gtop1_cmd": "admin",
            "gtop7_cmd": "admin",
            "gtop30_cmd": "admin",
            "extend_cmd": "admin"
        }
    )
    game_perm = getattr(cmd_perm, "game_cmd", "admin")
    member = await bot.get_chat_member(chat.chat_id, message.from_user.id)
    allowed = False
    if message.from_user.id in ADMINS or member.status == ChatMemberStatus.CREATOR:
        allowed = True
    elif game_perm == "admin":
        allowed = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    elif game_perm == "member":
        allowed = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR, ChatMemberStatus.MEMBER]
    elif game_perm == "ega":
        allowed = member.status in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]
    if not allowed:
        return

    old_game = await Game.filter(chat=chat, is_active=True).first()
    if old_game:
        if old_game.phase == "waiting":
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=old_game.message_id)
            except Exception:
                pass
            # Reset timer and update list
            game_times, _ = await GameSetTime.get_or_create(chat_id=chat.chat_id)
            need_spawn = (chat.chat_id not in game_timers)
            game_timers[chat.chat_id] = {
                'expiry': asyncio.get_event_loop().time() + game_times.reg_time,
                'warned': False,
                'paused': False,
                'game_id': old_game.id,
                'message': message
            }
            if need_spawn:
                create_task(auto_start_timer(chat.chat_id, old_game.id, bot))
            refresh_txt = f"O'yin yangilandi! Taymer qayta ishga tushdi ({game_times.reg_time} soniya)."
            await update_players_list(old_game, bot, new_msg=True, refresh_msg=refresh_txt)
            return
        else:
            await message.answer("⚠️ Bu guruhda allaqachon faol o'yin ketmoqda! Yangi o'yin boshlash uchun avval /stop bilan uni to'xtating.")
            return
    gmode = await GameModeSet.filter(chat_id=chat.chat_id).first()
    if not gmode:
        gmode = await GameModeSet.create(chat_id=chat.chat_id, mode_name="super")
    elif gmode.mode_name == "classic":
        gmode.mode_name = "super"
        await gmode.save()
    nik = message.text.split()[1][:10] if len(message.text.split()) > 1 else "Player"
    # nik keyinchalik HTML xabarlarga to'g'ridan-to'g'ri (escape qilinmagan holda)
    # qo'shiladi — "<", ">", "&" belgilari bo'lsa Telegram ENTITY_TEXT_INVALID
    # xatosi bilan xabarni butunlay rad etadi (masalan tungi o'yinchilar ro'yxati
    # yoki "kimga ovoz berasiz" xabari yuborilmay qoladi). Shu sabab tozalaymiz.
    nik = html.escape(nik, quote=False)
    if not nik:
        nik = "Player"
    game = await Game.create(chat=chat, creator=user, phase="waiting", message_id=0, mode=gmode.mode_name + ">" + nik)
    join_markup = await join_game_button(game.id)
    msg = await message.answer(
        f"<b>Ro'yxatdan o'tish boshlandi!</b>",
        reply_markup=join_markup,
        parse_mode="HTML"
    )

    try:
        await msg.pin()
    except Exception:
        pass

    game.message_id = msg.message_id
    await game.save()

    # Start auto-start timer
    game_times, _ = await GameSetTime.get_or_create(chat_id=chat.chat_id)
    expiry = asyncio.get_event_loop().time() + game_times.reg_time
    game_timers[chat.chat_id] = {
        'expiry': expiry,
        'warned': False,
        'paused': False,
        'game_id': game.id,
        'message': message
    }
    create_task(auto_start_timer(chat.chat_id, game.id, bot))

import asyncio
join_locks = {}

async def _join_game_handler_core(message: Message, bot: Bot, state: FSMContext):
    await state.update_data(xatolar_soni=0)
 
    game_id = message.text.split("_")[1]
    try:
        game = await Game.get(id=game_id)
    except:
        await message.answer("Kechirasiz, bu o'yinga qo'shilib bo'lmaydi!")
        return
    if not game or not (game.phase == "waiting" and game.is_active):
        await message.answer("Kechirasiz, bu o'yinga qo'shilib bo'lmaydi!")
        return
    await game.fetch_related("chat")
    chat = game.chat
    user, _ = await User.get_or_create(
        user_id=message.from_user.id,
        defaults={
            "full_name": message.from_user.full_name if message.from_user.full_name else "",
            "mention": message.from_user.mention_html()
        }
    )

    profile, _ = await Profile.get_or_create(
        user=user,
        defaults={
            "dollar": 0,
            "diamond": 0,
            "himoya": 0,
            "qotildan_himoya": 0,
            "osishdan_himoya": 0,
            "miltiq": 0,
            "wins": 0,
            "games_count": 0
        }
    )
    
    old_player = await GamePlayer.filter(user=user, game=game).first()
    if old_player and old_player.is_alive:
        if len(game.mode.split(":")) == 2:
            color_name = message.text.split("_")[-1]
            if old_player.team != color_name:
                old_player.team = color_name
                await old_player.save()
                await message.answer(f"Siz jamoangizni almashtirdingiz!", reply_markup=go_group_button(chat.invite_link))
                try: await update_players_list(game, bot)    
                except: pass
                return
        await message.answer("SIz bu o'yinga qo'shilgansiz!", reply_markup=go_group_button(chat.invite_link))
        return

    # Avvalgi o'yinlarni tekshirish - bir xil guruh yoki tugagan o'yindan osib qo'ydi chiqiqlari bermaymiz
    old_alive_players = await GamePlayer.filter(user=user, is_alive=True).prefetch_related("game", "game__chat").all()
    for op in old_alive_players:
        if not op.game or not op.game.is_active or op.game.phase in ("end", "ended", "finished", "stopped"):
            op.is_alive = False
            await op.save()
        elif op.game.chat and int(op.game.chat.chat_id) == int(chat.chat_id):
            # Bir xil guruhdagi eski o'yin -> osib qo'ydi xabarisiz statusni o'chirish
            op.is_alive = False
            await op.save()
        elif op.game.is_active and int(op.game.chat.chat_id) != int(chat.chat_id):
            # Boshqa (A guruh) faol o'yindan chiqib B guruhga o'tganda A guruhga o'zini osdi e'loni boradi
            try:
                await leave_game(message, bot, force=True)
            except Exception:
                pass
    if len(game.mode.split(":")) == 2:
        color_name = message.text.split("_")[-1]
        teams_count = int(game.mode.split(">")[0][-1])
        team_players = await GamePlayer.filter(game=game, team=color_name, is_alive=True).count()
        max_team_players = (await GroupMoreSet.get_or_create(chat_id=chat.chat_id))[0].max_players // teams_count
        if team_players >= max_team_players:
            await message.answer(f"Kechirasiz, bu jamoasi to'lgan!", reply_markup=go_group_button(chat.invite_link))
            return
        player, _ = await GamePlayer.get_or_create(user=user, game=game, role='', team=color_name)
        await message.answer("Siz o'yinga muvaffaqiyatli qo'shildingiz!", reply_markup=go_group_button(chat.invite_link))
    else:
        player, _ = await GamePlayer.get_or_create(user=user, game=game, role='')
        player_ball, _ = await PlayersGameBall.get_or_create(player=player, game=game)
        await message.answer("Siz o'yinga muvaffaqiyatli qo'shildingiz!", reply_markup=go_group_button(chat.invite_link))
    await update_players_list(game, bot)

    if chat.chat_id not in game_timers and game.phase == "waiting":
        game_times, _ = await GameSetTime.get_or_create(chat_id=chat.chat_id)
        expiry = asyncio.get_event_loop().time() + game_times.reg_time
        game_timers[chat.chat_id] = {
            'expiry': expiry,
            'warned': False,
            'paused': False,
            'game_id': game.id,
            'message': message
        }
        create_task(auto_start_timer(chat.chat_id, game.id, bot))

    players = await GamePlayer.filter(game=game).all()
    more_set, _ = await GroupMoreSet.get_or_create(chat_id=chat.chat_id)
    if len(players) >= more_set.max_players:
        if await create_or_get_game_redis(game.chat.chat_id):
            return
    
        await starting_game(game=game, message=message, start=True, bot=bot)

async def tungi_harakat(message: Message, phase: GamePhase, bot: Bot, vsgame=False, nik=None):
    await phase.fetch_related("game")
    game = phase.game
    players = await GamePlayer.filter(game=game, is_alive=True).prefetch_related("user")

    for player in players:
        role = player.role
        user_id = player.user.user_id

        # Aktyor har tunda yangi faol rolga kiradi
        if role == RoleNames.AKTYOR:
            active_pool = [
                RoleNames.KOMISSAR, RoleNames.DOKTOR, RoleNames.DON, RoleNames.MAFIA,
                RoleNames.QOTIL, RoleNames.DAYDI, RoleNames.KEZUVCHI, RoleNames.ADVOKAT,
                RoleNames.QAROQCHI, RoleNames.SEHRGAR, RoleNames.AFERIST, RoleNames.ZANJIR,
                RoleNames.REVERSER
            ]
            role = random.choice(active_pool)
            await safe_send_message(
                bot, user_id,
                f"🎭 <b>Aktyor</b>: Siz bu tun <b>{role_display(role)}</b> roliga kirdingiz!",
                parse_mode="HTML"
            )

        # Taqlidchi (Mimic): Birinchi halok bo'lgan o'yinchining rolini egallaydi
        if role == RoleNames.TAQLIDCHI:
            if getattr(player, "copied_role", None):
                role = player.copied_role
            else:
                dead_players = await GamePlayer.filter(game=game, is_alive=False).exclude(role=RoleNames.TAQLIDCHI).order_by("-deaded_at").all()
                if dead_players:
                    new_role = dead_players[0].role
                    player.copied_role = new_role
                    player.role = new_role
                    await player.save()
                    role = new_role
                    await safe_send_message(
                        bot, user_id,
                        f"🎭 <b>Taqlidchi</b>: Siz halok bo'lgan o'yinchining rolini egalladingiz!\nYangi rolingiz: <b>{role_display(new_role)}</b>",
                        parse_mode="HTML"
                    )
                else:
                    await safe_send_message(
                        bot, user_id,
                        "🎭 <b>Taqlidchi</b>: Hali hech kim halok bo'lmadi — birinchi o'lik o'yinchining rolini kuting.",
                        parse_mode="HTML"
                    )
                    continue

        if role == RoleNames.KOMISSAR:
            kb = await action_buttons(user_id=user_id, role=role, players=players, phase_id=phase.id, vsgame=vsgame, kom=True, nik=nik)
            await safe_send_message(bot, user_id, f"🕵🏼 <b>{role_display(role)}</b>: Harakat turini tanlang:", reply_markup=kb, parse_mode="HTML")
        elif role == RoleNames.DOKTOR:
            kb = await action_buttons(user_id=user_id, role=role, players=players, phase_id=phase.id, vsgame=vsgame, davo=True, nik=nik)
            await safe_send_message(bot, user_id, f"👨🏼‍⚕️ <b>{role_display(role)}</b>: Kimni davolamoqchisiz?", reply_markup=kb, parse_mode="HTML")
        elif role == RoleNames.DON:
            kb = await action_buttons(user_id=user_id, role=role, players=players, phase_id=phase.id, vsgame=vsgame, otish=True, nik=nik)
            await safe_send_message(bot, user_id, f"🤵🏻 <b>{role_display(role)}</b>: Kimni o'ldirmoqchisiz?", reply_markup=kb, parse_mode="HTML")
        elif role == RoleNames.MAFIA:
            kb = await action_buttons(user_id=user_id, role=role, players=players, phase_id=phase.id, vsgame=vsgame, otish=True, nik=nik)
            await safe_send_message(bot, user_id, f"🤵🏼 <b>{role_display(role)}</b>: Kimni o'ldirmoqchisiz?", reply_markup=kb, parse_mode="HTML")
        elif role == RoleNames.QOTIL:
            kb = await action_buttons(user_id=user_id, role=role, players=players, phase_id=phase.id, vsgame=vsgame, otish=True, nik=nik)
            await safe_send_message(bot, user_id, f"🔪 <b>{role_display(role)}</b>: Kimni o'ldirmoqchisiz?", reply_markup=kb, parse_mode="HTML")
        elif role == RoleNames.DAYDI:
            kb = await action_buttons(user_id=user_id, role=role, players=players, phase_id=phase.id, vsgame=vsgame, daydi=True, nik=nik)
            await safe_send_message(bot, user_id, f"🧙‍♂️ <b>{role_display(role)}</b>: Kimning uyiga bormoqchisiz?", reply_markup=kb, parse_mode="HTML")
        elif role == RoleNames.KEZUVCHI:
            kb = await action_buttons(user_id=user_id, role=role, players=players, phase_id=phase.id, vsgame=vsgame, kezuv=True, nik=nik)
            await safe_send_message(bot, user_id, f"💃 <b>{role_display(role)}</b>: Kimni uxlatmoqchisiz?", reply_markup=kb, parse_mode="HTML")
        elif role == RoleNames.ADVOKAT:
            kb = await action_buttons(user_id=user_id, role=role, players=players, phase_id=phase.id, vsgame=vsgame, adv=True, nik=nik)
            await safe_send_message(bot, user_id, f"👨🏼‍💼 <b>{role_display(role)}</b>: Kimga himoya bermoqchisiz?", reply_markup=kb, parse_mode="HTML")
        elif role == RoleNames.QAROQCHI:
            kb = await qaroqchi_action_button(role=role, phase_id=phase.id)
            await safe_send_message(bot, user_id, f"⚔️ <b>{role_display(role)}</b>: Harakatni tanlang:", reply_markup=kb, parse_mode="HTML")
        elif role == RoleNames.SEHRGAR:
            kb = await action_buttons(user_id=user_id, role=role, players=players, phase_id=phase.id, vsgame=vsgame, nik=nik)
            await safe_send_message(bot, user_id, f"🧙‍♂️ <b>{role_display(role)}</b>: Kimni sehrlamoqchisiz?", reply_markup=kb, parse_mode="HTML")
        elif role == RoleNames.AFERIST:
            kb = await action_buttons(user_id=user_id, role=role, players=players, phase_id=phase.id, vsgame=vsgame, nik=nik)
            await safe_send_message(bot, user_id, f"🤹🏻 <b>{role_display(role)}</b>: Kimning rolini almashtirmoqchisiz?", reply_markup=kb, parse_mode="HTML")
        elif role == RoleNames.ZANJIR:
            kb = await action_buttons(user_id=user_id, role=role, players=players, phase_id=phase.id, vsgame=vsgame, nik=nik)
            await safe_send_message(bot, user_id, f"⛓ <b>{role_display(role)}</b>: Kimni zanjirlamoqchisiz?", reply_markup=kb, parse_mode="HTML")
        elif role == RoleNames.REVERSER:
            kb = await action_buttons(user_id=user_id, role=role, players=players, phase_id=phase.id, vsgame=vsgame, nik=nik)
            await safe_send_message(bot, user_id, f"🔄 <b>{role_display(role)}</b>: Harakatini burmoqchi bo'lgan 1-o'yinchini tanlang:", reply_markup=kb, parse_mode="HTML")
        elif role == RoleNames.KONCHI:
            konlar = get_konchi_konlari()
            kb = await konchi_button(role=role, phase_id=phase.id, konlar=konlar)
            await safe_send_message(bot, user_id, f"👷🏻‍♂️ <b>{role_display(role)}</b>: Qaysi konni qazasiz?", reply_markup=kb, parse_mode="HTML")
        elif role == RoleNames.QORIQCHI:
            kb = await action_buttons(user_id=user_id, role=role, players=players, phase_id=phase.id, vsgame=vsgame, nik=nik)
            await safe_send_message(bot, user_id, f"🛡 <b>{role_display(role)}</b>: Kimni qo'riqlamoqchisiz?", reply_markup=kb, parse_mode="HTML")
        elif role == RoleNames.OVCHI:
            kb = await action_buttons(user_id=user_id, role=role, players=players, phase_id=phase.id, vsgame=vsgame, otish=True, nik=nik)
            await safe_send_message(bot, user_id, f"🥷 <b>{role_display(role)}</b>: Nishonni belgilang:", reply_markup=kb, parse_mode="HTML")
        elif role == RoleNames.AYGOQCHI:
            kb = await action_buttons(user_id=user_id, role=role, players=players, phase_id=phase.id, vsgame=vsgame, nik=nik)
            await safe_send_message(bot, user_id, f"🦇 <b>{role_display(role)}</b>: Kimni kuzatmoqchisiz?", reply_markup=kb, parse_mode="HTML")
        elif role == RoleNames.JURNALIST:
            kb = await action_buttons(user_id=user_id, role=role, players=players, phase_id=phase.id, vsgame=vsgame, nik=nik)
            await safe_send_message(bot, user_id, f"👩🏼‍💻 <b>{role_display(role)}</b>: Kim haqida ma'lumot yig'moqchisiz?", reply_markup=kb, parse_mode="HTML")
        elif role == RoleNames.SOTQIN:
            kb = await action_buttons(user_id=user_id, role=role, players=players, phase_id=phase.id, vsgame=vsgame, nik=nik)
            await safe_send_message(bot, user_id, f"🤓 <b>{role_display(role)}</b>: Kimni sotmoqchisiz?", reply_markup=kb, parse_mode="HTML")
        elif role == RoleNames.GAZABDOR:
            kb = await action_buttons(user_id=user_id, role=role, players=players, phase_id=phase.id, vsgame=vsgame, nik=nik)
            await safe_send_message(bot, user_id, f"🧌 <b>{role_display(role)}</b>: Kimga g'azabingizni qaratmoqchisiz?", reply_markup=kb, parse_mode="HTML")
        elif role == RoleNames.XOYIN:
            kb = await action_buttons(user_id=user_id, role=role, players=players, phase_id=phase.id, vsgame=vsgame, nik=nik)
            await safe_send_message(bot, user_id, f"👺 <b>{role_display(role)}</b>: Kimni mafiya deb hisoblaysiz?", reply_markup=kb, parse_mode="HTML")
        elif role == RoleNames.ZOMBI:
            kb = await action_buttons(user_id=user_id, role=role, players=players, phase_id=phase.id, vsgame=vsgame, otish=True, nik=nik)
            await safe_send_message(bot, user_id, f"🧟 <b>{role_display(role)}</b>: Kimni tishlamoqchisiz?", reply_markup=kb, parse_mode="HTML")
        else:
            await safe_send_message(
                bot, user_id,
                f"🌙 <b>Tun bo'ldi.</b>\nRolingiz: {role_display(role)}\n\nBu tunda maxsus harakatingiz yo'q — tonggacha kuting.",
                parse_mode="HTML"
            )

async def join_game_handler(message: Message, bot: Bot, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in join_locks:
        join_locks[user_id] = asyncio.Lock()
    async with join_locks[user_id]:
        await _join_game_handler_core(message, bot, state)

async def start_game_handler(message: Message, bot: Bot, state: FSMContext = None):
    chat, _ = await Chat.get_or_create(
        chat_id=message.chat.id, 
        defaults={"title": message.chat.title, "type": message.chat.type}
    )
    
    me = await bot.get_me()
    gaming_set, _ = await GamingOnChat.get_or_create(chat_id=message.chat.id, defaults={"bot_id": me.id})
    if not gaming_set.can_gaming:
        await message.answer(
            f"<b>⚠️ {message.from_user.mention_html()} bu guruhda o'yin o'ynash mumkin emas!</b>", 
            parse_mode="HTML"
        )
        return
    
    cmd_perm, _ = await CommandPermissionsChat.get_or_create(
        chat_id=chat.chat_id,
        defaults={
            "game_cmd": "admin",
            "start_cmd": "admin",
            "stop_cmd": "admin",
            "top1_cmd": "admin",
            "top7_cmd": "admin",
            "top30_cmd": "admin",
            "gtop1_cmd": "admin",
            "gtop7_cmd": "admin",
            "gtop30_cmd": "admin"
        }
    )
    start_perm = getattr(cmd_perm, "start_cmd", "admin")
    member = await bot.get_chat_member(chat.chat_id, message.from_user.id)
    allowed = False
    if message.from_user.id in ADMINS or member.status == ChatMemberStatus.CREATOR:
        allowed = True
    elif start_perm == "admin":
        allowed = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    elif start_perm == "member":
        allowed = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR, ChatMemberStatus.MEMBER]
    elif start_perm == "ega":
        allowed = member.status in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]
    
    if not allowed:
        return

    game = await Game.filter(chat=chat, is_active=True, phase="waiting").first()
    if not game:
        await message.answer("⚠️ Guruhda faol kutilayotgan o'yin topilmadi!")
        return

    players_count = await GamePlayer.filter(game=game, is_alive=True).count()
    if players_count < 4:
        await message.answer(f"❗ O'yinni boshlash uchun kamida 4 ta ishtirokchi kerak! (Hozir: {players_count} ta)")
        return

    await starting_game(game=game, message=message, start=True, bot=bot)

async def extend_game_timer(message: Message, bot: Bot):
    chat, _ = await Chat.get_or_create(
        chat_id=message.chat.id, 
        defaults={"title": message.chat.title, "type": message.chat.type}
    )
    
    cmd_perm, _ = await CommandPermissionsChat.get_or_create(
        chat_id=chat.chat_id,
        defaults={"extend_cmd": "admin"}
    )
    extend_perm = getattr(cmd_perm, "extend_cmd", "admin")
    member = await bot.get_chat_member(chat.chat_id, message.from_user.id)
    allowed = False
    if message.from_user.id in ADMINS or member.status == ChatMemberStatus.CREATOR:
        allowed = True
    elif extend_perm == "admin":
        allowed = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    elif extend_perm == "member":
        allowed = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR, ChatMemberStatus.MEMBER]
    elif extend_perm == "ega":
        allowed = member.status in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]
    
    if not allowed:
        return

    game = await Game.filter(chat=chat, is_active=True, phase="waiting").first()
    if not game:
        await message.answer("⚠️ Guruhda faol kutilayotgan o'yin topilmadi!")
        return

    now = asyncio.get_event_loop().time()
    two_hours = 7200

    if chat.chat_id in game_timers:
        game_timers[chat.chat_id]['expiry'] = now + two_hours
        game_timers[chat.chat_id]['warned'] = True
    else:
        game_timers[chat.chat_id] = {
            'expiry': now + two_hours,
            'warned': True,
            'paused': False,
            'game_id': game.id,
            'message': message
        }
        create_task(auto_start_timer(chat.chat_id, game.id, bot))

    await safe_send_message(
        bot,
        chat.chat_id,
        "⏱ <b>Ro'yxatdan o'tish vaqti cheksizga uzaytirildi!</b>",
        parse_mode="HTML"
    )

async def stop_game_handler(message: Message, bot: Bot):
    chat, _ = await Chat.get_or_create(
        chat_id=message.chat.id, 
        defaults={"title": message.chat.title, "type": message.chat.type}
    )
    cmd_perm, _ = await CommandPermissionsChat.get_or_create(
        chat_id=chat.chat_id,
        defaults={
            "game_cmd": "admin",
            "start_cmd": "admin",
            "stop_cmd": "admin",
            "top1_cmd": "admin",
            "top7_cmd": "admin",
            "top30_cmd": "admin",
            "gtop1_cmd": "admin",
            "gtop7_cmd": "admin",
            "gtop30_cmd": "admin"
        }
    )
    stop_perm = getattr(cmd_perm, "stop_cmd", "admin")
    member = await bot.get_chat_member(chat.chat_id, message.from_user.id)
    allowed = False
    if message.from_user.id in ADMINS or member.status == ChatMemberStatus.CREATOR:
        allowed = True
    elif stop_perm == "admin":
        allowed = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    elif stop_perm == "member":
        allowed = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR, ChatMemberStatus.MEMBER]
    elif stop_perm == "ega":
        allowed = member.status in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]
    
    if not allowed:
        return

    game = await Game.filter(chat=chat, is_active=True).first()
    if not game:
        await message.answer("⚠️ Ushbu guruhda faol o'yin topilmadi.")
        return

    game.is_active = False
    game.phase = "end"
    await game.save()

    if chat.chat_id in game_timers:
        del game_timers[chat.chat_id]

    await message.answer("🛑 O'yin to'xtatildi!")

async def update_players_list(game: Game, bot: Bot, new_msg=False, refresh_msg=None):
    players = await GamePlayer.filter(game=game, is_alive=True)
    message_text = f"<b>Ro'yxatdan o'tish davom etmoqda!</b>\nRo'yhatdan o'tganlar:\n\n"
    if len(game.mode.split(":")) == 2:
        colors_dict = TeamCOlors.all_colors_dict()
        teams = {}
        for player in players:
            if player.team not in teams:
                teams[player.team] = []
            await player.fetch_related("user")
            print(player.team)
            teams[player.team].append(player.user.mention)
        for team, team_players in teams.items():
            for i, player in enumerate(team_players):
                message_text += f"{colors_dict.get(team, team)} {i + 1}. {player}\n"
        join_markup = join_vsgame_button(game.id, int(game.mode.split(">")[0][-1]))
    else:
        c = 0
        lst = []
        random.shuffle(players)

        vip_map = {}
        try:
            uids = [p.user_id for p in players]
            if uids:
                vip_rows = await VipUser.filter(user_id__in=uids).values_list("user_id", "emoji_id", "emoji_char")
                vip_map = {row[0]: (row[1], row[2]) for row in vip_rows}
        except Exception:
            vip_map = {}

        for player in players:
            c += 1
            await player.fetch_related("user")
            prefix = build_vip_prefix(*vip_map[player.user_id]) if player.user_id in vip_map else ""
            lst.append(f"{prefix}{player.user.mention}")
        message_text += ", ".join(lst)
        join_markup = await join_game_button(game.id)
    message_text += f"\n\nJami: <b>{len(players)}</b> ta"
    if refresh_msg:
        message_text += f"\n\n🔄 {refresh_msg}"
    await game.fetch_related("chat")    
    if new_msg:
        try: 
            msg = await safe_send_message(bot, chat_id=game.chat.chat_id, text=message_text, parse_mode="HTML", reply_markup=join_markup)
            game.message_id = msg.message_id
            try: await msg.pin()
            except: pass
            await game.save()
        except: pass
    else:
        try:
            msg = await bot.edit_message_text(chat_id=game.chat.chat_id, message_id=game.message_id, text=message_text, parse_mode="HTML", reply_markup=join_markup)
            game.message_id = msg.message_id
            try: await msg.pin()
            except: pass
            await game.save()
        except: pass

def maxsus_raqamni_tartiblash(player: GamePlayer) -> int:
    try: return player.maxsus_raqam
    except: return 0

async def view_players_list(
    players: List[GamePlayer],
    title: str = "<b>Tirik o'yinchilar:</b>",
    caption: str = "",
    guruhlash: bool = False,
    add_roles_text=False, 
    view_life=False,
    gmode: str = ""
) -> str:
    if not players:
        return "<b>Tirik o'yinchi qolmadi!</b>\n"

    players_text = f"{title}\n"

    vip_map = {}
    try:
        # Diqqat: player.user_id — GamePlayer'ning xom FK ustuni (User.id, ICHKI PK),
        # Telegram user_id EMAS. VipUser.user_id ham xuddi shu ichki PK'ga ishora qiladi,
        # shuning uchun ikkalasini ham shu xil "id fazosida" solishtiramiz.
        uids = [getattr(p, "user_id", None) for p in players]
        uids = [u for u in uids if u is not None]
        if uids:
            vip_rows = await VipUser.filter(user_id__in=uids).values_list("user_id", "emoji_id", "emoji_char")
            vip_map = {row[0]: (row[1], row[2]) for row in vip_rows}
    except Exception:
        vip_map = {}

    actor_ids = []
    if players:
        try:
            first_p = players[0]
            await first_p.fetch_related("game")
            actor_ids = await redis_client.smembers(f"game:{first_p.game.id}:actors")
        except:
            pass

    tinchlar = [
        RoleNames.KOMISSAR, RoleNames.SERJANT,
        RoleNames.DAYDI, RoleNames.DOKTOR, RoleNames.KEZUVCHI, RoleNames.FUQARO, RoleNames.HAMSHIRA,
        RoleNames.SOTQIN, RoleNames.JANOB, RoleNames.OMADLI, RoleNames.XOYIN,
        RoleNames.QORIQCHI, RoleNames.ZANJIR
    ]
    mafialar = [
        RoleNames.DON, RoleNames.MAFIA, RoleNames.ADVOKAT, RoleNames.OVCHI,
        RoleNames.JURNALIST, RoleNames.AYGOQCHI
    ]
    yakkalar = [
        RoleNames.AFERIST, RoleNames.BORI, RoleNames.GAZABDOR,
        RoleNames.QOTIL, RoleNames.SEHRGAR,
        RoleNames.SUIDSID, RoleNames.QASOSKOR, RoleNames.QAROQCHI, RoleNames.AKTYOR, RoleNames.JIN
    ]

    roles = []
    valid_players_count = 0
    
    # Team-based game check - faqat birinchi o'yinchini emas, barcha o'yinchilarni tekshirish
    has_teams = any(hasattr(player, 'team') and player.team for player in players)
    
    try:
        sorted_players = sorted(players, key=maxsus_raqamni_tartiblash)
    except Exception as e:
        print(f"Sorting error: {e}")
        sorted_players = players  # Agar sorting muvaffaqiyatsiz bo'lsa, asl ro'yxatni ishlatamiz

    for player in sorted_players:
        try:
            # O'yinchi ma'lumotlarini tekshirish
            if not player:
                continue
                
            nik = gmode.split(">")[1] if len(gmode.split(">")) > 1 else None
            if not hasattr(player, 'user') or not player.user:
                player_mention = "👤 Noma'lum o'yinchi"
            elif nik:
                player_mention = nik
            else:
                try:
                    player_mention = getattr(player.user, 'mention', f"👤 {getattr(player.user, 'full_name', 'ishtirokchi')}")
                    vip_uid = getattr(player, 'user_id', None)
                    if vip_uid in vip_map:
                        player_mention = f"{build_vip_prefix(*vip_map[vip_uid])}{player_mention}"
                except Exception:
                    player_mention = "👤 O'yinchi"
            
            # Maxsus raqamni tekshirish
            try:
                maxsus_raqam = getattr(player, 'maxsus_raqam', None) or (valid_players_count + 1)
            except Exception:
                maxsus_raqam = valid_players_count + 1
            valid_players_count += 1
            
            # Life foizini tekshirish
            life_text = ""
            if view_life:
                try:
                    life = getattr(player, 'life', 100)
                    if life < 100:
                        life_text = f" {life}%"
                except Exception:
                    pass
            
            # Team-based yoki oddiy format
            if has_teams:
                try:
                    team = getattr(player, 'team', 'Nomalum')
                    team_color = TeamCOlors.all_colors_dict().get(team, '🔹')
                    players_text += f"{team_color} {maxsus_raqam}. {player_mention}{life_text}\n"
                except Exception as e:
                    print(f"Team format error for player {maxsus_raqam}: {e}")
                    players_text += f"🔹 {maxsus_raqam}. {player_mention}{life_text}\n"
            else:
                players_text += f"{maxsus_raqam}. {player_mention}{life_text}\n"
            
            # Role ni xavfsiz tarzda qo'shish
            try:
                role = getattr(player, 'role', None)
                if str(player.id) in actor_ids:
                    role = RoleNames.AKTYOR
                roles.append(role if role else "Nomaʼlum")
            except Exception:
                roles.append("Nomaʼlum")
            
        except Exception as e:
            print(f"Error processing player: {e}")
            # Xatolik bo'lgan holatda ham o'yinchini ro'yxatga qo'shamiz
            try:
                fallback_number = valid_players_count + 1
                players_text += f"❓ {fallback_number}. 👤 O'yinchi (ma'lumot yuklanmadi)\n"
                roles.append("Nomaʼlum")
                valid_players_count += 1
            except Exception:
                continue  # Agar bu ham ishlamasa, o'tkazib yuboramiz
    
    # Agar hech qanday o'yinchi ko'rsatilmagan bo'lsa
    if valid_players_count == 0:
        return f"{title}\n❌ O'yinchilar ma'lumotini yuklashda xatolik yuz berdi.\n<b>Jami:</b> {len(players)} ta\n\n{caption}"
    
    if not add_roles_text:
        return players_text + "\n" + caption

    # Role counter - xavfsiz tarzda
    role_counter = {}
    try:
        for role in roles:
            role_key = str(role) if role else "Nomaʼlum"
            role_counter[role_key] = role_counter.get(role_key, 0) + 1
    except Exception as e:
        print(f"Role counting error: {e}")
        # Agar role counting ishlamasa, role ma'lumotisiz qaytaramiz
        players_text += f"<b>Jami:</b> {valid_players_count} ta\n\n{caption}"
        return players_text

    try:
        if guruhlash:
            grouped_counts = {
                "Tinchlar": [],
                "Mafiyalar": [],
                "Yakkalar": []
            }

            for role, count in role_counter.items():
                try:
                    if role in tinchlar:
                        grouped_counts["Tinchlar"].append((role, count))
                    elif role in mafialar:
                        grouped_counts["Mafiyalar"].append((role, count))
                    elif role in yakkalar:
                        grouped_counts["Yakkalar"].append((role, count))
                except Exception:
                    continue

            players_text += "\n"
            for group, items in grouped_counts.items():
                if items:
                    try:
                        total_count = sum(count for _, count in items)
                        players_text += f"<b>{group} - {total_count}</b>:\n"
                        role_texts = []
                        for role, count in items:
                            try:
                                role_text = f"{role_display(role)} - {count}" if count > 1 else str(role_display(role))
                                role_texts.append(role_text)
                            except Exception:
                                role_texts.append("Noma'lum")
                        players_text += ", ".join(role_texts)
                        players_text += "\n\n"
                    except Exception as e:
                        print(f"Group formatting error: {e}")
                        continue
        else:
            try:
                role_texts = []
                for role, count in sorted(role_counter.items(), key=lambda x: str(x[0])):
                    try:
                        role_text = f"{role_display(role)} - {count}" if count > 1 else str(role_display(role))
                        role_texts.append(role_text)
                    except Exception:
                        role_texts.append("Noma'lum")
                
                roles_count_text = ", ".join(role_texts)
                players_text += f"\n<b>Ulardan:</b> {roles_count_text}\n\n"
            except Exception as e:
                print(f"Role text formatting error: {e}")
                players_text += "\n<b>Ulardan:</b> Ma'lumotni yuklashda xatolik\n\n"
    except Exception as e:
        print(f"Role display error: {e}")
        # Agar role ko'rsatishda xatolik bo'lsa, role ma'lumotisiz davom etamiz

    players_text += f"<b>Jami:</b> {valid_players_count} ta\n\n{caption}"

    return players_text

async def stop_voting_mafias(phase: GamePhase, bot: Bot, chat: Chat):
    try:
        await phase.fetch_related("game")
        don = await GamePlayer.filter(role=RoleNames.DON, is_alive=True, game=phase.game).first().prefetch_related("user")
        mafs = await GamePlayer.filter(role=RoleNames.MAFIA, is_alive=True, game=phase.game).all().prefetch_related("user")

        maf_actions = await Action.filter(phase=phase, result="mafdan ovoz").all()
        don_action = await Action.filter(phase=phase, result="dondan ovoz").first()
        colors_dcit = TeamCOlors.all_colors_dict()
        target = None
        shooter = None

        if don and don_action and don_action.target_id:
            await don_action.fetch_related("target")
            target = don_action.target
            shooter = don
        elif maf_actions:
            targets = [a.target_id for a in maf_actions if a.target_id]
            if targets:
                vote_counts = Counter(targets)
                top_target_id, vote_count = vote_counts.most_common(1)[0]
                target = await GamePlayer.filter(id=top_target_id).first()
                
                if mafs:
                    shooter = mafs[0]
                elif don:
                    shooter = don
                    
                if don and (not don_action or not don_action.target_id):
                    await safe_send_message(
                        bot,
                        chat.chat_id,
                        "Don uxlab qolgan shekilli, lekin nozir yordamchi - Mafia uning uchun o'lja tanladi!",
                        parse_mode="HTML"
                    )

        if target:
            try:
                await target.fetch_related("user")
            except Exception:
                pass

        if target and shooter:
            has_miltiq = False
            if don_action and getattr(don_action, "with_miltiq", False) and target.id == don_action.target_id:
                has_miltiq = True
            elif maf_actions:
                for act in maf_actions:
                    if act.target_id == target.id and getattr(act, "with_miltiq", False):
                        has_miltiq = True
                        break
                        
            await Action.create(
                phase=phase,
                actor=shooter,
                target=target,
                action_type="otish",
                result="o'ldi",
                with_miltiq=has_miltiq
            )

            target_name = target.user.full_name if (target and target.user) else "O'yinchi"
            target_team = getattr(target, 'team', None)
            color_prefix = colors_dcit.get(target_team, '') if ('vsgame' in phase.game.mode and target_team) else ''
            
            kill_msg = f"Mafiyalarning ovoz berishi natijasida {color_prefix}<b>{target_name}</b> o'ldirildi!"

            for maf in mafs:
                if maf and maf.user:
                    await safe_send_message(bot, 
                        maf.user.user_id,
                        kill_msg,
                        parse_mode="HTML",
                        reply_markup=go_group_button(chat.invite_link)
                    )
            if don and don.user:
                await safe_send_message(bot, 
                    don.user.user_id,
                    kill_msg,
                    parse_mode="HTML",
                    reply_markup=go_group_button(chat.invite_link)
                )
        if not target:
            no_kill_msg = "Mafiyalar kelisha olmadi va natijada hech kim o'ldirilmadi!"
            if don and don.user:
                await safe_send_message(bot, 
                    don.user.user_id,
                    no_kill_msg,
                    parse_mode="HTML",
                    reply_markup=go_group_button(chat.invite_link)
                )
            for maf in mafs:
                if maf and maf.user:
                    await safe_send_message(bot, 
                        maf.user.user_id,
                        no_kill_msg,
                        parse_mode="HTML",
                        reply_markup=go_group_button(chat.invite_link)
                    )
    except Exception as e:
        logger.error(f"stop_voting_mafias xatosi: {e}")

async def view_night_results(phase: GamePhase, game: Game, bot: Bot, chat: Chat, vsgame=False):
    """
    Optimizatsiyalangan kecha natijalari ko'rsatish funksiyasi
    """

    # Qora Materiya — Void Swap kunini kamaytirish (tong)
    try:
        from utils.qora_materiya import decrement_void_swap_days
        await decrement_void_swap_days(game)
    except Exception as e:
        logger.error(f"QM void swap decrement error: {e}")

    # 1. BARCHA ACTION LARNI OLDINDAN YUKLASH
    # order_by shart: pastdagi "actor bo'yicha oxirgisini qoldirish" filtri
    # qatorlar kelish tartibiga tayanadi, ORDER BY siz Postgres buni kafolatlamaydi.
    actions = await Action.filter(phase=phase).order_by("id").prefetch_related(
        "actor__user", "target__user", "actor", "target"
    ).all()
    
    # So'nggi so'z uchun vaqt sozlamasini olish
    try:
        from models.game_set import GameSetTime
        _game_time_set = await GameSetTime.get_or_none(chat_id=chat.chat_id)
        _word_time = _game_time_set.word_time if _game_time_set else 45
    except Exception:
        _word_time = 45
    
    asl_actions = actions.copy()
    
    # Unique action larni filterlash - har bir actor uchun faqat eng oxirgisini qoldiramiz.
    # Jin orqali berilgan tilak (jin_qotil, jin_hayot) alohida hisoblanadi.
    filtered_actions = []
    seen_keys = set()
    
    for action in reversed(actions):
        key = (action.actor_id, "jin" if action.action_type in ("jin_qotil", "jin_hayot") else "normal")
        if key not in seen_keys:
            seen_keys.add(key)
            filtered_actions.append(action)
            
    filtered_actions.reverse()
    actions = filtered_actions
    nik = game.mode.split(">")[1] if ">" in game.mode else ""
    # 2. BARCHA ZARURIY PLAYER VA PROFILE LARNI OLDINDAN YUKLASH
    all_player_ids = set()
    for action in actions:
        all_player_ids.add(action.actor_id)
        all_player_ids.add(action.target_id)
    
    # Player va user ma'lumotlarini cache qilish
    players_cache = {}
    profiles_cache = {}
    
    if all_player_ids:
        # Barcha zaruriy playerlarni yuklash
        players = await GamePlayer.filter(id__in=all_player_ids).prefetch_related("user").all()
        players_cache = {p.id: p for p in players}
        
        # Barcha user ID larni olish
        user_ids = {p.user_id for p in players}
        
        # Barcha zaruriy profilelarni yuklash
        profiles = await Profile.filter(user_id__in=user_ids).all()
        profiles_cache = {p.user_id: p for p in profiles}
    
    # 3. CONSTANTS VA INITIAL VARIABLES
    MAFIA_ROLES = {
        RoleNames.DON, RoleNames.MAFIA, RoleNames.ADVOKAT, RoleNames.OVCHI,
        RoleNames.JURNALIST, RoleNames.AYGOQCHI
    }
    
    ACTIVE_ROLES = {
        RoleNames.DON, RoleNames.DOKTOR, RoleNames.KOMISSAR,
        RoleNames.DAYDI, RoleNames.KEZUVCHI, RoleNames.ADVOKAT, RoleNames.QOTIL,
        RoleNames.OVCHI, RoleNames.GAZABDOR, RoleNames.AYGOQCHI, RoleNames.QORIQCHI,
        RoleNames.SEHRGAR, RoleNames.AKTYOR, RoleNames.JIN, RoleNames.KONCHI,
        RoleNames.AFERIST, RoleNames.QAROQCHI, RoleNames.JURNALIST, RoleNames.SOTQIN,
        RoleNames.XOYIN, RoleNames.ZANJIR, RoleNames.ZOMBI
    }
    
    colors_dict = TeamCOlors.all_colors_dict()
    
    # State variables
    saved_user = None
    doctor_user = None
    kimyogar_saved_user = None
    kimyogar_user = None
    labarant_saved_user = None
    labarant_user = None
    robin_ketdi = False
    minior_player = None
    
    attackers_roles = []
    kimyogar_attackers_roles = []
    labarant_attackers_roles = []
    daydi_info = {}
    kezuvchi_targets = {}
    advokat_himoyalar = {}
    qasoskor_otganlar = {}
    minior_targets = {}
    qoriqchi_saves = {}
    minaga_tushganlar = []
    awardees_dict = defaultdict(int)
    muhim_olimlar = []
    killed_players = []
    dead_player_ids = set()
    
    # Update queue lar (bulk update uchun)
    profile_updates = []
    player_updates = []
    action_updates = []
    
    # 2.5 SEHRGAR ROLE SWAP (Hamma narsadan oldin)
    sehr_action = next((a for a in actions if a.action_type == "sehr"), None)
    if sehr_action:
        target1 = players_cache.get(sehr_action.target_id)
        try:
            target2_id = int(sehr_action.result)
        except:
            target2_id = None
        target2 = players_cache.get(target2_id)
        
        if target1 and target2 and target1.is_alive and target2.is_alive:
            # Aktyor statuslarini tekshirish va almashtirish
            is_actor1 = await redis_client.sismember(f"game:{game.id}:actors", target1.id)
            is_actor2 = await redis_client.sismember(f"game:{game.id}:actors", target2.id)
            
            if is_actor1 and not is_actor2:
                await redis_client.srem(f"game:{game.id}:actors", target1.id)
                await redis_client.sadd(f"game:{game.id}:actors", target2.id)
            elif is_actor2 and not is_actor1:
                await redis_client.srem(f"game:{game.id}:actors", target2.id)
                await redis_client.sadd(f"game:{game.id}:actors", target1.id)

            role1 = target1.role
            role2 = target2.role
            target1.role = role2
            target2.role = role1
            player_updates.append(target1)
            player_updates.append(target2)
            
            # Actionlardagi actor va target rollarini ham yangilash (mantiqiy xatolar bo'lmasligi uchun)
            for a in actions:
                if a.actor_id == target1.id: a.actor.role = target1.role
                elif a.actor_id == target2.id: a.actor.role = target2.role
                if a.target_id == target1.id: a.target.role = target1.role
                elif a.target_id == target2.id: a.target.role = target2.role

            # Xabarlarda Aktyor rolni to'g'ri ko'rsatish
            msg_role1 = RoleNames.AKTYOR if is_actor2 else target1.role
            msg_role2 = RoleNames.AKTYOR if is_actor1 else target2.role
            
            try:
                await safe_send_message(bot, target1.user.user_id, f"🔮 Sehrgar sizning rolingizni almashtirdi! Yangi rolingiz: <b>{msg_role1}</b>", parse_mode="HTML")
                await safe_send_message(bot, target2.user.user_id, f"🔮 Sehrgar sizning rolingizni almashtirdi! Yangi rolingiz: <b>{msg_role2}</b>", parse_mode="HTML")
            except:
                pass
    
    # 3.5 BOSH KOMISSAR SHOSHILINCH ARREST — hibsga olingan o'yinchining harakatlari bekor qilinadi
    kom_arrest_player = next(
        (p for p in players_cache.values()
         if p.role == RoleNames.KOMISSAR and getattr(p, "kom_arrest_pid", None) and p.is_alive),
        None
    )
    if kom_arrest_player:
        arrested_pid = kom_arrest_player.kom_arrest_pid
        arrested_player = players_cache.get(arrested_pid)
        kom_skip_types = {"kom_wire", "kom_profile", "kom_arrest", "kom_himoya", "kom_signal", "skype", "otmen"}
        for action in actions:
            if action.actor_id == arrested_pid and action.action_type not in kom_skip_types:
                action.result = "otmen"
                action.action_type = "otmen"
                action_updates.append(action)
        kom_arrest_player.kom_arrest_pid = None
        player_updates.append(kom_arrest_player)
        if arrested_player:
            await safe_send_message(bot, arrested_player.user.user_id, "⚡ Siz bu tunda Bosh Komissar tomonidan hibsga olindingiz — harakatingiz bloklandi!", parse_mode="HTML")
        await safe_send_message(
            bot, kom_arrest_player.user.user_id,
            f"⚡ Arrest bajarildi. {arrested_player.user.full_name if arrested_player else ''} ning harakati bloklandi.",
            parse_mode="HTML"
        )

    # 3.6 BOSH KOMISSAR SIMLI QURILMA — kuzatilayotgan o'yinchi haqida tongda hisobot
    kom_wire_player = next(
        (p for p in players_cache.values()
         if p.role == RoleNames.KOMISSAR and getattr(p, "kom_wire_target_pid", None) and p.is_alive),
        None
    )
    if kom_wire_player:
        wire_pid = kom_wire_player.kom_wire_target_pid
        wire_target = players_cache.get(wire_pid)
        if wire_target:
            wire_lines = []
            wire_skip_types = {"skype", "otmen", "kom_wire", "kom_profile", "kom_arrest", "kom_himoya", "kom_signal"}
            for a in actions:
                if a.action_type in wire_skip_types:
                    continue
                if a.actor_id == wire_pid:
                    tgt_name = a.target.user.full_name if a.target else "?"
                    wire_lines.append(f"• <b>Harakati:</b> <code>{a.action_type}</code> → {tgt_name}")
                elif a.target_id == wire_pid:
                    act_name = a.actor.user.full_name if a.actor else "?"
                    wire_lines.append(f"• <b>Unga keldi:</b> <code>{a.action_type}</code> ← {act_name}")
            if wire_lines:
                report = f"📡 <b>Simli Qurilma Hisoboti: {wire_target.user.full_name}</b>\n\n" + "\n".join(wire_lines)
            else:
                report = f"📡 <b>Simli Qurilma Hisoboti: {wire_target.user.full_name}</b>\n\n<i>Bu tunda hech qanday aloqa qayd etilmadi.</i>"
            await safe_send_message(bot, kom_wire_player.user.user_id, report, parse_mode="HTML")
        kom_wire_player.kom_wire_target_pid = None
        player_updates.append(kom_wire_player)

    # 4. KIMYOGAR HIMOYASINI BIRINCHI QAYTA ISHLASH
    kimyogar_saves = {a.target_id for a in actions if a.action_type == "hayot"}
    weapons_set, _ = await GameSetWeapons.get_or_create(chat_id=chat.chat_id)
    # Kimyogar saved user va kimyogar user ni aniqlash
    for action in actions:
        if action.action_type == "hayot":
            kimyogar_saved_user = action.target.user
            kimyogar_user = action.actor.user
            break
    
    # Kimyogar himoyasini action larga qo'llash
    for target_id in kimyogar_saves:
        target_player = players_cache.get(target_id)
        if not target_player:
            continue
            
        for action in actions:
            if (action.target_id != target_id or action.action_type in ("hayot", "dondan ovoz") or
                action.result in ("hayot", "dondan ovoz") or
                action.actor_id == target_id):
                continue
                
            if getattr(action, "with_miltiq", False):
                continue
                
            # Action ni bekor qilish
            action.result = "otmen"
            action.action_type = "otmen"
            action_updates.append(action)
            
            attacker = players_cache.get(action.actor_id)
            if (attacker and action.result != "dondan ovoz" and
                attacker.role not in [RoleNames.MAFIA, RoleNames.QAROQCHI] and 
                attacker.is_alive):
                
                # Message queue ga qo'shish
                await safe_send_message(bot, 
                    attacker.user.user_id,
                    "👨‍🔬 Ushbu ishtirokchi kimyogar himoyasida!",
                    parse_mode="HTML",
                    reply_markup=go_group_button(chat.invite_link)
                )
                kimyogar_attackers_roles.append(attacker.role)
                awardees_dict[kimyogar_user] += 3
    
    # 5. ASOSIY ACTION LARNI QAYTA ISHLASH
    doctor_saves = set()
    labarant_saves = set()
    
    # Action type bo'yicha preliminary parsing
    for action in actions:
        if action.action_type == "davo":
            saved_user = action.target.user
            doctor_user = action.actor.user
            doctor_saves.add(action.target_id)
            
        elif action.action_type == "labarant":
            target = players_cache.get(action.target_id)
            if target and target.role in MAFIA_ROLES:
                labarant_saved_user = action.target.user
                labarant_user = action.actor.user
                labarant_saves.add(action.target_id)
        
        elif action.action_type == "jin_hayot":
            doctor_saves.add(action.target_id)
                
        elif action.action_type == "daydi":
            daydi_info[action.actor_id] = action.target_id
            
        elif action.action_type == "kezuv":
            kezuvchi_targets[action.actor_id] = action.target_id
            
        elif action.action_type == "advokat":
            advokat_himoyalar[action.target_id] = action.actor_id
            
        elif action.action_type == "minior":
            minior_targets[action.actor_id] = action.target_id
            minior_player = action.actor
        elif action.action_type == "qoriqchi":
            qoriqchi_saves[action.target_id] = action.actor
    
    # 6. MINIOR ACTIONLARINI QAYTA ISHLASH
    for actor_id, target_id in minior_targets.items():
        mina_target = players_cache.get(target_id)
        if not mina_target:
            continue
            
        # Mina targetga hujum qilganlarni topish
        attackers = [
            a for a in asl_actions
            if a.target_id == target_id and a.actor_id not in [actor_id, target_id] and a.result != "dondan ovoz"
        ]
        
        role_change_candidates = []
        
        for attack_action in attackers:
            # Action ni bekor qilish
            attack_action.result = "otmen"
            attack_action.action_type = "otmen"
            action_updates.append(attack_action)
            
            attacker = players_cache.get(attack_action.actor_id)
            if not attacker or attacker.role in [RoleNames.OVCHI, RoleNames.MAFIA]:
                continue
                
            if not attacker.is_alive:
                continue
                
            # Himoya tekshirish
            protected = False
            
            # Doctor himoyasi
            if saved_user and attacker.user.user_id == saved_user.user_id:
                attackers_roles.append(RoleNames.MINIOR)
                protected = True
            
            # Labarant himoyasi
            if labarant_saved_user and attacker.user.user_id == labarant_saved_user.user_id:
                labarant_attackers_roles.append(RoleNames.LABARANT)
                protected = True
            
            # Self himoya
            if (not protected and 
                getattr(attacker, "can_protection_self", True) and weapons_set.himoya):
                
                profile = profiles_cache.get(attacker.user_id)
                if profile and profile.himoya > 0 and profile.on_himoya and not getattr(game, 'qm_portlat_active', False):
                    profile.himoya -= 1
                    profile_updates.append(profile)
                    
                    attacker.can_protection_self = False
                    player_updates.append(attacker)
                    protected = True
                    
                    await safe_send_message(bot, 
                        attacker.user.user_id,
                        "🛡 Siz minaga tushdingiz, ammo himoya sizni qutqardi!",
                        parse_mode="HTML",
                        reply_markup=go_group_button(chat.invite_link)
                    )
                    await safe_send_message(bot, 
                        chat.chat_id,
                        "💫 Kimningdir himoyasi ishladi!"
                    )
            
            # Agar himoyalanmagan bo'lsa - o'ldirish
            if not protected:
                attacker.is_alive = False
                attacker.deaded_at = datetime.now(timezone.utc)
                attacker.is_sayed_last_word = False
                dead_player_ids.add(attacker.id)
                player_updates.append(attacker)
                
                minaga_tushganlar.append(attacker)
                
                if minior_player:
                    minior_player.is_really_winner = True
                    player_updates.append(minior_player)
                    awardees_dict[minior_player] += 3
                
                # Role change kerak bo'lganlarni yig'ish
                if attacker.role in [RoleNames.DON, RoleNames.KOMISSAR, RoleNames.DOKTOR]:
                    role_change_candidates.append(attacker)
        
        # Role assignment lar
        for candidate in role_change_candidates:
            muhim_olimlar.append((candidate, phase, bot, chat))

    # 7. KEZUVCHI ACTIONLARINI QAYTA ISHLASH
    blocked_targets = []
    
    for actor_id, target_id in kezuvchi_targets.items():
        actor = players_cache.get(actor_id)
        if not actor:
            continue
            
        # Doctor yoki labarant save qilgan bo'lsa
        if target_id in doctor_saves:
            attackers_roles.append(RoleNames.KEZUVCHI)
            continue
        elif target_id in labarant_saves:
            labarant_attackers_roles.append(RoleNames.KEZUVCHI)
            continue
        
        target_player = players_cache.get(target_id)
        if not target_player:
            continue
            
        # Ovchi kezuvchidan ta'sirlanmaydi
        if target_player.role in [RoleNames.OVCHI]:
            continue
            
        if not target_player.is_alive:
            continue
            
        # Doctor save tekshirish
        if saved_user and target_player.user.user_id == saved_user.user_id:
            attackers_roles.append(RoleNames.KEZUVCHI)
            continue
            
        # Labarant save tekshirish
        if labarant_saved_user and target_player.user.user_id == labarant_saved_user.user_id:
            labarant_attackers_roles.append(RoleNames.KEZUVCHI)
            continue
        
        # Dori himoyasi tekshirish
        profile = profiles_cache.get(target_player.user_id)
        if (getattr(target_player, "can_doridan_himoya", True) and profile and 
            profile.doridan_himoya > 0 and 
            profile.on_doridan_himoya and weapons_set.doridan_himoya):
            
            profile.doridan_himoya -= 1
            profile_updates.append(profile)
            target_player.can_doridan_himoya = False
            player_updates.append(target_player)
            
            await safe_send_message(bot, 
                target_player.user.user_id,
                "💊 Sizni doringiz kezuvchidan saqlab qoldi!",
                reply_markup=go_group_button(chat.invite_link)
            )
            continue
        
        # Kezuvchi ta'siri
        target_player.is_sleep = True
        player_updates.append(target_player)
        
        # Role-specific effects
        if target_player.role == RoleNames.DOKTOR:
            doctor_user = None
            saved_user = None
            doctor_saves = set()
        
        # Award berish
        if target_player.role in MAFIA_ROLES | {RoleNames.QOTIL, RoleNames.QAROQCHI}:
            awardees_dict[actor] += 5
            
        blocked_targets.append(target_id)
        
        await safe_send_message(bot, 
            target_player.user.user_id,
            "\"Ana 💊 dori ta'sir qila boshladi, bir kun uxlab qolding...\" – dedi 💃 Kezuvchi",
            parse_mode="HTML",
            reply_markup=go_group_button(chat.invite_link)
        )
    
    # Blocked playerlarning actionlarini filter qilish
    actions = [a for a in actions if a.actor_id not in blocked_targets]
    
    # 8. QOLGAN ACTIONLARNI QAYTA ISHLASH
    for action in actions:
        actor = players_cache.get(action.actor_id)
        target = players_cache.get(action.target_id)
        
        if not actor or not target:
            continue
        
        # FOTOPARATCHI ACTION
        if action.result == "fotoparatchi":
            if target.role == RoleNames.MAFIA:
                await safe_send_message(bot, 
                    actor.user.user_id,
                    f"Afsuski, {colors_dict.get(target.team, '') if vsgame else ''}{target.user.full_name if not nik else nik} bugun hech kimnikiga bormadi."
                )
                continue
                
            # Target ning actionini topish
            target_action = None
            for a in asl_actions:
                if a.actor_id == target.id:
                    target_action = a
                    break
            
            if target_action and target_action.actor_id != target_action.target_id:
                target_target = players_cache.get(target_action.target_id)
                if target_target:
                    if target.role in MAFIA_ROLES | {RoleNames.QOTIL, RoleNames.QAROQCHI}:
                        awardees_dict[actor] += 5
                    
                    await safe_send_message(bot, 
                        actor.user.user_id,
                        f"Siz {colors_dict.get(target.team, '') if vsgame else ''}{target.user.full_name if not nik else nik} tunda {colors_dict.get(target_target.team, '') if vsgame else ''}{target_target.user.full_name if not nik else nik}nikiga borganini rasmga oldingiz!"
                    )
                else:
                    await safe_send_message(bot, 
                        actor.user.user_id,
                        f"Afsuski, {colors_dict.get(target.team, '') if vsgame else ''}{target.user.full_name if not nik else nik} bugun hech kimnikiga bormadi."
                    )
            else:
                await safe_send_message(bot, 
                    actor.user.user_id,
                    f"Afsuski, {colors_dict.get(target.team, '') if vsgame else ''}{target.user.full_name if not nik else nik} bugun hech kimnikiga bormadi."
                )
            continue
        
        # KOLDUN PROTECT ACTION
        elif action.result == "kprotect":
            await safe_send_message(bot, 
                target.user.user_id,
                "⚡️ Bu kunda siz osilmaysiz, chunki, koldun sizni o'z himoyasiga oldi!"
            )
            continue
        
        # ZOMBI ACTION
        elif action.result == "zombi":
            if target.role in [RoleNames.OVCHI]:
                target.life -= 10
                player_updates.append(target)
                
                if target.life <= 0:
                    target.role = RoleNames.ZOMBI
                    await target.save()
                    await safe_send_message(bot, 
                        target.user.user_id,
                        f"🧟 Siz <b>{role_display(target.role)}</b>ga aylandingiz!",
                        parse_mode="HTML",
                        reply_markup=go_group_button(chat.invite_link)
                    )
                    awardees_dict[actor] += 10
            elif target.is_alive:
                if target.role in [RoleNames.DON, RoleNames.KOMISSAR, RoleNames.DOKTOR]:
                    muhim_olimlar.append((target, phase, bot, chat))
                elif target.role == RoleNames.ZOMBI:
                    continue
                target.role = RoleNames.ZOMBI
                player_updates.append(target)
                awardees_dict[actor] += 5
                
                await safe_send_message(bot, 
                    target.user.user_id,
                    f"🧟 Siz <b>{role_display(target.role)}</b>ga aylandingiz!",
                    parse_mode="HTML",
                    reply_markup=go_group_button(chat.invite_link)
                )
            continue
        
        # BOYOTA VA URISH ACTIONS
        if action.action_type == "qorbobo":
                await action.fetch_related("actor")
                await action.fetch_related("target")
                await action.target.fetch_related("user")
                await action.actor.fetch_related("user")            
                targ  = action.target
                actor = action.actor
                targ_prof = await Profile.get_or_none(user=targ.user)
                if targ_prof:
                    gifts = {
                        "qotildan_himoya": "⛑️ Qotildan himoya",
                        "osishdan_himoya": "⚖️ Ovozdan himoya",
                        "miltiq": "🔫 Miltiq",
                        "doridan_himoya": "💊 Doridan himoya",
                        "maska": "🎭 Maska",
                        "slip_himoya": "🪤 Sirpanishdan himoya",
                        "active_role": "🃏 Faol rol"
                    }

                    if action.result in gifts.keys():
                        setattr(targ_prof, action.result, getattr(targ_prof, action.result) + 1)
                        await targ_prof.save()
                        await safe_send_message(bot, 
                            targ.user.user_id,
                            f"🎅🏻 Qorbobo sizga {gifts[action.result]} sovg'a qildi!",
                            parse_mode="HTML",
                            reply_markup=go_group_button(chat.invite_link)
                        )
                        await safe_send_message(bot, 
                            actor.user.user_id,
                            f"🎅🏻 Siz {colors_dict[targ.team] if vsgame else ''}{targ.user.full_name if not nik else nik}'ga {gifts[action.result]} sovg'a qildingiz!",
                            parse_mode="HTML",
                            reply_markup=go_group_button(chat.invite_link)
                        )
                        awardees_dict[actor] += 2
                    else:
                        await ActiveRole.create(
                            profile=targ_prof,
                            role=action.result
                        )
                        await safe_send_message(bot, 
                            targ.user.user_id,
                            f"🎅🏻 Qorbobo sizga {action.result} sovg'a qildi!"
                            , parse_mode="HTML",
                            reply_markup=go_group_button(chat.invite_link)
                        )
                        await safe_send_message(bot, 
                            actor.user.user_id,
                            f"🎅🏻 Siz {colors_dict[targ.team] if vsgame else ''}{targ.user.full_name if not nik else nik}'ga 🃏 Faol rol sovg'a qildingiz!",
                            parse_mode="HTML",
                            reply_markup=go_group_button(chat.invite_link)
                        )
                        awardees_dict[actor] += 5
            
        elif action.result == "sirpanish" and action.action_type == "konchi_olim":
            if target.life > 0:
                target.life = 0
                target.is_alive = False
                target.deaded_at = datetime.now(timezone.utc)
                dead_player_ids.add(target.id)
                player_updates.append(target)
                killed_players.append((
                    target.user.mention,
                    target.role,
                    "Minada sirpanish",
                    target.user.user_id,
                    getattr(target, 'team', None)
                ))
            continue
            
        elif action.result in ("boyota", "urish"):
            if action.result == "urish":
                if target.life < 1:
                    target.is_alive = False
                    target.deaded_at = datetime.now(timezone.utc)
                    dead_player_ids.add(target.id)
                    player_updates.append(target)
                    
                    killed_players.append((
                        target.user.mention,
                        target.role,
                        actor.role,
                        target.user.user_id,
                        getattr(target, 'team', None)
                    ))
                    awardees_dict[actor] += 10
                continue
            
            # Boyota - sovg'a berish
            profile = profiles_cache.get(target.user_id)
            if profile:
                dollar = random.randint(1, 100)
                if dollar > 2:
                    profile.dollar += dollar
                    currency = "<tg-emoji emoji-id='5211062061932521090'>💵</tg-emoji>"
                else:
                    profile.diamond += dollar
                    currency = '<tg-emoji emoji-id="5210941235912552228">💎</tg-emoji>'
                
                profile_updates.append(profile)
                
                await safe_send_message(bot, 
                    target.user.user_id,
                    f"Sizga {role_display(actor.role)} {dollar} {currency} sovg'a qildi!!",
                    parse_mode="HTML"
                )
                await safe_send_message(bot, 
                    actor.user.user_id,
                    f"Siz {colors_dict.get(target.team, '') if vsgame else ''}{target.user.full_name if not nik else nik}'ga {dollar} {currency} sovg'a qildingiz!",
                    parse_mode="HTML"
                )
            continue
        
        # AYG'OQCHI ACTION
        elif action.action_type == "ayg'oqchi":
            profile = profiles_cache.get(target.user_id)

            if getattr(target, "kom_himoya_protected", False):
                await safe_send_message(bot, actor.user.user_id, "🛡 Bu o'yinchi Bosh Komissarning Himoya Dasturi ostida — tekshirib bo'lmadi!", parse_mode="HTML")
                continue

            if target.role in [RoleNames.JOKER]:
                kom_info = f"<b>{target.user.full_name}</b> - <b>{RoleNames.FUQARO}</b>"
            elif (profile and profile.hujjat > 0 and not getattr(game, 'qm_portlat_active', False) and
                  getattr(target, "can_document_self", False) and
                  target.role not in {RoleNames.DON, RoleNames.MAFIA, RoleNames.ADVOKAT, RoleNames.JURNALIST, RoleNames.FUQARO} and
                  profile.on_hujjat) and weapons_set.hujjat:
                
                kom_info = f"{colors_dict.get(target.team, '') if vsgame else ''}<b>{target.user.full_name}</b> - <b>{RoleNames.FUQARO}</b>"
                
                await safe_send_message(bot, 
                    target.user.user_id,
                    "📄🦇 Sizni Ayg'oqchi tekshirdi. Ammo, siz hujjatni ishga soldingiz!",
                    parse_mode="HTML",
                    reply_markup=go_group_button(chat.invite_link)
                )
            else:
                kom_info = f"{colors_dict.get(target.team, '') if vsgame else ''}<b>{target.user.full_name if not nik else nik}</b> - <b>{role_display(target.role)}</b>"
                awardees_dict[actor] += 3
                
                await safe_send_message(bot, 
                    target.user.user_id,
                    "🦇 Ayg'oqchi rolingizga juda qizziqdi!",
                    reply_markup=go_group_button(chat.invite_link)
                )
            
            # Ayg'oqchi va mafiyalarga xabar yuborish
            await safe_send_message(bot, actor.user.user_id, kom_info, parse_mode="HTML")
            
            # Mafiyalarga xabar
            mafia_players = await GamePlayer.filter(
                game=game,
                role__in=[RoleNames.DON, RoleNames.MAFIA, RoleNames.ADVOKAT],
                is_alive=True
            ).prefetch_related("user").all()
            
            for mafia in mafia_players:
                await safe_send_message(bot, mafia.user.user_id, kom_info, parse_mode="HTML")
            continue
            
        # O'LDIRISH ACTIONS
        if action.result in ("o'ldi", "qotil", "ovchi", "gazab", "labarant", "kdeath") or action.action_type == "jin_qotil":
            # Labarant save tekshirish
            if action.result == "labarant" and labarant_saved_user:
                continue
            
            # Robin tamom action
            if action.action_type == "robin_tamom":
                await safe_send_message(bot, 
                    chat.chat_id,
                    f"🔫 {role_display(actor.role)} {colors_dict.get(actor.team, '') if vsgame else ''}{actor.user.mention if not nik else nik} 2 marta fuqarolar tarafga hujum qildi va xatolarini kechira olmay o'z joniga qasd qildi!",
                    parse_mode="HTML"
                )
                actor.is_alive = False
                actor.deaded_at = datetime.now(timezone.utc)
                dead_player_ids.add(actor.id)
                player_updates.append(actor)
                killed_players.append((
                    actor.user.mention,
                    actor.role,
                    "O'zini o'zi o'ldirdi",
                    actor.user.user_id,
                    getattr(actor, 'team', None)
                ))
                robin_ketdi = True
            
            # Ovchi o'ldirilmaydi
            if target.role in [RoleNames.OVCHI]:
                continue
            
            # Bo'ri special case
            if target.role == RoleNames.BORI:
                if actor.role == RoleNames.KOMISSAR:
                    target.role = RoleNames.SERJANT
                    player_updates.append(target)
                    awardees_dict[actor] += 5
                    
                    await safe_send_message(bot,
                        chat.chat_id,
                        f"{role_display(RoleNames.BORI)} <b>{role_display(RoleNames.SERJANT)}</b>ga aylandi!",
                        parse_mode="HTML"
                    )
                    continue
                elif actor.role == RoleNames.DON:
                    target.role = RoleNames.MAFIA
                    player_updates.append(target)
                    awardees_dict[actor] += 5

                    await safe_send_message(bot,
                        chat.chat_id,
                        f"{role_display(RoleNames.BORI)} <b>{role_display(RoleNames.MAFIA)}</b>ga aylandi!",
                        parse_mode="HTML"
                    )
                    continue
            
            # Sehrgar special case
            if target.role == RoleNames.SEHRGAR:
                if actor.role not in [RoleNames.OVCHI, RoleNames.GAZABDOR]:
                    markup = await sehr_action_button(game.id, actor.id)
                    await safe_send_message(bot, 
                        target.user.user_id,
                        f"Sizni {actor.user.full_name if not nik else nik} {role_display(actor.role)} o'ldirishga urindi. Siz uni kechirasizmi?",
                        parse_mode="HTML",
                        reply_markup=markup
                    )
                    await safe_send_message(bot, 
                        chat.chat_id,
                        f"Tunda {role_display(actor.role)} {role_display(target.role)}ni o'ldirishga urindi. Sehrgar uni kechiradimi yoki yo'q, buni vaqt ko'rsatadi!"
                    )
                    continue
            
            # Gazab special handling
            if action.result == "gazab":
                # Gazabdorga tunda hujum bo'lganini tekshiramiz
                was_attacked = False
                for a in asl_actions:
                    if a.target_id == actor.id and a.result in ("o'ldi", "qotil", "ovchi", "labarant", "kdeath", "urish") and a.result != "otmen":
                        was_attacked = True
                        break
                    if a.target_id == actor.id and a.action_type == "jin_qotil" and a.result != "otmen":
                        was_attacked = True
                        break
                
                if not was_attacked:
                    continue
                
                # Gazabdor picks
                picks = await Action.filter(
                    actor=actor,
                    action_type=f"gazab:{game.id}"
                ).prefetch_related("target__user").all()
                
                valid_picks = []
                
                for pick in picks:
                    pick_target = players_cache.get(pick.target_id)
                    if not pick_target or not pick_target.is_alive:
                        continue
                    
                    # Himoya tekshirish
                    protected = False
                    
                    if saved_user and pick_target.user.user_id == saved_user.user_id:
                        attackers_roles.append(actor.role)
                        protected = True
                    
                    if labarant_saved_user and pick_target.user.user_id == labarant_saved_user.user_id:
                        labarant_attackers_roles.append(actor.role)
                        protected = True
                    
                    if (not protected and 
                        getattr(pick_target, "can_protection_self", True) and weapons_set.himoya):
                        
                        profile = profiles_cache.get(pick_target.user_id)
                        if profile and profile.himoya > 0 and profile.on_himoya and not getattr(game, 'qm_portlat_active', False):
                            profile.himoya -= 1
                            profile_updates.append(profile)
                            
                            pick_target.can_protection_self = False
                            player_updates.append(pick_target)
                            protected = True
                            
                            await safe_send_message(bot, 
                                pick_target.user.user_id,
                                "🛡 Sizga hujum bo'ldi, ammo himoya sizni qutqardi!",
                                parse_mode="HTML",
                                reply_markup=go_group_button(chat.invite_link)
                            )
                            await safe_send_message(bot, 
                                chat.chat_id,
                                "💫 Kimnigdir himoyasi ishladi!"
                            )
                    
                    if not protected:
                        valid_picks.append(pick)
                
                # Valid picklar ni o'ldirish
                for pick in valid_picks:
                    pick_target = players_cache.get(pick.target_id)
                    if pick_target:
                        pick_target.is_alive = False
                        pick_target.deaded_at = datetime.now(timezone.utc)
                        dead_player_ids.add(pick_target.id)
                        player_updates.append(pick_target)
                        
                        killed_players.append((
                            pick_target.user.mention,
                            pick_target.role,
                            actor.role,
                            pick_target.user.user_id,
                            getattr(pick_target, 'team', None)
                        ))
                
                # Gazabdor o'zini o'ldirish
                actor.is_alive = False
                actor.deaded_at = datetime.now(timezone.utc)
                dead_player_ids.add(actor.id)
                player_updates.append(actor)
                
                killed_players.append((
                    actor.user.mention,
                    actor.role,
                    actor.role,
                    actor.user.user_id,
                    getattr(actor, 'team', None)
                ))
                
                # Award
                if len(valid_picks) >= 2:
                    actor.is_really_winner = True
                    player_updates.append(actor)
                    awardees_dict[actor] += 15
                continue
            
            # Ovchi vs Komissar
            if actor.role == RoleNames.OVCHI and target.role == RoleNames.KOMISSAR:
                actor.is_alive = False
                actor.deaded_at = datetime.now(timezone.utc)
                dead_player_ids.add(actor.id)
                player_updates.append(actor)
                awardees_dict[actor] -= 10
                
                killed_players.append((
                    actor.user.mention,
                    actor.role,
                    target.role,
                    actor.user.user_id,
                    getattr(actor, 'team', None)
                ))
                continue
            
            # Qotil va Ovchi special handling
            if (actor.role in [RoleNames.QOTIL, RoleNames.OVCHI] and 
                (actor.role != RoleNames.QOTIL or target.role != RoleNames.QASOSKOR)):
                
                # Qotil vs Bori in real mode
                if (actor.role == RoleNames.QOTIL and 
                    target.role == RoleNames.BORI and 
                    game.mode.startswith("super")):
                    
                    target.role = RoleNames.QOTIL
                    player_updates.append(target)
                    awardees_dict[actor] += 5
                    
                    await safe_send_message(bot,
                        chat.chat_id,
                        f"{role_display(RoleNames.BORI)} <b>{role_display(RoleNames.QOTIL)}</b>ga aylandi!",
                        parse_mode="HTML"
                    )
                    continue
                
                # Labarant save
                if not getattr(action, 'with_miltiq', False) and labarant_saved_user and target.user.user_id == labarant_saved_user.user_id:
                    labarant_attackers_roles.append(actor.role)
                    continue
                
                # Doctor save (faqat qotil uchun)
                if not getattr(action, 'with_miltiq', False) and (actor.role == RoleNames.QOTIL and 
                    saved_user and target.user.user_id == saved_user.user_id):
                    attackers_roles.append(actor.role)
                    continue
                
                # Qotildan himoya
                profile = profiles_cache.get(target.user_id)
                if not getattr(action, 'with_miltiq', False) and getattr(target, "can_qotildan_himoya", True) and (profile and not getattr(game, 'qm_portlat_active', False) and
                    profile.qotildan_himoya > 0 and profile.on_qotildan_himoya and
                    weapons_set.qotildan_himoya):
                    
                    profile.qotildan_himoya -= 1
                    profile_updates.append(profile)
                    target.can_qotildan_himoya = False
                    player_updates.append(target)
                    
                    await safe_send_message(bot, 
                        target.user.user_id,
                        "🛡 Sizni qotildan himoya qutqardi!",
                        parse_mode="HTML",
                        reply_markup=go_group_button(chat.invite_link)
                    )
                    await safe_send_message(bot, 
                        chat.chat_id,
                        "💫 Kimnigdir qotildan himoyasi ishladi!"
                    )
                    continue
                
                # O'ldirish
                target.is_alive = False
                target.deaded_at = datetime.now(timezone.utc)
                dead_player_ids.add(target.id)
                player_updates.append(target)
                awardees_dict[actor] += 6
                
                if getattr(action, 'with_miltiq', False):
                    actor_profile = profiles_cache.get(actor.user_id)
                    if actor_profile:
                        actor_profile.miltiq = max(0, actor_profile.miltiq - 1)
                        profile_updates.append(actor_profile)
                    await safe_send_message(bot, chat.chat_id, "🔫 Kimdir miltiqdan foydalandi.", parse_mode="HTML")
                
                killed_players.append((
                    target.user.mention,
                    target.role,
                    actor.role,
                    target.user.user_id,
                    getattr(target, 'team', None)
                ))

                muhim_olimlar.append((target, phase, bot, chat))
                continue
            
            # Qasoskor special case
            if target.role == RoleNames.QASOSKOR:
                labarant_bormi = False
                
                if labarant_saved_user and target.user.user_id == labarant_saved_user.user_id:
                    labarant_attackers_roles.append(actor.role)
                    labarant_bormi = True
                
                target.is_alive = False
                target.deaded_at = datetime.now(timezone.utc)
                dead_player_ids.add(target.id)
                player_updates.append(target)
                
                # Unconditionally take the shooter if they are alive (and not protected)
                if not labarant_bormi:
                    actor.is_alive = False
                    actor.deaded_at = datetime.now(timezone.utc)
                    dead_player_ids.add(actor.id)
                    player_updates.append(actor)
                    
                    if qasoskor_otganlar.get(target):
                        qasoskor_otganlar[target].append(actor.role)
                    else:
                        qasoskor_otganlar[target] = [actor.role]
                    
                    if target.role in MAFIA_ROLES | {RoleNames.QOTIL}:
                        awardees_dict[actor] += 10
                    
                    killed_players.append((
                        actor.user.mention,
                        actor.role,
                        target.role,
                        actor.user.user_id,
                        getattr(actor, 'team', None)
                    ))
                
                killed_players.append((
                    target.user.mention,
                    target.role,
                    actor.role,
                    target.user.user_id,
                    getattr(target, 'team', None)
                ))
                
                if not actor.is_alive:
                    if actor.role in [RoleNames.DON, RoleNames.KOMISSAR, RoleNames.DOKTOR]:
                        muhim_olimlar.append((actor, phase, bot, chat))
                continue
            
            # Miltiq bilan o'ldirish
            if (actor.role in [RoleNames.DON, RoleNames.KOMISSAR] and 
                getattr(action, 'with_miltiq', False)):
                
                target.is_alive = False
                target.deaded_at = datetime.now(timezone.utc)
                dead_player_ids.add(target.id)
                player_updates.append(target)
                await safe_send_message(bot, 
                    chat.chat_id,
                    f"🔫 Kimdir miltiqdan foydalandi.",
                    parse_mode="HTML"
                )
                killed_players.append((
                    target.user.mention,
                    target.role,
                    actor.role,
                    target.user.user_id,
                    getattr(target, 'team', None)
                ))
                
                # Miltiq ni kamaytirish
                actor_profile = profiles_cache.get(actor.user_id)
                if actor_profile:
                    actor_profile.miltiq -= 1
                    profile_updates.append(actor_profile)
                
                # Award
                is_correct_kill = (
                    (actor.role == RoleNames.KOMISSAR and target.role in MAFIA_ROLES | {RoleNames.QOTIL}) or
                    (actor.role == RoleNames.DON and target.role not in MAFIA_ROLES)
                )
                if is_correct_kill:
                    awardees_dict[actor] += 6
                
                continue
            
            # Oddiy o'ldirish - himoya tekshirish
            protected = False
            
            # Doctor himoyasi
            if saved_user and target.user.user_id == saved_user.user_id:
                attackers_roles.append(actor.role)
                protected = True
            
            # Labarant himoyasi
            if labarant_saved_user and target.user.user_id == labarant_saved_user.user_id:
                labarant_attackers_roles.append(actor.role)
                protected = True
            
            # Qo'riqchi himoyasi
            if not protected and target.id in qoriqchi_saves:
                q_actor = qoriqchi_saves[target.id]
                if q_actor.is_alive and actor.id != q_actor.id:
                    # Hujumchini o'ldirish
                    actor.is_alive = False
                    actor.deaded_at = datetime.now(timezone.utc)
                    dead_player_ids.add(actor.id)
                    player_updates.append(actor)
                    
                    killed_players.append((
                        actor.user.mention,
                        actor.role,
                        RoleNames.QORIQCHI,
                        actor.user.user_id,
                        getattr(actor, 'team', None)
                    ))
                    
                    # Qo'riqchiga award
                    awardees_dict[q_actor] += 10
                    
                    await safe_send_message(bot, 
                        q_actor.user.user_id,
                        f"🛡 Siz qo'riqlayotgan <b>{target.user.full_name if not nik else nik}</b>ga hujum bo'ldi. Siz hujumchini bartaraf etdingiz!",
                        parse_mode="HTML"
                    )
                    await safe_send_message(bot, 
                        target.user.user_id,
                        f"🛡 Sizga hujum bo'ldi, ammo <b>🛡 Qo'riqchi</b> sizni qutqarib qoldi!",
                        parse_mode="HTML"
                    )
                    await safe_send_message(bot, 
                        chat.chat_id,
                        f"🛡 Qo'riqchi o'z vazifasini bajardi! Hujumchi halok bo'ldi.",
                        parse_mode="HTML"
                    )
                    protected = True
            
            # Self himoya
            if (not protected and 
                getattr(target, "can_protection_self", True) and weapons_set.himoya):
                
                profile = profiles_cache.get(target.user_id)
                if profile and profile.himoya > 0 and profile.on_himoya and not getattr(game, 'qm_portlat_active', False):
                    profile.himoya -= 1
                    profile.on_himoya = False
                    profile_updates.append(profile)
                    
                    target.can_protection_self = False
                    player_updates.append(target)
                    protected = True
                    
                    await safe_send_message(bot, 
                        target.user.user_id,
                        "🛡 Sizga hujum bo'ldi, ammo himoya qutqardi!",
                        parse_mode="HTML",
                        reply_markup=go_group_button(chat.invite_link)
                    )
                    await safe_send_message(bot, 
                        chat.chat_id,
                        "💫 Kimnigdir himoyasi ishladi!"
                    )
            
            if protected:
                continue
            
            # Omadli special case
            if target.role == RoleNames.OMADLI and random.randint(1, 100) <= 85:
                await safe_send_message(bot, 
                    chat.chat_id,
                    "💫 Kimningdir omadi keldi va omon qoldi!",
                    parse_mode="HTML"
                )
                awardees_dict[target] += 6
                continue
            
            # O'ldirish
            killed_players.append((
                target.user.mention,
                target.role,
                RoleNames.JIN if action.action_type == "jin_qotil" else actor.role,
                target.user.user_id,
                getattr(target, 'team', None)
            ))
            
            if target.role in (RoleNames.DON, RoleNames.KOMISSAR, RoleNames.DOKTOR):
                muhim_olimlar.append((target, phase, bot, chat))
            
            target.is_alive = False
            target.deaded_at = datetime.now(timezone.utc)
            dead_player_ids.add(target.id)
            player_updates.append(target)
            awardees_dict[actor] += 10
        
        # SOTQIN ACTION
        elif action.action_type == "sotqin":
            if target.role in [RoleNames.DON, RoleNames.MAFIA, RoleNames.QOTIL, RoleNames.AYGOQCHI]:
                awardees_dict[actor] += 7
                await safe_send_message(bot, 
                    chat.chat_id,
                    f"<b>{role_display(actor.role)}</b> odamlarga {colors_dict.get(target.team, '') if vsgame else ''}<b>{target.user.mention if not nik else nik}</b>ning <b>{role_display(target.role)}</b> ekanini sotib berdi",
                    parse_mode="HTML"
                )
        
        # JOKER ACTION
        elif action.action_type == "joker":
            death_number = action.result.split(":")[-1]
            target.should_choose_card = True
            player_updates.append(target)
            
            if target.role != RoleNames.OVCHI:
                markup = joker_buttons(phase.id, death_number)
                await safe_send_message(bot, 
                    target.user.user_id,
                    f"🤡🎈 Joker seni tanladi, sho'rlik! Bugun kechgacha bitta kartani tanla – omading chopsa yashaysan, tanlamasang o'lasan!",
                    parse_mode="HTML",
                    reply_markup=markup
                )
        
        # XOYIN ACTION
        elif action.action_type == "xoyin_found":
            if action.result == "mafia":
                # Success - transformation
                actor.role = RoleNames.MAFIA
                player_updates.append(actor)
                awardees_dict[actor] += 10
                
                await safe_send_message(bot, 
                    actor.user.user_id,
                    "👺 Siz mafiyani topdingiz va endi <b>🤵🏼 Mafia</b>ga aylandingiz!",
                    parse_mode="HTML",
                    reply_markup=go_group_button(chat.invite_link)
                )
                await safe_send_message(bot, 
                    chat.chat_id,
                    "👺 Xoyin mafiyani topdi va ularning safiga qo'shildi!"
                )
            else:
                # Miss - count actions
                failed_attempts = await Action.filter(actor=actor, action_type="xoyin_found", result="miss").count()
                if failed_attempts >= 3:
                    actor.is_alive = False
                    actor.deaded_at = datetime.now(timezone.utc)
                    dead_player_ids.add(actor.id)
                    player_updates.append(actor)
                    
                    killed_players.append((
                        actor.user.mention,
                        actor.role,
                        "O'zini o'zi o'ldirdi",  # Bu ro'yxat uchun xavfsizroq, pastda to'liq tekst o'zgartiriladi
                        actor.user.user_id,
                        getattr(actor, 'team', None)
                    ))
                    
                    await safe_send_message(bot, 
                        actor.user.user_id,
                        "💀 Siz 3 marta noto'g'ri tanlov qildingiz va halok bo'ldingiz!",
                        parse_mode="HTML",
                        reply_markup=go_group_button(chat.invite_link)
                    )
                else:
                    attempts_left = 3 - failed_attempts
                    await safe_send_message(bot, 
                        actor.user.user_id,
                        f"❌ Siz tanlagan ishtirokchi mafiya emas edi. Sizda {attempts_left} ta imkoniyat qoldi.",
                        parse_mode="HTML",
                        reply_markup=go_group_button(chat.invite_link)
                    )
            continue

        # KOMISSAR TEKSHIRISH
        elif action.action_type == "tek":
            profile = profiles_cache.get(target.user_id)
            
            # Advokat himoyasi
            if target.id in advokat_himoyalar:
                adv_id = advokat_himoyalar[target.id]
                adv_player = players_cache.get(adv_id)
                if adv_player:
                    await safe_send_message(bot, 
                        adv_player.user.user_id,
                        f"🛡 Siz {colors_dict.get(target.team, '') if vsgame else ''}{target.user.full_name if not nik else nik}ni Komissar tekshiruvidan himoya qildingiz!",
                        parse_mode="HTML",
                        reply_markup=go_group_button(chat.invite_link)
                    )
                    await safe_send_message(bot, 
                        target.user.user_id,
                        "📄 Sizni advokat komissardan himoya qildi!!",
                        parse_mode="HTML",
                        reply_markup=go_group_button(chat.invite_link)
                    )
                
                kom_info = f"<b>{target.user.full_name}</b> - <b>{RoleNames.FUQARO}</b>"
            
            # Ovchi
            elif target.role in [RoleNames.OVCHI]:
                kom_info = f"<b>{target.user.full_name}</b> - <b>{RoleNames.FUQARO}</b>"
            
            # Hujjat himoyasi
            elif weapons_set.hujjat and (profile and profile.hujjat > 0 and not getattr(game, 'qm_portlat_active', False) and
                  getattr(target, "can_document_self", True) and
                  target.role in {RoleNames.DON, RoleNames.MAFIA, RoleNames.ADVOKAT, RoleNames.JURNALIST, RoleNames.GAZABDOR, RoleNames.QOTIL, RoleNames.AFERIST} and
                  profile.on_hujjat):
                
                profile.hujjat -= 1
                profile_updates.append(profile)
                
                target.can_document_self = False
                player_updates.append(target)
                
                kom_info = f"{colors_dict.get(target.team, '') if vsgame else ''}<b>{target.user.full_name if not nik else nik}</b> - <b>{RoleNames.FUQARO}</b>"
                
                await safe_send_message(bot, 
                    target.user.user_id,
                    "📄 Sizni komissar tekshirdi. Ammo, siz rolingizni yashirdingiz.",
                    parse_mode="HTML",
                    reply_markup=go_group_button(chat.invite_link)
                )
            else:
                awardees_dict[actor] += 4
                kom_info = f"{colors_dict.get(target.team, '') if vsgame else ''}<b>{target.user.full_name if not nik else nik}</b> - <b>{role_display(target.role)}</b>"
                
                await safe_send_message(bot, 
                    target.user.user_id,
                    "Kimdir rolingizga juda qizziqdi!",
                    reply_markup=go_group_button(chat.invite_link)
                )
            
            # Komissar va serjantlarga xabar
            await safe_send_message(bot, actor.user.user_id, kom_info, parse_mode="HTML")
            
            serj_list = await GamePlayer.filter(
                game=game,
                role__in=[RoleNames.SERJANT],
                is_alive=True
            ).prefetch_related("user").all()
            
            for serj in serj_list:
                await safe_send_message(bot, serj.user.user_id, kom_info, parse_mode="HTML")
    
    # 9. QASOSKOR WINNER STATUS UPDATE
    for qasoskor, otganlar in qasoskor_otganlar.items():
        for otgan in otganlar:
            if otgan in MAFIA_ROLES | {RoleNames.QOTIL}:
                qasoskor.is_really_winner = True
                player_updates.append(qasoskor)
                break
        else:
            qasoskor.is_really_winner = False
            player_updates.append(qasoskor)
    
    # 10. VISIT MAP VA DAYDI PROCESSING
    visit_map = defaultdict(set)
    action_type_map = {}
    
    for action in actions:
        if action.action_type != "daydi" and action.result != "dondan ovoz":
            visit_map[action.target_id].add(action.actor_id)
            action_type_map[action.actor_id] = action.action_type
    
    # Daydi processing
    for daydi_actor_id, target_id in daydi_info.items():
        daydi_player = players_cache.get(daydi_actor_id)
        if not daydi_player or daydi_player.is_sleep:
            break
        
        visitor_ids = visit_map.get(target_id, set()) - {daydi_actor_id}
        visible_visitors = []
        
        for visitor_id in visitor_ids:
            visitor = players_cache.get(visitor_id)
            if not visitor:
                continue
            
            role = visitor.role
            action_type = action_type_map.get(visitor_id)
            
            # Faqat ma'lum role va action type lar ko'rinadi
            if role in [RoleNames.DON, RoleNames.QOTIL, RoleNames.QASOSKOR, RoleNames.GAZABDOR]:
                pass
            elif role == RoleNames.KOMISSAR and action_type == "otish":
                pass
            else:
                continue
            
            # Maska tekshirish
            visitor_profile = profiles_cache.get(visitor.user_id)
            maska = False
            if (getattr(visitor, "can_maska", True) and weapons_set.maska and 
                (visitor_profile and visitor_profile.maska > 0 and 
                visitor.role != RoleNames.KOMISSAR and visitor_profile.on_maska)):
                visitor_profile.maska -= 1
                profile_updates.append(visitor_profile)
                visitor.can_maska = False
                player_updates.append(visitor)
                maska = True
            
            visitor_name = 'maskali' if maska else (
                f"{colors_dict.get(visitor.team, '')}{visitor.user.full_name if not nik else nik}" if vsgame else visitor.user.full_name if not nik else nik
            )
            
            visible_visitors.append(f"<b>{visitor_name}</b> - <b>{role_display(visitor.role)}</b>")
        
        # Daydi ga natija yuborish
        if not visible_visitors:
            await safe_send_message(bot, 
                daydi_player.user.user_id,
                "🍾 Siz shishani oldingiz va uyingizga qaytdingiz! Shubhali narsani ko'rmadingiz!",
                parse_mode="HTML",
                reply_markup=go_group_button(chat.invite_link)
            )
        else:
            visitors_text = ", ".join(visible_visitors)
            await safe_send_message(bot, 
                daydi_player.user.user_id,
                f"🍾 Siz kimningdir jonsiz jasadi ustida {visitors_text}{'lar' if len(visible_visitors) > 1 else ''}ni turganini ko'rdingiz.",
                parse_mode="HTML",
                reply_markup=go_group_button(chat.invite_link)
            )
    
    # 11. HIMOYA NATIJALARI
    # Hamshira bilgilendirish
    hamshira_player = await GamePlayer.get_or_none(
        game=phase.game,
        role=RoleNames.HAMSHIRA,
        is_alive=True
    ).prefetch_related("user")
    
    # Doctor himoya natijalari
    if saved_user and attackers_roles:
        roles_str = ", ".join(attackers_roles)
        doctor_actor = await GamePlayer.filter(user__user_id=doctor_user.user_id).last()
        if doctor_actor:
            awardees_dict[doctor_actor] += len(attackers_roles)
        
        await safe_send_message(bot, 
            doctor_user.user_id,
            f"🛡 Siz {saved_user.full_name if not nik else nik}ni {roles_str} hujumidan qutqardingiz!",
            parse_mode="HTML",
            reply_markup=go_group_button(chat.invite_link)
        )
        
        if hamshira_player:
            await safe_send_message(bot, 
                hamshira_player.user.user_id,
                f"🛡 {RoleNames.DOKTOR} tunda {saved_user.full_name if not nik else nik}ni {roles_str} hujumidan qutqarib qoldi!",
                parse_mode="HTML",
                reply_markup=go_group_button(chat.invite_link)
            )
        
        await safe_send_message(bot, 
            saved_user.user_id,
            f"🛡 {roles_str} sizga hujum qildi, ammo 👨🏼‍⚕️ doktor sizni saqlab qoldi.",
            parse_mode="HTML",
            reply_markup=go_group_button(chat.invite_link)
        )
    else:
        if saved_user:
            await safe_send_message(bot, 
                saved_user.user_id,
                "👨🏼‍⚕️ Doktor siznikiga mehmonga keldi!",
                parse_mode="HTML",
                reply_markup=go_group_button(chat.invite_link)
            )
            
            if hamshira_player:
                await safe_send_message(bot, 
                    hamshira_player.user.user_id,
                    f"👨🏼‍⚕️ Doktor tunda hech narsa qilmadi!",
                    parse_mode="HTML",
                    reply_markup=go_group_button(chat.invite_link)
                )
            
            await safe_send_message(bot, 
                doctor_user.user_id,
                "👨🏼‍⚕️ Doktor yordam berolmadi!",
                parse_mode="HTML",
                reply_markup=go_group_button(chat.invite_link)
            )
    
    # Kimyogar himoya natijalari
    if kimyogar_saved_user and kimyogar_attackers_roles:
        roles_str = ", ".join(kimyogar_attackers_roles)
        kimyogar_actor = await GamePlayer.filter(user__user_id=kimyogar_user.user_id).last()
        if kimyogar_actor:
            awardees_dict[kimyogar_actor] += len(kimyogar_attackers_roles)
        
        await safe_send_message(bot, 
            kimyogar_user.user_id,
            f"🛡 Siz {kimyogar_saved_user.full_name if not nik else nik}ni {roles_str}lardan himoya qildingiz!",
            parse_mode="HTML",
            reply_markup=go_group_button(chat.invite_link)
        )
        
        await safe_send_message(bot, 
            kimyogar_saved_user.user_id,
            f"🛡 {roles_str} tunda siznikiga keldi, ammo 👨‍🔬 kimyogar eleksiri sizni himoya qildi.",
            parse_mode="HTML",
            reply_markup=go_group_button(chat.invite_link)
        )
    else:
        if kimyogar_saved_user:
            await safe_send_message(bot, 
                kimyogar_saved_user.user_id,
                "👨‍🔬 kimyogar siznikiga mehmonga keldi!",
                parse_mode="HTML",
                reply_markup=go_group_button(chat.invite_link)
            )
            
            await safe_send_message(bot, 
                kimyogar_user.user_id,
                "👨‍🔬 kimyogar yordamiga muhtojlik bo'lmadi!",
                parse_mode="HTML",
                reply_markup=go_group_button(chat.invite_link)
            )
    
    # Labarant himoya natijalari
    if labarant_saved_user and labarant_attackers_roles:
        roles_str = ", ".join(labarant_attackers_roles)
        labarant_actor = await GamePlayer.filter(user__user_id=labarant_user.user_id).last()
        if labarant_actor:
            awardees_dict[labarant_actor] += len(labarant_attackers_roles)
        
        await safe_send_message(bot, 
            labarant_user.user_id,
            f"🛡 Siz {labarant_saved_user.full_name if not nik else nik}ni {roles_str} hujumidan qutqardingiz!",
            parse_mode="HTML",
            reply_markup=go_group_button(chat.invite_link)
        )
        
        await safe_send_message(bot, 
            labarant_saved_user.user_id,
            f"🛡 {roles_str} sizga hujum qildi, ammo 👩‍⚕️ labarant sizni saqlab qoldi.",
            parse_mode="HTML",
            reply_markup=go_group_button(chat.invite_link)
        )
    else:
        if labarant_saved_user:
            await safe_send_message(bot, 
                labarant_saved_user.user_id,
                "👩‍⚕️ labarant siznikiga mehmonga keldi!",
                parse_mode="HTML",
                reply_markup=go_group_button(chat.invite_link)
            )
            
            await safe_send_message(bot, 
                labarant_user.user_id,
                "👩‍⚕️ labarant yordam berolmadi!",
                parse_mode="HTML",
                reply_markup=go_group_button(chat.invite_link)
            )

    # Jurnalist intervyu natijalari (to'g'irlangan va cachesdan foydalanadi)
    jurnalist_actions = [a for a in actions if a.action_type == "jurnalist"]

    for a in jurnalist_actions:
        jurnalist = players_cache.get(a.actor_id) or await GamePlayer.get_or_none(id=a.actor_id).prefetch_related("user")
        target = players_cache.get(a.target_id) or await GamePlayer.get_or_none(id=a.target_id).prefetch_related("user")
        if not jurnalist or not target:
            continue
        # agar o'zi yoki notog'ri target bo'lsa davom etmaymiz
        if jurnalist.id == target.id:
            try:
                await safe_send_message(bot, 
                    jurnalist.user.user_id,
                    f"Siz {colors_dict.get(target.team, '') if vsgame else ''}{target.user.full_name if not nik else nik} intervyu oldingiz va ortingizga qaytdingiz! Hech kimni aniqlay olmadingiz!",
                    parse_mode="HTML",
                    reply_markup=go_group_button(chat.invite_link)
                )
            except Exception:
                pass
            continue

        visitor_ids = visit_map.get(target.id, set()) - {jurnalist.id}
        visible_visitors = []

        if target.role != RoleNames.KOMISSAR:
            for vid in visitor_ids:
                vp = players_cache.get(vid)
                if not vp:
                    try:
                        vp = await GamePlayer.get(id=vid).prefetch_related("user")
                    except Exception:
                        continue
                if vp.role in [RoleNames.DON, RoleNames.MAFIA]:
                    continue
                vp_profile = profiles_cache.get(vp.user_id)
                maska = False
                if (getattr(vp, "can_maska", True) and weapons_set.maska and vp_profile and 
                    vp_profile.maska > 0 and vp.role not in [RoleNames.DON, RoleNames.OVCHI] and vp_profile.on_maska):
                    vp_profile.maska -= 1
                    profile_updates.append(vp_profile)  # bulk update later
                    vp.can_maska = False
                    player_updates.append(vp)
                    maska = True

                name = (colors_dict.get(vp.team, "") + (vp.user.full_name if not nik else nik)) if vsgame else (vp.user.full_name if not nik else nik)
                visible_visitors.append(f"<b>{'maskali' if maska else name}</b> - <b>{role_display(vp.role)}</b>")

        if visible_visitors:
            visitors_text = ", ".join(visible_visitors)
            try:
                await safe_send_message(bot, 
                    jurnalist.user.user_id,
                    f"Siz {colors_dict.get(target.team, '') if vsgame else ''}{target.user.full_name if not nik else nik}dan intervyu oldingiz va unikiga {visitors_text} {'' if len(visible_visitors) == 1 else 'lar'}ni kelganini aniqladingiz.",
                    parse_mode="HTML",
                    reply_markup=go_group_button(chat.invite_link)
                )
            except Exception:
                pass

            don_player = await GamePlayer.filter(game=game, is_alive=True, role=RoleNames.DON).prefetch_related("user").first()
            if don_player:
                try:
                    await safe_send_message(bot, 
                        don_player.user.user_id,
                        f"📬 Sizga jurnalistdan xat:\n\n"
                        f"Men {colors_dict.get(target.team, '') if vsgame else ''}{target.user.full_name if not nik else nik}dan intervyu oldim va unikiga {visitors_text} {'' if len(visible_visitors) == 1 else 'lar'}ni kelganini aniqladim.",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
        else:
            try:
                await safe_send_message(bot, 
                    jurnalist.user.user_id,
                    f"Siz {colors_dict.get(target.team, '') if vsgame else ''}{target.user.full_name if not nik else nik} intervyu oldingiz va ortingizga qaytdingiz! Hech kimni aniqlay olmadingiz!",
                    parse_mode="HTML",
                    reply_markup=go_group_button(chat.invite_link)
                )
            except Exception:
                pass
    # 12. MISSED NIGHTS (AFK) PROCESSING — Faqat tunda yuradigan (aktiv) rollar uchun
    acted_ids = set()
    for action in asl_actions:
        if action.actor_id:
            acted_ids.add(action.actor_id)

    all_alive_players = await GamePlayer.filter(
        game=phase.game,
        is_alive=True
    ).prefetch_related("user").all()
    
    kimdir_ketdimi = False
    for player in all_alive_players:
        # Agar bu o'yinchi shu kecha o'lgan bo'lsa, AFK hisobidan va alive ro'yxatidan chiqarish
        if player.id in dead_player_ids or not player.is_alive:
            continue

        # Kezuvchi uxlatgan o'yinchilarni AFK hisobidan chiqarib tashlash
        if player.is_sleep:
            if player.missed_nights:
                player.missed_nights = 0
                player_updates.append(player)
            continue

        # Tunda yurmaydigan (passiv) rollar (Fuqaro, Hamshira, Qasoskor, Omadli, Suidsid, Serjant) AFK hisoblanmaydi!
        if player.role not in ACTIVE_ROLES:
            if player.missed_nights:
                player.missed_nights = 0
                player_updates.append(player)
            continue

        # Faqat aktiv rollar tunda harakatlanmagan bo'lsa AFK hisoblanadi.
        # Agar o'yinchi harakat qilgan bo'lsa yoki "O'tkazib yuborish" (dam oladi) ni bosgan bo'lsa -> AFK hisoblanmaydi!
        if player.id in acted_ids or player.is_actioned:
            if player.missed_nights:
                player.missed_nights = 0
                player_updates.append(player)
        else:
            player.missed_nights += 1
            if player.missed_nights >= 2:
                player.is_alive = False
                player.deaded_at = datetime.now(timezone.utc)
                dead_player_ids.add(player.id)
                player_updates.append(player)
                
                await safe_send_message(bot, 
                    chat.chat_id,
                    f"""
Aholidan kimdir {colors_dict.get(player.team, '') if vsgame else ''}<b>{role_display(player.role)}</b> {player.user.mention} o'limidan oldin:
"Men o'yin paytida boshqa uxlamayma-a-a-a-a-a-an!" - deb qichqirganini eshitgan.
""",
                    parse_mode="HTML"
                )
                kimdir_ketdimi = True
                
                if player.role in (RoleNames.DON, RoleNames.KOMISSAR, RoleNames.DOKTOR):
                    muhim_olimlar.append((player, phase, bot, chat))
            else:
                player_updates.append(player)

    # 12.5 ZANJIR PROCESSING
    zanjir_actions = [a for a in asl_actions if a.action_type == "zanjir"]
    for z_action in zanjir_actions:
        t1_id = z_action.target_id
        t2_id = int(z_action.result)
        
        dead_ids = set()
        for p in minaga_tushganlar:
            dead_ids.add(p.user_id)
        for _, _, _, uid, _ in killed_players:
            # uid is user.user_id
            dead_ids.add(uid)
            
        # Add missed_nights deads
        for p in all_alive_players:
            if p.missed_nights >= 2:
                dead_ids.add(p.user_id)

        t1 = players_cache.get(t1_id)
        t2 = players_cache.get(t2_id)
        
        if not t1 or not t2:
            continue
            
        t1_dead = (t1.user_id in dead_ids) or (not t1.is_alive) or (t1.id in dead_player_ids)
        t2_dead = (t2.user_id in dead_ids) or (not t2.is_alive) or (t2.id in dead_player_ids)
        
        to_kill = None
        if t1_dead and not t2_dead and t2.is_alive:
            to_kill = t2
        elif t2_dead and not t1_dead and t1.is_alive:
            to_kill = t1
            
        if to_kill:
            to_kill.is_alive = False
            to_kill.deaded_at = datetime.now(timezone.utc)
            dead_player_ids.add(to_kill.id)
            player_updates.append(to_kill)
            
            killed_players.append((
                to_kill.user.mention,
                to_kill.role,
                RoleNames.ZANJIR,
                to_kill.user.user_id,
                getattr(to_kill, 'team', None)
            ))
            
            if to_kill.role in (RoleNames.DON, RoleNames.KOMISSAR, RoleNames.DOKTOR):
                muhim_olimlar.append((to_kill, phase, bot, chat))
    
    # 13. BULK UPDATES
    try:
        if profile_updates:
            unique_profile_updates = list({p.id: p for p in profile_updates}.values())
            await Profile.bulk_update(
                unique_profile_updates,
                fields=['himoya', 'qotildan_himoya', 'doridan_himoya', 'maska', 'hujjat', 'dollar', 'diamond', 'miltiq']
            )
        
        if player_updates:
            player_dict = {}
            for p in player_updates:
                if p.id in player_dict:
                    prev = player_dict[p.id]
                    # Agar biror marta o'lgan bo'lsa, o'lim holati 100% saqlansin
                    if not prev.is_alive or not p.is_alive or p.id in dead_player_ids:
                        p.is_alive = False
                        p.deaded_at = p.deaded_at or prev.deaded_at or datetime.now(timezone.utc)
                elif p.id in dead_player_ids:
                    p.is_alive = False
                    p.deaded_at = p.deaded_at or datetime.now(timezone.utc)
                player_dict[p.id] = p
            unique_player_updates = list(player_dict.values())
            await GamePlayer.bulk_update(
                unique_player_updates,
                fields=[
                    'is_alive', 'deaded_at', 'can_protection_self', 'is_sleep',
                    'role', 'missed_nights', 'should_choose_card', 'is_really_winner', 'life',
                    'can_heal_self', 'can_document_self', 'can_investigate_self',
                    'can_osishdan_himoya', 'can_osishdan_himoya_adv', 'can_slip_himoya', 'is_actioned',
                    'kom_success_checks', 'kom_is_upgraded', 'kom_wire_uses', 'kom_wire_target_pid',
                    'kom_profile_used', 'kom_qosh_used', 'kom_arrest_pid', 'kom_arrest_used',
                    'kom_himoya_target_pid', 'kom_himoya_nights', 'kom_signal_used', 'kom_himoya_protected',
                    'qm_active', 'qm_void_swap_role', 'qm_void_swap_days', 'qm_original_role',
                    'qm_portlat_used', 'qm_tiriltir_used', 'qm_xazina_used'
                ]
            )
        
        if action_updates:
            unique_action_updates = list({a.id: a for a in action_updates}.values())
            await Action.bulk_update(
                unique_action_updates,
                fields=['result', 'action_type']
            )
    except Exception as e:
        # Fallback - individual saves. Har biri alohida try/except ichida bo'lishi
        # SHART: aks holda bitta o'yinchining saqlanishi muvaffaqiyatsiz bo'lsa,
        # undan keyingi barcha o'yinchilarning is_alive/o'lim holati saqlanmay
        # qoladi ("o'lgan o'yinchi keyingi kechada ham o'ynashda davom etadi" bugi).
        logger.error(f"view_night_results bulk_update xatosi, individual saqlashga o'tildi: {e}")
        for profile in profile_updates:
            try:
                await profile.save()
            except Exception as ie:
                logger.error(f"Profile saqlashda xato (id={getattr(profile, 'id', '?')}): {ie}")
        for player in player_updates:
            try:
                if player.id in dead_player_ids:
                    player.is_alive = False
                    player.deaded_at = player.deaded_at or datetime.now(timezone.utc)
                await player.save()
            except Exception as ie:
                logger.error(f"GamePlayer saqlashda xato (id={getattr(player, 'id', '?')}): {ie}")
        for action in action_updates:
            try:
                await action.save()
            except Exception as ie:
                logger.error(f"Action saqlashda xato (id={getattr(action, 'id', '?')}): {ie}")

    # Atomik kafolat: O'limi e'lon qilingan barcha o'yinchilar bazada 100% is_alive=False bo'lishini ta'minlash
    if dead_player_ids:
        try:
            await GamePlayer.filter(id__in=list(dead_player_ids)).update(
                is_alive=False,
                is_sayed_last_word=False,
                deaded_at=datetime.now(timezone.utc)
            )
            for dead_id in dead_player_ids:
                p_obj = players_cache.get(dead_id)
                if p_obj and hasattr(p_obj, 'user') and p_obj.user:
                    await safe_send_message(
                        bot,
                        p_obj.user.user_id,
                        "💀 <b>Siz kechasi halok bo'ldingiz!</b>\n💬 Guruhingizga <b>oxirgi so'z</b>ingizni yuborish uchun shu yerga (bot shaxsiyiga) matningizni yuboring!",
                        parse_mode="HTML"
                    )
        except Exception as de:
            logger.error(f"dead_player_ids atomik update xatosi: {de}")
    
    # 14. FINAL RESULTS
    # Minaga tushganlar
    if minaga_tushganlar:
        text = "<b>💣 Minaga tushganlar:</b>\n"
        tushganlar = []
        for player in minaga_tushganlar:
            tushganlar.append(f"{colors_dict.get(player.team, '') if vsgame else ''}{player.user.mention} — {role_display(player.role)}")
        text += ", ".join(tushganlar)
        await safe_send_message(bot, chat.chat_id, text, parse_mode="HTML")
        kimdir_ketdimi = True
    
    if robin_ketdi:
        kimdir_ketdimi = True
    
    # O'ldirilganlar ro'yxati
    if killed_players:
        lines = []
        grouped = defaultdict(lambda: {"role": None, "attackers": set(), "user_id": None, "team": None})
        
        for mention, role, attacker, user_id, team in killed_players:
            grouped[mention]["role"] = role
            grouped[mention]["attackers"].add(attacker)
            grouped[mention]["user_id"] = user_id
            grouped[mention]["team"] = team
        
        for mention, info in grouped.items():
            role = info["role"]
            attackers = info["attackers"]
            user_id = info["user_id"]
            team = info["team"]
            
            await safe_send_message(bot, 
                user_id,
                f"Sizni shavfqatsizlarcha o'ldirishdi! So'nggi so'zingizni aytish uchun sizda {_word_time} soniya vaqt bor."
            )
            
            if RoleNames.GAZABDOR in attackers and len(attackers) == 1 and role == RoleNames.GAZABDOR:
                lines.append(f"{colors_dict.get(team, '') if vsgame else ''}{role_display(role)} {mention} — o'zimni o'ldirdim!")
            elif "O'zini o'zi o'ldirdi" in attackers and role == RoleNames.XOYIN:
                lines.append(f"Tunda {colors_dict.get(team, '') if vsgame else ''}<b>{role_display(role)}</b> {mention}...\n3 marta xato tanlov qildi va halok bo'ldi.")
            elif RoleNames.ZANJIR in attackers:
                lines.append(f"Tunda {colors_dict.get(team, '') if vsgame else ''}<b>{role_display(role)}</b> {mention}...\nvaxshiylarcha o'ldirildi. U zanjir bilan bog'langanligi sababli tortib ketildi.")
            elif "Minada sirpanish" in attackers:
                lines.append(f"Tunda {colors_dict.get(team, '') if vsgame else ''}<b>{role_display(role)}</b> {mention}...\nkonda minaga tushib portlab halok bo'ldi.")
            else:
                attacker_list = ", ".join(role_display(a) for a in attackers)
                lines.append(f"Tunda {colors_dict.get(team, '') if vsgame else ''}<b>{role_display(role)}</b> {mention}...\nvaxshiylarcha o'ldirildi. Aytishlaricha, unikiga {attacker_list} kelgan.")
        
        text = "<b>Tunda o'ldirilganlar:</b>\n\n" + "\n\n".join(lines)
        await safe_send_message(bot, chat.chat_id, text, parse_mode="HTML")
    elif kimdir_ketdimi:
        pass  # Boshqa o'lim bor edi
    else:
        await safe_send_message(bot, 
            chat.chat_id,
            "<i>Ishonish qiyin! Lekin, bu tunda hech kim o'lmadi...</i>",
            parse_mode="HTML"
        )
    seen_olims = set()
    for olim in muhim_olimlar:
        if olim in seen_olims:
            continue
        seen_olims.add(olim)
        await assign_new_role(*olim)
    # 15. PLAYER BALL UPDATES
    if awardees_dict:
        ball_updates = []
        for actor, ball in awardees_dict.items():
            try:
                player_ball, created = await PlayersGameBall.get_or_create(
                    player=actor, 
                    game=game,
                    defaults={'ball': ball}
                )
                if not created:
                    player_ball.ball += ball
                ball_updates.append(player_ball)
            except Exception:
                continue
        
        if ball_updates:
            try:
                unique_ball_updates = list({b.id: b for b in ball_updates}.values())
                await PlayersGameBall.bulk_update(unique_ball_updates, fields=['ball'])
            except Exception:
                for ball_obj in ball_updates:
                    await ball_obj.save()

async def leave_game(message: Message, bot: Bot, force = False):
    user, _ = await User.get_or_create(
        user_id=message.from_user.id,
        defaults={
            "full_name": message.from_user.full_name if message.from_user.full_name else "",
            "mention": message.from_user.mention_html()
        }
    )
    player = await GamePlayer.filter(user=user, is_alive=True, game__is_active=True).first().prefetch_related("game", "user", "game__chat")
    if not player or not player.game or not player.game.is_active or player.game.phase in ("end", "ended", "finished", "stopped"):
        return
    await player.game.fetch_related("chat")
    game_set, _ = await GameSetPermissions.get_or_create(chat_id=player.game.chat.chat_id)
    if not game_set.leave_qilish and not force: return
    player.is_alive = False
    player.deaded_at = datetime.now(timezone.utc)
    player.is_sayed_last_word = False

    if player.game.phase == "waiting":
        await player.delete()
        try:
            await update_players_list(player.game, bot)
        except Exception:
            pass
        players = await GamePlayer.filter(game=player.game).all()
        more_set, _ = await GroupMoreSet.get_or_create(chat_id=player.game.chat.chat_id)
        if len(players) >= more_set.max_players:
            await starting_game(game=player.game, message=message, start=True, bot=bot)
    else:
        await safe_send_message(bot, 
            player.user.user_id,
            "💀 <b>Siz o'zingizni osib o'ldirdingiz!</b>\n💬 Guruhingizga <b>oxirgi so'z</b>ingizni yuborish uchun shu yerga (bot shaxsiyiga) matningizni yuboring!",
            parse_mode="HTML"
        )
        try:
            await safe_send_message(bot, 
                player.game.chat.chat_id,
                f"{user.mention} bu shaharning yovuzliklariga chiday olmadi va o'zini osib qo'ydi.\n\nU edi {role_display(player.role)}",
                parse_mode="HTML"
            )
        except Exception:
            pass
        await player.save()


async def rol_taqsimlash(players: List[GamePlayer], bot: Bot, chat: Chat, game: Game):
    from utils.role_configuration import RoleConfiguration
    from utils.roles_text import Roles
    n = len(players)
    rollar = RoleConfiguration.get_roles_for_mode(game.mode, n)
    fuqarolar_soni = n - len(rollar)
    if fuqarolar_soni > 0:
        rollar += [RoleNames.FUQARO] * fuqarolar_soni
    random.shuffle(players)
    random.shuffle(rollar)
    for i, (p, r) in enumerate(zip(players, rollar), start=1):
        p.role = r
        p.maxsus_raqam = i
        await p.save()
        await safe_send_message(
            bot,
            p.user.user_id,
            Roles.get_by_role(r)
        )
