"""
Redis-based game handlers - migrated from utils/game_logic.py.
These handlers implement the same logic but use Redis for state management.
"""
from aiogram import Bot
from aiogram.types import Message
from aiogram.enums.chat_member_status import ChatMemberStatus
from aiogram.fsm.context import FSMContext
from datetime import datetime, timezone
from models.user import User, Profile, Paralar
from models.game_data import Chat
from models.game_set import GamingOnChat, CommandPermissionsChat, GameModeSet, GameSetPermissions, GroupMoreSet
from keyboards.game_keyboard import join_game_button, join_vsgame_button, go_group_button
from utils.redis_game import game_service, player_service
from utils.redis_game.repositories.game_repository import game_repository as game_repo
from utils.redis_game.repositories.player_repository import player_repository as player_repo
from utils.redis_game.role_assignment import rol_taqsimlash_redis
from utils.redis_game.win_conditions import check_win_conditions_redis, announce_game_result_redis, cleanup_game_redis
from utils.redis_game.game_phases import execute_night_phase_redis, execute_day_phase_redis
# from utils.role_replacement import check_and_replace_missing_roles_redis
from collections import defaultdict
from asyncio import create_task
from utils.database import redis_client
from models.game_set import GameSetTime, GameSetWeapons
from utils.role_names import RoleNames
from keyboards.main_keyboard import bot_link_markup
import random
from utils.vsgame import TeamCOlors as TeamColors

async def create_vs_game_handler_redis(message: Message, bot: Bot):
    """
    Redis version of create_vs_game_handler.
    Simplified - faqat service'ni chaqiradi.
    """
    # Service barcha logic'ni bajaradi (permissions, validations, xabar yuborish)
    game_state = await game_service.create_game(
        message=message,
        bot=bot,
        is_vs_game=True
    )
    
    if not game_state:
        # Service allaqachon xatolik xabarini yuborgan yoki permission yo'q
        return



async def create_game_handler_redis(message: Message, bot: Bot):
    """
    Redis version of create_game_handler.
    Simplified - faqat service'ni chaqiradi.
    """
    # Service barcha logic'ni bajaradi (permissions, validations, xabar yuborish)
    game_state = await game_service.create_game(
        message=message,
        bot=bot,
        is_vs_game=False
    )
    
    if not game_state:
        # Service allaqachon xatolik xabarini yuborgan yoki permission yo'q
        return

import asyncio
redis_join_locks = {}

async def _join_game_handler_redis_core(message: Message, bot: Bot, state: FSMContext):
    """
    Redis version of join_game_handler.
    Handles players joining a game via private message.
    """
    
    await state.update_data(xatolar_soni=0)
    
    # Parse game_id from message text (e.g., "join_123_red")
    try:
        game_id = int(message.text.split("_")[1])
    except (IndexError, ValueError):
        await message.answer("Kechirasiz, bu o'yinga qo'shilib bo'lmaydi! ID")
        return
    
    # Load game from Redis
    game_state = await game_repo.load_game(game_id)
    if not game_state:
        await message.answer("Kechirasiz, bu o'yin topilmadi! State")
        return
    
    if game_state.phase != "waiting":
        await message.answer("Kechirasiz, bu o'yin allaqachon boshlangan! Phase")
        return
    
    # Get or create user profile
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
    
    # Get chat info
    chat, _ = await Chat.get_or_create(
        chat_id=game_state.chat_id,
        defaults={"title": "Unknown", "type": "supergroup"}
    )
    
    # Check if player already in this game
    existing_player = await player_repo.load_player(game_id, message.from_user.id)
    if existing_player and existing_player.is_alive:
        # VS game: allow team switching
        if ":vsgame" in game_state.mode:
            color_name = message.text.split("_")[-1]
            if existing_player.team != color_name:
                existing_player.team = color_name
                await player_repo.save_player(existing_player)
                await message.answer(
                    f"Siz jamoangizni almashtirdingiz!", 
                    reply_markup=go_group_button(chat.invite_link)
                )
                await update_players_list_redis(game_id, bot)
                return
        await message.answer(
            "Siz bu o'yinga qo'shilgansiz!", 
            reply_markup=go_group_button(chat.invite_link)
        )
        return
    
    # Check if player is in another active game
    # Scan all active games to see if player already in one
    cursor = 0
    player_in_another_game = False
    while True:
        cursor, keys = await redis_client.scan(cursor, match="game:*:state", count=100)
        for key in keys:
            other_game_id = int(key.split(":")[1])
            if other_game_id != game_id:
                other_player = await player_repo.load_player(other_game_id, message.from_user.id)
                if other_player and other_player.is_alive:
                    player_in_another_game = True
                    break
        if cursor == 0 or player_in_another_game:
            break
    
    if player_in_another_game:
        other_game_state = await game_repo.load_game(other_game_id)
        if other_game_state and other_game_state.phase == "waiting":
            await player_repo.delete_player(other_game_id, message.from_user.id)
            try:
                await update_players_list_redis(other_game_id, bot)
            except Exception:
                pass
        else:
            await message.answer("Siz hozirda boshqa guruhdagi faol o'yindasiz! Avvalgi o'yin yakunlanishini kuting.")
            return
    
    # VS game logic
    if ":vsgame" in game_state.mode:
        color_name = message.text.split("_")[-1]
        teams_count = int(game_state.mode.split("vsgame")[-1])
        
        # Get all players in this team
        all_players = await player_repo.get_all_players(game_id)
        team_players = [p for p in all_players if p.team == color_name and p.is_alive]
        
        # Check team capacity
        more_set, _ = await GroupMoreSet.get_or_create(chat_id=game_state.chat_id)
        max_team_players = more_set.max_players // teams_count
        
        if len(team_players) >= max_team_players:
            await message.answer(
                f"Kechirasiz, bu jamoasi to'lgan!", 
                reply_markup=go_group_button(chat.invite_link)
            )
            return
        
        # Join game with team
        success = await player_service.join_game(
            game_id=game_id,
            user_id=message.from_user.id,
            team=color_name
        )
        if not success:
            await message.answer("Kechirasiz, qo'shilishda xatolik yuz berdi!")
            return
        
        await message.answer(
            "Siz o'yinga muvaffaqiyatli qo'shildingiz!", 
            reply_markup=go_group_button(chat.invite_link)
        )
    else:
        # Normal game - no team
        success = await player_service.join_game(
            game_id=game_id,
            user_id=message.from_user.id,
            team=None
        )
        if not success:
            await message.answer("Kechirasiz, qo'shilishda xatolik yuz berdi!")
            return
        await message.answer(
            "Siz o'yinga muvaffaqiyatli qo'shildingiz!", 
            reply_markup=go_group_button(chat.invite_link)
        )
    
    # Update player list
    await update_players_list_redis(game_id, bot)
    
    # Check if max players reached - auto start
    all_players = await player_repo.get_all_players(game_id)
    more_set, _ = await GroupMoreSet.get_or_create(chat_id=game_state.chat_id)
    if len(all_players) >= more_set.max_players:
        # TODO: Implement starting_game_redis
        # await starting_game_redis(game_id=game_id, message=message, start=True, bot=bot)
        pass

async def join_game_handler_redis(message: Message, bot: Bot, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in redis_join_locks:
        redis_join_locks[user_id] = asyncio.Lock()
    async with redis_join_locks[user_id]:
        await _join_game_handler_redis_core(message, bot, state)


async def update_players_list_redis(game_id: str, bot: Bot, new_msg: bool = False):
    """
    Redis version of update_players_list.
    Updates the player list message in the chat.
    
    Args:
        game_id: Game ID in Redis
        bot: Bot instance
        new_msg: If True, creates a new message instead of editing
    """
    
    game_state = await game_repo.load_game(game_id)
    if not game_state:
        return
    
    # Get all alive players
    players = await player_repo.get_alive_players(game_id)
    
    # Build message text
    message_text = f"<b>Ro'yxatdan o'tish davom etmoqda!</b>\nRo'yhatdan o'tganlar:\n\n"
    
    # VS game: group by teams
    if ":vsgame" in game_state.mode:
        colors_dict = TeamColors.all_colors_dict() if hasattr(TeamColors, 'all_colors_dict') else {}
        teams = {}
        for player in players:
            if player.team not in teams:
                teams[player.team] = []
            # Get user mention from database
            user = await User.get_or_none(user_id=player.user_id)
            clean_name = html.escape((user.full_name if user and user.full_name else player.first_name) or "O'yinchi")
            mention = f'<a href="tg://user?id={player.user_id}">{clean_name}</a>'
            teams[player.team].append(mention)
        
        for team, team_players in teams.items():
            for i, player_mention in enumerate(team_players):
                message_text += f"{colors_dict.get(team, team)} {i + 1}. {player_mention}\n"
        
        teams_count = int(game_state.mode.split("vsgame")[-1])
        join_markup = join_vsgame_button(game_id=game_id, team_count=teams_count)
    else:
        # Normal game: shuffle and show as comma-separated list
        player_mentions = []
        for player in players:
            user = await User.get_or_none(user_id=player.user_id)
            clean_name = html.escape((user.full_name if user and user.full_name else player.first_name) or "O'yinchi")
            mention = f'<a href="tg://user?id={player.user_id}">{clean_name}</a>'
            player_mentions.append(mention)
        
        random.shuffle(player_mentions)
        message_text += ", ".join(player_mentions)
        join_markup = await join_game_button(game_id)
    
    message_text += f"\n\nJami: <b>{len(players)}</b> ta"

    try:
        from utils.i18n import get_chat_lang, translate_text, translate_keyboard
        chat_lang = await get_chat_lang(game_state.chat_id)
        if chat_lang != "uz":
            message_text = translate_text(message_text, chat_lang)
            join_markup = translate_keyboard(join_markup, chat_lang)
    except Exception:
        pass
    
    if new_msg:
        # Create new message
        try:
            msg = await bot.send_message(
                chat_id=game_state.chat_id,
                text=message_text,
                reply_markup=join_markup,
                parse_mode="HTML"
            )
            try:
                await msg.pin()
            except:
                pass
            # Update message_id
            await game_repo.update_game_field(game_id, "message_id", msg.message_id)
        except:
            pass
    else:
        # Edit existing message
        try:
            await bot.edit_message_text(
                chat_id=game_state.chat_id,
                message_id=game_state.message_id,
                text=message_text,
                reply_markup=join_markup,
                parse_mode="HTML"
            )
        except:
            # If edit fails, try creating new message
            await update_players_list_redis(game_id, bot, new_msg=True)


async def kick_player_redis(message: Message, bot: Bot):
    """
    Redis version of kick_player.
    Admin command to kick a player from the game by their number.
    Usage: /kick <player_number>
    """
    # Check admin permissions
    admin = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if admin.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
        return 
    
    # Parse command
    parts = message.text.strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        return 
    
    try:
        target_number = int(parts[1])
    except ValueError:
        return 
    
    # Get active game from Redis
    active_game_id = await game_repo.get_active_game(message.chat.id)
    if not active_game_id:
        return
    
    
    game_state = await game_repo.load_game(active_game_id)
    if not game_state:
        return
    
    # Find player by maxsus_raqam
    all_players = await player_repo.get_alive_players(active_game_id)
    target_player = None
    for player in all_players:
        if getattr(player, 'maxsus_raqam', 0) == target_number:
            target_player = player
            break
    
    if not target_player:
        return
    
    # Mark player as dead
    target_player.is_alive = False
    await player_repo.save_player(target_player)
    
    # Handle based on game phase
    if game_state.phase == "waiting":
        # Remove from waiting list
        await player_repo.delete_player(active_game_id, target_player.user_id)
        await update_players_list_redis(active_game_id, bot)
        
        # Check if should auto-start
        remaining_players = await player_repo.get_alive_players(active_game_id)
        more_set, _ = await GroupMoreSet.get_or_create(chat_id=message.chat.id)
        if len(remaining_players) >= more_set.max_players:
            # TODO: Implement starting_game_redis
            # await starting_game_redis(game_id=active_game_id, message=message, start=True, bot=bot)
            pass
    else:
        # Game in progress - announce death
        colors_dct = TeamColors.all_colors_dict() if hasattr(TeamColors, 'all_colors_dict') else {}
        
        user = await User.get_or_none(user_id=target_player.user_id)
        if not user:
            return
        
        try:
            if ":vsgame" in game_state.mode:
                team_emoji = colors_dct.get(target_player.team, target_player.team)
                await bot.send_message(
                    message.chat.id,
                    f"{team_emoji}{user.mention} o'yindan admin tomonidan chiqarildi.\nU edi {target_player.role}",
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    message.chat.id,
                    f"{user.mention} o'yindan admin tomonidan chiqarildi.\nU edi {target_player.role}",
                    parse_mode="HTML"
                )
        except:
            pass
        
        # TODO: Implement assign_new_role_redis
        # await assign_new_role_redis(target_player, game_state, bot, message.chat.id, active_game_id)


async def leave_game_redis(message: Message, bot: Bot):
    """
    Redis version of leave_game.
    Player voluntarily leaves the game (suicide).
    """
    # Get or create user
    user, _ = await User.get_or_create(
        user_id=message.from_user.id,
        defaults={
            "full_name": message.from_user.full_name if message.from_user.full_name else "",
            "mention": message.from_user.mention_html()
        }
    )
    
    # Find player's active game using service
    result = await player_service.find_player_active_game(message.from_user.id)
    if not result:
        # User has no active game
        return
    
    player_game_id, player_state = result
    
    # Get game state
    game_state = await game_repo.load_game(player_game_id)
    if not game_state:
        return
    
    # Check if leaving is allowed
    game_set, _ = await GameSetPermissions.get_or_create(chat_id=game_state.chat_id)
    if not game_set.leave_qilish:
        await message.answer("Bu guruhda o'yinni tark etish mumkin emas!")
        return
    
    if game_state.phase == "waiting":
        # Remove from waiting list
        await player_repo.delete_player(player_game_id, message.from_user.id)
        await update_players_list_redis(player_game_id, bot)
        
        # Check if should auto-start
        remaining_players = await player_repo.get_all_players(player_game_id)
        more_set, _ = await GroupMoreSet.get_or_create(chat_id=game_state.chat_id)
        if len(remaining_players) >= more_set.max_players:
            # Auto-start if max players reached
            await starting_game_redis(
                game_id=player_game_id,
                message=message,
                bot=bot,
                start=True,
                paralar=None
            )
    elif game_state.is_active and game_state.phase not in ("waiting", "end"):
        # Game in progress - suicide
        # Mark as dead
        player_state.is_alive = False
        player_state.death_reason = "suicide"
        player_state.deaded_at = datetime.now(timezone.utc)
        await player_repo.save_player(player_state)
        
        # Notify player
        await bot.send_message(
            player_state.user_id,
            "Siz o'zingizni osib o'ldirdingiz! So'ngi so'zingizni aytishingiz mumkin!"
        )
        
        # Notify group
        try:
            await bot.send_message(
                game_state.chat_id,
                f"{user.mention} bu shaharning yovuzliklariga chiday olmadi va o'zini osib qo'ydi.\n\nU edi {player_state.role}",
                parse_mode="HTML"
            )
        except Exception:
            pass
    else:
        player_state.is_alive = False
        await player_repo.save_player(player_state)


async def start_game_handler_redis(message: Message, bot: Bot, state):
    """
    Redis version of start_game_handler.
    Initiates game start - checks permissions and player count.
    """
    
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
    
    # Check permissions
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
    
    if start_perm == "admin":
        allowed = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    elif start_perm == "member":
        allowed = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR, ChatMemberStatus.MEMBER]
    elif start_perm == "ega":
        # Check if user is game creator
        active_game_id = await game_repo.get_active_game(message.chat.id)
        if active_game_id:
            game_state = await game_repo.load_game(active_game_id)
            if game_state and game_state.creator_id == message.from_user.id:
                allowed = True
    
    if not allowed:
        return
    
    # Get active game from Redis
    active_game_id = await game_repo.get_active_game(message.chat.id)
    if not active_game_id:
        await message.answer("❗ O'yinni boshlash uchun /game buyrug'ini yuboring.")
        return
    
    game_state = await game_repo.load_game(active_game_id)
    if not game_state:
        await message.answer("❗ O'yinni boshlash uchun /game buyrug'ini yuboring.")
        return
    
    if game_state.phase != "waiting":
        return
    
    # Get all players
    players = await player_repo.get_alive_players(active_game_id)
    if len(players) < 4:
        await message.answer("❗ O'yinni boshlash uchun kamida 4 ta ishtirokchi kerak.")
        return
    
    # Handle para mode (pairs)
    if game_state.mode in ["para x classic", "para x super", "para x mega"]:
        
        # Get all paras
        player_user_ids = {p.user_id for p in players}
        all_paras_raw = await Paralar.all().prefetch_related("user1", "user2")
        all_paras = [
            para for para in all_paras_raw
            if para.user1.id in player_user_ids or para.user2.id in player_user_ids
        ]
        
        # Build para map
        para_map = {}
        for para in all_paras:
            para_map.setdefault(para.user1.id, para.user2.id)
            para_map.setdefault(para.user2.id, para.user1.id)
        
        # Find valid pairs
        paralar = []
        used_players = set()
        players_to_remove = []
        
        for player in players:
            if player.user_id in used_players:
                continue
            
            partner_id = para_map.get(player.user_id)
            if not partner_id:
                # No partner - remove player
                players_to_remove.append(player.user_id)
                continue
            
            # Find partner in players
            partner = next((p for p in players if p.user_id == partner_id and p.user_id not in used_players), None)
            if partner:
                # Valid pair
                paralar.append((player.user_id, partner.user_id))
                used_players.add(player.user_id)
                used_players.add(partner.user_id)
            else:
                # Partner not in game - remove player
                players_to_remove.append(player.user_id)
        
        # Remove players without pairs
        for user_id in players_to_remove:
            await player_repo.delete_player(active_game_id, user_id)
        
        # Recheck player count
        players = await player_repo.get_alive_players(active_game_id)
        if len(players) < 4:
            await message.answer("❗ O'yinni boshlash uchun kamida 4 ta ishtirokchi kerak.")
            return
        
        # Start game with pairs
        create_task(starting_game_redis(active_game_id, message, bot, start=True, paralar=paralar))
    else:
        # Start normal game
        create_task(starting_game_redis(active_game_id, message, bot, start=True))


async def starting_game_redis(game_id: str, message: Message, bot: Bot, start=False, paralar=None):
    """
    Redis version of starting_game - main game loop.
    Handles game initialization, role assignment, and game phases.
    """
    import asyncio
    from collections import defaultdict

    game_state = await game_repo.load_game(game_id)
    if not game_state:
        return
    
    chat_id = game_state.chat_id
    chat = await Chat.get(chat_id=chat_id)
    game_times, _ = await GameSetTime.get_or_create(chat_id=chat_id)
    
    if start:
        # Mark game as started
        game_state.phase = "night"
        game_state.started_at = datetime.now(timezone.utc)
        await game_repo.save_game(game_state)
        
        # Delete waiting message
        try:
            await bot.delete_message(chat_id, message_id=game_state.message_id)
        except:
            pass
        
        # Send game start message
        await bot.send_message(
            chat_id=chat_id,
            text=f"<b>O'yin boshlandi!</b>\nMode: {game_state.mode}",
            parse_mode="HTML",
            reply_markup=bot_link_markup
        )
        
        # Get all players
        players = await player_repo.get_alive_players(game_id)
        # Ensure all players have User and Profile records
        for player in players:
            user = await User.get_or_none(user_id=player.user_id)
            await Profile.get_or_create(
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
        
        # Role assignment
        await rol_taqsimlash_redis(players, bot, chat.chat_id, game_state.mode)
        
        # Role replacement check
        # await check_and_replace_missing_roles_redis(players, bot, chat, game_id)
    
    # Initialize counters
    night = 0
    day = 0
    
    # Update created_at timestamp
    game_state.created_at = datetime.now(timezone.utc)
    await game_repo.save_game(game_state)
    
    # Main game loop
    while game_state.phase != "end" and game_state.is_active:
        # Reload game state
        game_state = await game_repo.load_game(game_id)
        if not game_state or not game_state.is_active:
            break
        
        # Get alive players
        players = await player_repo.get_alive_players(game_id)
        
        # Check win conditions
        win_result = await check_win_conditions_redis(game_id, players, game_state, bot, chat)
        if win_result:
            # Game ended
            break
        
        # Check if no players left
        if len(players) == 0:
            await announce_game_result_redis(
                game_id, bot, chat,
                winner_roles=[RoleNames.SUIDSID, RoleNames.QASOSKOR, RoleNames.GAZABDOR]
            )
            game_state.phase = "end"
            game_state.is_active = False
            await game_repo.save_game(game_state)
            break
        
        # Phase execution
        if game_state.phase == "night":
            night += 1
            await execute_night_phase_redis(
                game_id, night, players, bot, chat, message, game_times, paralar
            )
            
            # Update phase
            game_state = await game_repo.load_game(game_id)
            if not game_state or not game_state.is_active:
                break
            game_state.phase = "day"
            await game_repo.save_game(game_state)
        
        elif game_state.phase == "day":
            day += 1
            await execute_day_phase_redis(
                game_id, day, players, bot, chat, message, game_times, paralar
            )
            
            # Update phase
            game_state = await game_repo.load_game(game_id)
            if not game_state or not game_state.is_active:
                break
            game_state.phase = "night"
            await game_repo.save_game(game_state)
    
    # Game ended - cleanup
    await cleanup_game_redis(game_id)


async def stop_game_handler_redis(message: Message, bot: Bot):
    """
    Redis version of stop_game_handler.
    Admin command to stop/cancel the active game.
    """
    import config
    
    # Get chat
    chat, _ = await Chat.get_or_create(
        chat_id=message.chat.id,
        defaults={"title": message.chat.title or 'nomsiz', "type": message.chat.type}
    )
    
    # Check permissions
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
    
    # Check if super admin
    if message.from_user.id in config.ADMINS:
        allowed = True
    elif stop_perm == "admin":
        allowed = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    elif stop_perm == "member":
        allowed = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR, ChatMemberStatus.MEMBER]
    elif stop_perm == "ega":
        # Check if user is game creator
        active_game_id = await game_repo.get_active_game(message.chat.id)
        if active_game_id:
            game_state = await game_repo.load_game(active_game_id)
            if game_state and game_state.creator_id == message.from_user.id:
                allowed = True
    
    if not allowed:
        return
    
    # Get active game from Redis
    active_game_id = await game_repo.get_active_game(message.chat.id)
    if not active_game_id:
        await message.answer("❌ Bekor qilinadigan aktiv o'yin topilmadi.")
        return
    
    game_state = await game_repo.load_game(active_game_id)
    if not game_state:
        await message.answer("❌ Bekor qilinadigan aktiv o'yin topilmadi.")
        return
    
    if game_state.phase in ["waiting", "night", "day"]:
        # Mark game as ended
        game_state.phase = "end"
        game_state.is_active = False
    
        await game_repo.save_game(game_state)
        # Delete game message
        try:
            await bot.delete_message(chat.chat_id, game_state.message_id)
        except:
            pass
        
        # Mark all players as dead
        all_players = await player_repo.get_all_players(active_game_id)
        for player in all_players:
            player.is_alive = False
            await player_repo.save_player(player)
        
        # Remove from active games
        await game_repo.remove_active_game(message.chat.id, active_game_id)
        
        # Cleanup Redis data (after 1 hour TTL)
        # Data will auto-expire, but we can cleanup immediately if needed
        # await game_repo.cleanup_game_data(active_game_id)
        
        await message.answer("🛑 O'yin bekor qilindi.")
    else:
        await message.answer("❌ Bekor qilinadigan aktiv o'yin topilmadi.")
