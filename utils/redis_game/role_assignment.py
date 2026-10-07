"""
Simplified role assignment system for Redis.
Uses RoleConfiguration for clean, maintainable code.
"""
import random
from typing import List
from aiogram import Bot
from models.user import User, Profile, ActiveRole
from models.game_data import Chat
from models.game_set import GamingOnChat, CommandPermissionsChat, GameModeSet, GameSetPermissions, GroupMoreSet, GameSetListRoles
from utils.role_names import RoleNames
from utils.role_configuration import RoleConfiguration
from utils.roles_text import Roles
from keyboards.game_keyboard import go_group_button
from tortoise.transactions import in_transaction


async def rol_taqsimlash_redis(
    players: List,  # List of PlayerState objects
    bot: Bot,
    chat_id: int,
    game_mode: str
) -> List:
    """
    Redis uchun soddalashtirilgan rol taqsimlash.
    
    Args:
        players: PlayerState objectlar listi
        bot: Bot instance
        chat_id: Chat ID
        game_mode: O'yin mode'i (classic, super, mega, etc.)
        
    Returns:
        Updated players with assigned roles
    """
    async with in_transaction():
        n = len(players)
        
        # Get role configuration for this mode and player count
        rollar = RoleConfiguration.get_roles_for_mode(game_mode, n)
        
        # Get banned roles setting
        role_set, _ = await GameSetListRoles.get_or_create(chat_id=chat_id)
        
        # Add FUQARO for remaining players
        fuqarolar_soni = n - len(rollar)
        if fuqarolar_soni > 0:
            rollar += [RoleNames.FUQARO] * fuqarolar_soni
        
        # Filter banned roles
        filtered_rollar = _filter_banned_roles(rollar, role_set, game_mode)
        
        # Count roles
        role_cap = {}
        for r in filtered_rollar:
            role_cap[r] = role_cap.get(r, 0) + 1
        
        # Shuffle players
        players_shuffled = list(players)
        random.shuffle(players_shuffled)
        
        # Get player profiles and active roles
        user_ids = [p.user_id for p in players_shuffled]
        profiles = await Profile.filter(user_id__in=user_ids).all()
        profile_by_user = {pr.user_id: pr for pr in profiles}
        
        # Ensure all players have profiles - create missing ones
        for player in players_shuffled:
            if player.user_id not in profile_by_user:
                # Get or create user
                user = await User.get_or_none(user_id=player.user_id)   
                # Create profile
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
                profile_by_user[player.user_id] = profile
        
        # Get active bought roles faqat on_active_role yoqilgan profillar uchun
        profile_ids = [
            profile_by_user[p.user_id].id 
            for p in players_shuffled
            if profile_by_user.get(p.user_id) and getattr(profile_by_user[p.user_id], "on_active_role", True)
        ]
        active_roles = await ActiveRole.filter(
            is_active=True,
            profile_id__in=profile_ids
        ).order_by("id").all()
        
        # Skip active roles for para and vs games
        if "para x" in game_mode or "vsgame" in game_mode:
            active_roles = []
        
        # Build profile to bought roles map
        profile_to_bought = {}
        for ar in active_roles:
            profile_to_bought.setdefault(ar.profile_id, []).append(ar)
        
        # Assign roles
        assigned_roles, used_active_ids, remaining_roles = _assign_roles_with_priority(
            players_shuffled,
            profile_by_user,
            profile_to_bought,
            role_cap
        )
        
        # Deactivate used active roles
        if used_active_ids:
            await ActiveRole.filter(id__in=used_active_ids).update(is_active=False)
        
        # Final assignment and notifications
        await _finalize_role_assignment(
            players_shuffled,
            assigned_roles,
            remaining_roles,
            profile_by_user,
            bot,
            chat_id
        )
    
    return players_shuffled


def _filter_banned_roles(
    rollar: List[str],
    role_set: GameSetListRoles,
    game_mode: str
) -> List[str]:
    """
    Taqiqlangan rollarni filterlash va FUQARO/BORI bilan almashtirish.
    """
    filtered_rollar = []
    required_roles = [
        RoleNames.DON,
        RoleNames.MAFIA,
        RoleNames.KOMISSAR,
        RoleNames.FUQARO
    ]
    
    for role in rollar:
        if role in required_roles or not role_set.is_banned(role):
            filtered_rollar.append(role)
        else:
            # Banned role - replace based on mode
            if "mega" in game_mode:
                filtered_rollar.append(RoleNames.BORI)
            else:
                filtered_rollar.append(RoleNames.FUQARO)
    
    return filtered_rollar


def _assign_roles_with_priority(
    players_shuffled: List,
    profile_by_user: dict,
    profile_to_bought: dict,
    role_cap: dict
) -> tuple:
    """
    Rollarni prioritet asosida taqsimlash.
    Birinchi navbatda sotib olingan rollar beriladi.
    
    Returns:
        (assigned_roles_dict, used_active_ids, remaining_roles_list)
    """
    assigned_role_by_profile = {}
    used_active_ids = []
    taken_count = {}
    
    # First pass: assign bought roles
    for p in players_shuffled:
        pr = profile_by_user[p.user_id]
        if pr.id in profile_to_bought:
            ars = profile_to_bought[pr.id]
            ars.sort(key=lambda x: (getattr(x, "created_at", None) or 0, x.id))
            
            for ar in ars:
                c = taken_count.get(ar.role, 0)
                cap = role_cap.get(ar.role, 0)
                if c < cap:
                    assigned_role_by_profile[pr.id] = ar.role
                    taken_count[ar.role] = c + 1
                    used_active_ids.append(ar.id)
                    break
    
    # Calculate remaining roles
    remain_cap = {}
    for r, cap in role_cap.items():
        used = taken_count.get(r, 0)
        left = cap - used
        if left > 0:
            remain_cap[r] = left
    
    remaining_roles = []
    for r, cnt in remain_cap.items():
        remaining_roles.extend([r] * cnt)
    random.shuffle(remaining_roles)
    
    return assigned_role_by_profile, used_active_ids, remaining_roles


async def _finalize_role_assignment(
    players_shuffled: List,
    assigned_roles: dict,
    remaining_roles: List[str],
    profile_by_user: dict,
    bot: Bot,
    chat_id: int
):
    """
    Final rol tayinlash va notification yuborish.
    """
    from utils.redis_game.repositories.player_repository import player_repository as player_repo

    chat = await Chat.get(chat_id=chat_id)
    err_players = []
    i = 1
    
    for p in players_shuffled:
        pr = profile_by_user[p.user_id]
        
        # Assign role
        if pr.id in assigned_roles:
            rol = assigned_roles[pr.id]
            # Notify about active role usage
            try:
                await bot.send_message(
                    p.user_id,
                    "🃏 <b>Faol roldan foydalanildi!</b>",
                    parse_mode="HTML"
                )
            except:
                pass
        else:
            # Assign from remaining roles
            if remaining_roles:
                rol = remaining_roles.pop(0)
            else:
                rol = RoleNames.FUQARO
        
        # Set role and special number
        p.role = rol
        p.maxsus_raqam = i
        i += 1

        # Save updated player state to Redis
        await player_repo.save_player(p)
        
        # Send role description
        try:
            user = await User.get(user_id=p.user_id)
            user_lang = user.lang if (user and user.lang) else "uz"
            rol_matni = Roles.get_by_role(rol, lang=user_lang)
            await bot.send_message(
                user.user_id,
                rol_matni,
                parse_mode="HTML",
                reply_markup=go_group_button(chat.invite_link)
            )
            
            # Increment games count
            pr.games_count += 1
            await pr.save()
        except Exception as e:
            # Player couldn't receive message - mark for removal
            err_players.append(p)
            i -= 1
    
    # Handle error players (couldn't receive private message)
    # In Redis version, we'll just mark them as inactive or remove
    for p in err_players:
        p.is_alive = False
        await player_repo.save_player(p)


async def get_role_config_text(mode: str = None) -> list:
    """
    Bot orqali role konfiguratsiyasini olish uchun helper.
    Telegram 4096 belgi limitini hisobga oladi.
    
    Args:
        mode: O'yin mode'i (agar None bo'lsa, barcha mode'lar ko'rsatiladi)
        
    Returns:
        List of formatted texts (bir yoki bir nechta xabar)
    """
    if mode:
        return RoleConfiguration.get_formatted_config(mode)
    else:
        # Show all available modes
        modes = RoleConfiguration.get_all_modes()
        text = "<b>📋 MAVJUD O'YIN MODE'LARI:</b>\n\n"
        for i, m in enumerate(modes, 1):
            text += f"{i}. <code>{m}</code>\n"
        text += "\n💡 Ma'lum bir mode uchun: <code>/roles {mode_name}</code>"
        return [text]
