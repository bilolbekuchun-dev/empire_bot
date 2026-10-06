"""
Game Service - O'yin lifecycle boshqaruvi (yaratish, boshlash, tugatish).
"""
from typing import Optional
from datetime import datetime, timezone
from aiogram import Bot
from aiogram.types import Message
from aiogram.enums.chat_member_status import ChatMemberStatus

from utils.redis_game.game_models_schema import GameState
from utils.redis_game.repositories import game_repository, player_repository
from models.user import User, Profile
from models.game_data import Chat, Game, GamePlayer, PlayersGameBall
from models.game_set import GamingOnChat, GameModeSet, CommandPermissionsChat
from keyboards.game_keyboard import join_vsgame_button, join_game_button


class GameService:
    """O'yin lifecycle ni boshqaruvchi service."""
    
    @staticmethod
    async def create_game(
        message: Message,
        bot: Bot,
        is_vs_game: bool = False
    ) -> Optional[GameState]:
        """
        Yangi o'yin yaratish.
        
        Returns:
            GameState yoki None (agar xato bo'lsa)
        """
        # Bot va guruh tekshirish
        me = await bot.get_me()
        gaming_set, _ = await GamingOnChat.get_or_create(chat_id=message.chat.id, defaults={"bot_id": me.id})
        
        if not gaming_set.can_gaming:
            await message.answer(
                f"<b>⚠️ {message.from_user.mention_html()} bu guruhda o'yin o'ynash mumkin emas!</b>",
                parse_mode="HTML"
            )
            return None
        
        if message.chat.type not in ["group", "supergroup"]:
            await message.answer("Bu buyruq faqat guruhda ishlaydi.")
            return None
        
        # User va chat yaratish
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
        
        chat, _ = await Chat.get_or_create(
            chat_id=message.chat.id,
            defaults={
                "title": message.chat.title,
                "type": message.chat.type
            }
        )
        
        # Permissions tekshirish
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
        
        game_perm = getattr(cmd_perm, "game_cmd", "admin")
        member = await bot.get_chat_member(chat.chat_id, message.from_user.id)
        allowed = False
        
        if game_perm == "admin":
            allowed = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
        elif game_perm == "member":
            allowed = member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR, ChatMemberStatus.MEMBER]
        elif game_perm == "ega":
            allowed = member.status == ChatMemberStatus.CREATOR
        
        if not allowed:
            return None
        
        # VS game uchun team count
        teams_count = 2
        if is_vs_game:
            teams_count = int(message.text[-1]) if message.text[-1].isdigit() else 2
            if teams_count < 2:
                return None
        
        # Eski o'yin tekshirish
        active_game_id = await game_repository.get_active_game(message.chat.id)
        if active_game_id:
            old_game = await game_repository.load_game(active_game_id)
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
                    # Yangi xabar yuborish (player list bilan)
                    from utils.redis_game.handlers import update_players_list_redis
                    await update_players_list_redis(active_game_id, bot, new_msg=True)
                return None
        
        # Game mode
        gmode = await GameModeSet.filter(chat_id=chat.chat_id).first()
        if not gmode:
            gmode = await GameModeSet.create(chat_id=chat.chat_id)
        
        mode = f"{gmode.mode_name}:vsgame{teams_count}" if is_vs_game else gmode.mode_name
        
        # Game yaratish
        game_id = await game_repository.generate_id()
        
        game_state = GameState(
            game_id=game_id,
            chat_id=message.chat.id,
            creator_id=message.from_user.id,
            phase="waiting",
            mode=mode,
            is_active=True,
            message_id=0,
            created_at=datetime.now(timezone.utc)
        )
        
        # Redis ga saqlash
        await game_repository.save_game(game_state, ttl_sec=86400)
        await game_repository.add_active_game(message.chat.id, game_id)
        
        # Join button
        join_markup = (
            join_vsgame_button(game_id=game_id, team_count=teams_count)
            if is_vs_game
            else await join_game_button(game_id)
        )
        
        # Xabar yuborish
        msg = await message.answer(
            f"<b>Ro'yxatdan o'tish boshlandi!</b>",
            reply_markup=join_markup,
            parse_mode="HTML"
        )
        
        try:
            await msg.pin()
        except Exception:
            pass
        
        # Message ID yangilash
        await game_repository.update_game_field(game_id, "message_id", msg.message_id)
        
        return game_state
    
    @staticmethod
    async def end_game(game_id: int, save_to_db: bool = True):
        """
        O'yinni yakunlash va tozalash.
        
        Args:
            game_id: O'yin ID
            save_to_db: True bo'lsa statistikani Tortoise ga saqlaydi
        """
        game = await game_repository.load_game(game_id)
        if not game:
            return
        
        # Game ni inactive qilish
        await game_repository.update_game_fields(
            game_id,
            is_active=False,
            phase="end"
        )
        
        # Active games dan olib tashlash
        await game_repository.remove_active_game(game.chat_id, game_id)
        
        # Statistika saqlash
        if save_to_db:
            await GameService._save_game_to_db(game_id, game)
        
        # Redis dan tozalash
        await GameService._cleanup_redis(game_id)
    
    @staticmethod
    async def _save_game_to_db(game_id: int, game: GameState):
        """Game va playerlarni Tortoise ORM ga saqlash."""
        chat = await Chat.filter(chat_id=game.chat_id).first()
        creator = await User.filter(user_id=game.creator_id).first()
        
        if not chat or not creator:
            return
        
        # Game yaratish
        game_db = await Game.create(
            chat=chat,
            creator=creator,
            is_active=False,
            mode=game.mode,
            created_at=game.created_at,
            phase="end",
            message_id=game.message_id
        )
        
        # Playerlarni saqlash
        player_ids = await player_repository.get_player_ids(game_id)
        
        for player_id in player_ids:
            player_state = await player_repository.load_player(game_id, player_id)
            if not player_state:
                continue
            
            user = await User.filter(user_id=player_id).first()
            if not user:
                continue
            
            game_player = await GamePlayer.create(
                user=user,
                game=game_db,
                role=player_state.role,
                is_alive=player_state.is_alive,
                joined_at=player_state.joined_at,
                deaded_at=player_state.deaded_at,
                is_sayed_last_word=player_state.is_sayed_last_word,
                can_heal_self=player_state.can_heal_self,
                can_protection_self=player_state.can_protection_self,
                can_document_self=player_state.can_document_self,
                can_investigate_self=player_state.can_investigate_self,
                can_osishdan_himoya=player_state.can_osishdan_himoya,
                can_osishdan_himoya_adv=player_state.can_osishdan_himoya_adv,
                can_slip_himoya=player_state.can_slip_himoya,
                is_sleep=player_state.is_sleep
            )
            
            # Ball saqlash
            ball = await player_repository.get_ball(game_id, player_id)
            if ball:
                await PlayersGameBall.create(
                    player=game_player,
                    game=game_db,
                    ball=ball
                )
    
    @staticmethod
    async def _cleanup_redis(game_id: int):
        """Redis dan game ma'lumotlarini to'liq tozalash."""
        # Playerlar tozalash
        player_ids = await player_repository.get_player_ids(game_id)
        
        for player_id in player_ids:
            await player_repository.delete_player(game_id, player_id)
            await player_repository.delete_ball(game_id, player_id)
        
        # Players set
        await player_repository.remove_player_from_set(game_id, 0)  # Set ni tozalash
        
        # Game state
        await game_repository.delete_game(game_id)
        
        # Boshqa ma'lumotlar (pattern scan)
        await game_repository.cleanup_game_data(game_id)


# Global instance
game_service = GameService()
