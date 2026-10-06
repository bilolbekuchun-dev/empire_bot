"""
Redis-based game management functions.
Bu fayl o'yin yaratish va boshqarish uchun Redis dan foydalanadigan funksiyalarni o'z ichiga oladi.
"""
from aiogram import Bot
from aiogram.types import Message
from aiogram.enums import ChatMemberStatus
from aiogram.fsm.context import FSMContext
from datetime import datetime, timezone
from typing import Optional

from utils.redis_game.game_models_schema import GameState, PlayerState
from utils.redis_game.game_models_crud import game_repo
from utils.database import redis_client as r

from models.user import User, Profile
from models.game_data import Chat, Game, GamePlayer, PlayersGameBall
from models.game_set import (
    GamingOnChat, 
    GameModeSet, 
    CommandPermissionsChat
)
from keyboards.game_keyboard import join_vsgame_button, join_game_button


async def generate_game_id() -> int:
    """Yangi unique game ID yaratish."""
    game_id = await r.incr("game:id_counter")
    return game_id


async def check_permissions(
    bot: Bot, 
    message: Message, 
    chat_id: int, 
    user_id: int,
    permission_type: str = "game_cmd"
) -> bool:
    """User ning buyruqni bajarish huquqini tekshirish."""
    
    cmd_perm, _ = await CommandPermissionsChat.get_or_create(
        chat_id=chat_id,
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
    
    perm_level = getattr(cmd_perm, permission_type, "admin")
    member = await bot.get_chat_member(chat_id, user_id)
    
    if perm_level == "admin":
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    elif perm_level == "member":
        return member.status in [
            ChatMemberStatus.ADMINISTRATOR, 
            ChatMemberStatus.CREATOR, 
            ChatMemberStatus.MEMBER
        ]
    elif perm_level == "ega":
        return member.status == ChatMemberStatus.CREATOR
    
    return False


async def get_active_game(chat_id: int) -> Optional[GameState]:
    """Chat da aktiv o'yinni topish."""
    # Redis da barcha active gamelarni saqlaymiz
    game_ids_str = await r.smembers(f"chat:{chat_id}:active_games")
    
    if not game_ids_str:
        return None
    
    # Birinchi active gameni qaytaramiz
    for game_id_str in game_ids_str:
        game_id = int(game_id_str)
        game = await game_repo.load_game(game_id)
        if game and game.is_active:
            return game
    
    return None


async def add_active_game(chat_id: int, game_id: int):
    """Chat ga active game qo'shish."""
    await r.sadd(f"chat:{chat_id}:active_games", str(game_id))


async def remove_active_game(chat_id: int, game_id: int):
    """Chat dan active game olib tashlash."""
    await r.srem(f"chat:{chat_id}:active_games", str(game_id))


async def create_game_handler(
    message: Message, 
    bot: Bot,
    is_vs_game: bool = False
):
    """
    O'yin yaratish (Redis bilan).
    
    Args:
        message: Telegram message
        bot: Bot instance
        is_vs_game: True bo'lsa vs game, False bo'lsa oddiy game
    """
    
    # Bot va guruh tekshirish
    me = await bot.get_me()
    gaming_set, _ = await GamingOnChat.get_or_create(chat_id=message.chat.id, defaults={"bot_id": me.id})
    
    if not gaming_set.can_gaming:
        await message.answer(
            f"<b>⚠️ {message.from_user.mention_html()} bu guruhda o'yin o'ynash mumkin emas!</b>", 
            parse_mode="HTML"
        )
        return
    
    if message.chat.type not in ["group", "supergroup"]:
        return await message.answer("Bu buyruq faqat guruhda ishlaydi.")
    
    # User va Profile yaratish/olish (hali Tortoise da)
    user, _ = await User.get_or_create(
        user_id=message.from_user.id,
        defaults={
            "full_name": message.from_user.full_name or "",
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
    
    # Chat yaratish/olish
    chat, _ = await Chat.get_or_create(
        chat_id=message.chat.id,
        defaults={
            "title": message.chat.title, 
            "type": message.chat.type
        }
    )
    
    # Permission tekshirish
    allowed = await check_permissions(
        bot, 
        message, 
        chat.chat_id, 
        message.from_user.id,
        "game_cmd"
    )
    
    if not allowed:
        return
    
    # VS game uchun team count olish
    teams_count = 2
    if is_vs_game:
        teams_count = int(message.text[-1]) if message.text[-1].isdigit() else 2
        if teams_count < 2:
            return
    
    # Eski o'yinni tekshirish
    old_game = await get_active_game(message.chat.id)
    if old_game:
        if old_game.phase == "waiting":
            # Eski xabarni o'chirish
            try:
                await bot.delete_message(
                    chat_id=message.chat.id, 
                    message_id=old_game.message_id
                )
            except Exception:
                pass
            
            # TODO: update_players_list ni Redis versiyasiga o'tkazish kerak
            # await update_players_list_redis(old_game, bot, new_msg=True)
            return
        else:
            # O'yin boshlangan bo'lsa yangi ochib bo'lmaydi
            return
    
    # Game mode olish
    gmode = await GameModeSet.filter(chat_id=chat.chat_id).first()
    if not gmode:
        gmode = await GameModeSet.create(chat_id=chat.chat_id)
    
    # Mode nomini aniqlash
    if is_vs_game:
        mode = f"{gmode.mode_name}:vsgame{teams_count}"
    else:
        mode = gmode.mode_name
    
    # Yangi game ID yaratish
    game_id = await generate_game_id()
    
    # GameState yaratish
    game_state = GameState(
        game_id=game_id,
        chat_id=message.chat.id,
        creator_id=message.from_user.id,
        phase="waiting",
        mode=mode,
        is_active=True,
        message_id=0,  # Keyinroq yangilanadi
        created_at=datetime.now(timezone.utc)
    )
    
    # Redis ga saqlash
    await game_repo.save_game(game_state, ttl_sec=86400)  # 24 soat TTL
    
    # Active games listiga qo'shish
    await add_active_game(message.chat.id, game_id)
    
    # Join button yaratish
    if is_vs_game:
        join_markup = join_vsgame_button(game_id=game_id, team_count=teams_count)
    else:
        join_markup = await join_game_button(game_id)
    
    # Xabar yuborish
    msg = await message.answer(
        f"<b>Ro'yxatdan o'tish boshlandi!</b>",
        reply_markup=join_markup,
        parse_mode="HTML"
    )
    
    # Xabarni pin qilish
    try:
        await msg.pin()
    except Exception:
        pass
    
    # Message ID ni yangilash
    await game_repo.update_game_field(game_id, "message_id", msg.message_id)


async def join_player_to_game(
    game_id: int,
    user_id: int,
    team: Optional[str] = None
) -> bool:
    """
    O'yinga player qo'shish.
    
    Returns:
        True - muvaffaqiyatli qo'shildi
        False - xatolik yoki allaqachon qo'shilgan
    """
    # O'yin mavjudligini tekshirish
    game = await game_repo.load_game(game_id)
    if not game or game.phase != "waiting":
        return False
    
    # Player allaqachon qo'shilgan yoki yo'qligini tekshirish
    player_exists = await game_repo.player_exists(game_id, user_id)
    if player_exists:
        return False
    
    # Yangi player yaratish (role keyinroq beriladi)
    player_state = PlayerState(
        game_id=game_id,
        user_id=user_id,
        role="",  # Start vaqtida beriladi
        team=team,
        is_alive=True,
        is_sleep=False,
        life=100,
        joined_at=datetime.now(timezone.utc)
    )
    
    # Redis ga saqlash
    await game_repo.save_player(player_state, ttl_sec=86400)
    
    # Players set ga qo'shish
    await r.sadd(f"game:{game_id}:players", str(user_id))
    
    return True



async def get_game_players(game_id: int) -> list[PlayerState]:
    """O'yindagi barcha playerlarni olish."""
    player_ids_str = await r.smembers(f"game:{game_id}:players")
    
    players = []
    for player_id_str in player_ids_str:
        player_id = int(player_id_str)
        player = await game_repo.load_player(game_id, player_id)
        if player:
            players.append(player)
    
    return players


async def get_game_players_count(game_id: int) -> int:
    """O'yindagi playerlar sonini olish."""
    return await r.scard(f"game:{game_id}:players")


async def remove_player_from_game(game_id: int, user_id: int) -> bool:
    """Playerni o'yindan olib tashlash."""
    # Player mavjudligini tekshirish
    player_exists = await game_repo.player_exists(game_id, user_id)
    if not player_exists:
        return False
    
    # Redis dan o'chirish
    await game_repo.delete_player(game_id, user_id)
    
    # Players set dan olib tashlash
    await r.srem(f"game:{game_id}:players", str(user_id))
    
    return True


async def end_game(game_id: int, save_to_db: bool = True):
    """
    O'yinni yakunlash va tozalash.
    
    Args:
        game_id: O'yin ID
        save_to_db: True bo'lsa ma'lumotlarni Tortoise ORM ga saqlaydi (statistika uchun)
    """
    game = await game_repo.load_game(game_id)
    if not game:
        return
    
    # Game ni inactive qilish
    await game_repo.update_game_field(game_id, "is_active", False)
    await game_repo.update_game_field(game_id, "phase", "end")
    
    # Active games dan olib tashlash
    await remove_active_game(game.chat_id, game_id)
    
    # Agar statistika saqlanishi kerak bo'lsa
    if save_to_db:
        # Chat va Creator ni Tortoise ORM dan olish
        chat = await Chat.filter(chat_id=game.chat_id).first()
        creator = await User.filter(user_id=game.creator_id).first()
        
        if chat and creator:
            # Game ni Tortoise ORM ga saqlash (statistika uchun)
            game_db = await Game.create(
                chat=chat,
                creator=creator,
                is_active=False,
                mode=game.mode,
                created_at=game.created_at,
                phase="end",
                message_id=game.message_id
            )
            
            # Barcha playerlarni Redis dan olish va Tortoise ga saqlash
            player_ids_str = await r.smembers(f"game:{game_id}:players")
            
            for player_id_str in player_ids_str:
                player_id = int(player_id_str)
                
                # Redis dan player ma'lumotlarini olish
                player_state = await game_repo.load_player(game_id, player_id)
                if not player_state:
                    continue
                
                # User ni Tortoise ORM dan olish
                user = await User.filter(user_id=player_id).first()
                if not user:
                    continue
                
                # GamePlayer ni Tortoise ORM ga saqlash
                game_player = await GamePlayer.create(
                    user=user,
                    game=game_db,
                    role=player_state.role,
                    is_alive=player_state.is_alive,
                    joined_at=player_state.joined_at,
                    deaded_at=player_state.deaded_at,
                    is_sayed_last_word=player_state.is_sayed_last_word,
                    is_sleep=player_state.is_sleep,
                    osildi=player_state.osildi,
                    is_really_winner=player_state.is_really_winner,
                    maxsus_raqam=player_state.maxsus_raqam,
                    win=player_state.win,
                    life=player_state.life,
                    team=player_state.team
                )
                
                # PlayersGameBall yaratish (agar ball saqlanishi kerak bo'lsa)
                # Ball ma'lumotini Redis dan olish mumkin (agar saqlangan bo'lsa)
                ball_key = f"game:{game_id}:player:{player_id}:ball"
                ball = await r.get(ball_key)
                if ball:
                    await PlayersGameBall.create(
                        player=game_player,
                        game=game_db,
                        ball=int(ball)
                    )
    
    # Redis dan barcha game ma'lumotlarini tozalash
    player_ids_str = await r.smembers(f"game:{game_id}:players")
    
    for player_id_str in player_ids_str:
        player_id = int(player_id_str)
        # Player state ni o'chirish
        await game_repo.delete_player(game_id, player_id)
        # Ball ma'lumotini o'chirish
        await r.delete(f"game:{game_id}:player:{player_id}:ball")
    
    # Players set ni tozalash
    await r.delete(f"game:{game_id}:players")
    
    # Game state ni o'chirish
    await game_repo.delete_game(game_id)
    
    # Qo'shimcha ma'lumotlarni tozalash (phases, votes, actions)
    # Pattern bo'yicha barcha key'larni topib o'chirish
    keys_to_delete = []
    
    # Game bilan bog'liq barcha key'larni topish
    cursor = 0
    pattern = f"game:{game_id}:*"
    
    while True:
        cursor, keys = await r.scan(cursor, match=pattern, count=100)
        keys_to_delete.extend(keys)
        if cursor == 0:
            break
    
    # Barcha topilgan key'larni o'chirish
    if keys_to_delete:
        await r.delete(*keys_to_delete)


async def set_player_ball(game_id: int, user_id: int, ball: int):
    """Player uchun ball saqlash."""
    await r.set(f"game:{game_id}:player:{user_id}:ball", str(ball))


async def get_player_ball(game_id: int, user_id: int) -> int:
    """Player ning ball ini olish."""
    ball = await r.get(f"game:{game_id}:player:{user_id}:ball")
    return int(ball) if ball else 0


async def increment_player_ball(game_id: int, user_id: int, amount: int = 1):
    """Player ball ini oshirish."""
    await r.incrby(f"game:{game_id}:player:{user_id}:ball", amount)


async def update_player_profile_after_game(
    user_id: int,
    is_winner: bool,
    is_member: bool = True,
    ball: int = 0
):
    """
    O'yin tugagandan keyin player profileini yangilash.
    
    Args:
        user_id: User ID
        is_winner: G'olib bo'lsa True
        is_member: Guruh a'zosi bo'lsa True (ko'proq pul oladi)
        ball: Qo'shimcha ball (agar bor bo'lsa)
    """
    user = await User.filter(user_id=user_id).first()
    if not user:
        return
    
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
    
    # Dollar qo'shish
    if is_winner:
        profile.dollar += 20 if is_member else 10
        profile.wins += 1
    else:
        profile.dollar += 5 if is_member else 0
    
    # O'yinlar sonini oshirish
    profile.games_count += 1
    
    await profile.save()
    
    return profile


async def get_game_statistics(game_id: int) -> dict:
    """
    O'yin statistikasini olish.
    
    Returns:
        dict: {
            'total_players': int,
            'alive_players': int,
            'dead_players': int,
            'players': list[PlayerState]
        }
    """
    players = await get_game_players(game_id)
    
    alive = [p for p in players if p.is_alive]
    dead = [p for p in players if not p.is_alive]
    
    return {
        'total_players': len(players),
        'alive_players': len(alive),
        'dead_players': len(dead),
        'players': players
    }
