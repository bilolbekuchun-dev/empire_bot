from aiogram.filters import Filter
from aiogram.types import Message
from aiogram.enums import ChatMemberStatus
from models.game_data import Game, GamePhase, GamePlayer, Chat
from models.game_set import BlockGrousp, WriteGroupPermis
from aiogram.enums import ChatType
from models.user import User, Blocked_user, VipUser
from utils.role_names import RoleNames
from aiogram.types import ChatPermissions
from asyncio import sleep
import re
from datetime import datetime, timedelta
from config import ADMINS
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
import time

bot_admin_cache = {}

class DelCommands(Filter):
    async def __call__(self, message: Message, state: FSMContext):
        # 0. Xizmat xabarlarini o'tkazib yuborish
        if getattr(message, "new_chat_members", None) or getattr(message, "left_chat_member", None) or getattr(message, "new_chat_title", None):
            return False

        # 1. Bot adminligini keshlangan tarzda tekshirish
        now = time.time()
        chat_id = message.chat.id
        is_bot_admin = True
        if chat_id in bot_admin_cache and now - bot_admin_cache[chat_id]['time'] < 300:
            is_bot_admin = bot_admin_cache[chat_id]['is_admin']
        else:
            try:
                me = await message.bot.get_chat_member(message.chat.id, message.bot.id)
                is_bot_admin = me.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
                bot_admin_cache[chat_id] = {'time': now, 'is_admin': is_bot_admin}
            except (TelegramForbiddenError, TelegramBadRequest):
                bot_admin_cache[chat_id] = {'time': now, 'is_admin': False}
                is_bot_admin = False
            except Exception:
                # Vaqtinchalik xato — "admin emas" deb keshlab guruhni bloklamaymiz
                is_bot_admin = bot_admin_cache.get(chat_id, {}).get('is_admin', True)

        if not is_bot_admin and message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            # Kesh eskirgan bo'lishi mumkin — xabar ko'rsatishdan oldin Telegram'dan qayta tekshiramiz
            try:
                me = await message.bot.get_chat_member(message.chat.id, message.bot.id)
                is_bot_admin = me.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
                bot_admin_cache[chat_id] = {'time': time.time(), 'is_admin': is_bot_admin}
            except Exception:
                is_bot_admin = True

        if not is_bot_admin and message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            # Xabarni qayta-qayta yubormaslik uchun faqat komanda bo'lsa javob berish
            if message.text and message.text.startswith("/"):
                try:
                    await message.answer(
                        "<b>❗️ Bot guruhda admin emas! Bot muammosiz ishlashi uchun botni guruhga admin qiling hamda unga bosh admin darajasidagi ruxsatlarni bering!</b>",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
            return False

        if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            await state.update_data(last_check_chat=datetime.now())
            try:
                chat, _ = await Chat.get_or_create(
                    chat_id=message.chat.id,
                    defaults={"title": message.chat.title, "type": str(message.chat.type)},
                )
            except:
                chats = await Chat.filter(chat_id=message.chat.id).all()
                if chats:
                    chat = chats[0]
                    for c in chats[1:]:
                        await c.delete()
                else:
                    chat = await Chat.create(chat_id=message.chat.id, title=message.chat.title, type=str(message.chat.type))

            updated = False
            if message.chat.username:
                new_link = f"https://t.me/{message.chat.username}"
                if chat.invite_link != new_link:
                    chat.invite_link = new_link
                    updated = True
            elif not chat.invite_link:
                try:
                    from utils.telegram_utils import get_chat_join_link
                    link = await get_chat_join_link(message.bot, message.chat.id)
                    if link:
                        chat.invite_link = link
                        updated = True
                except Exception:
                    pass
                    
            if message.chat.title and message.chat.title != chat.title:
                chat.title = message.chat.title
                updated = True
                
            if updated:
                await chat.save()
        
        if message.from_user:
            from_user = message.from_user
            
            clean_full_name = re.sub(r'[<>]', '', from_user.full_name[:100])
            
            mention = from_user.mention_html(clean_full_name)

            try:
                user, _ = await User.get_or_create(
                    user_id=from_user.id,
                    defaults={
                        "full_name": clean_full_name,
                        "mention": mention,
                        "is_bot": from_user.is_bot,
                    },
                )
            except Exception:
                users = await User.filter(user_id=from_user.id).order_by("id").all()
                if users:
                    user = users[0]
                    for u in users[1:]:
                        await u.delete()
                else:
                    user = await User.create(
                        user_id=from_user.id,
                        full_name=clean_full_name,
                        mention=mention,
                        is_bot=from_user.is_bot,
                    )
            chat_is_blocked = await BlockGrousp.filter(chat_id=message.chat.id).first()
            if chat_is_blocked:
                if message.text:
                    if message.text != "/ungblock":
                        return True
                


            user_is_blocked = await Blocked_user.filter(user=user).first()
            if user_is_blocked:
                return True
            updated = False

            if user.full_name != clean_full_name:
                user.full_name = clean_full_name
                updated = True

            if user.mention != mention:
                user.mention = mention
                updated = True
                
            if updated:
                await user.save()

        if message.chat.type == ChatType.PRIVATE:
            return False
        msg_text = (message.text or message.caption or "").strip()
        if not msg_text:
            return False

        # Tun fazasi ekanligini tekshirish (DB hamda Redis o'yinlari uchun)
        is_night = False
        try:
            game = await Game.filter(chat__chat_id=message.chat.id, is_active=True).first()
            if game:
                night_phase = await GamePhase.filter(game=game, phase_type="night", is_end=False).first()
                if night_phase:
                    is_night = True

            if not is_night:
                from utils.redis_game.repositories.game_repository import game_repository
                rg_id = await game_repository.get_active_game(message.chat.id)
                if rg_id:
                    rg = await game_repository.load_game(rg_id)
                    if rg and rg.is_active and rg.phase == "night":
                        is_night = True
        except Exception:
            pass

        if is_night:
            # Tun fazasida: '!' bilan boshlangan xabarlar o'chirilmaydi, '!'siz yozilganlar o'chiriladi
            if msg_text.startswith("!"):
                return False
            else:
                try:
                    await message.delete()
                except Exception:
                    pass
                return True

        if msg_text.startswith("/") or msg_text.startswith("!"):
            try:
                await message.delete()
            except Exception:
                pass
            return True

        admin = False
        member = None

        # 1. User adminligini tekshirish
        if message.from_user:
            try:
                member = await message.bot.get_chat_member(
                    message.chat.id, message.from_user.id
                )
                if member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]:
                    admin = True
            except Exception:
                pass


        # 2. Guruh sozlamalari va o'yin mavjudligini tekshirish
        group_perm = await WriteGroupPermis.filter(chat_id=message.chat.id).first()
        
        game = await Game.filter(chat__chat_id=message.chat.id, is_active=True).first()
        if not game:
            return

        # 3. Faza aniqlash
        night_phase = await GamePhase.filter(game=game, phase_type="night", is_end=False).first()
        day_or_afternoon_phase = await GamePhase.filter(game=game, phase_type__in=["day", "afternoon", "morning"], is_end=False).first()
        if group_perm and night_phase and group_perm.night == "all":
            return  # tunda hammaga yozishga ruxsat

        if group_perm and day_or_afternoon_phase and group_perm.day == "all":
            return  # kunduzi hammaga yozishga ruxsat

        # 4. Adminlarga "!buyruqlar"ga ruxsat berish (faqat tunda yoki kunduzi, sozlamaga qarab)
        admin_perm = group_perm and ((night_phase and group_perm.night != "ega") or (day_or_afternoon_phase and group_perm.day != "ega"))
        if message.text:
            is_vip = await VipUser.filter(user__user_id=message.from_user.id).first()
            if is_vip:
                return
            if ((admin and message.text.startswith("!") and admin_perm) or message.from_user.id in ADMINS):
                return  # admin yoki superadmin komandani ishlatmoqda

        # 5. O‘yinchi aniqlash
        player = await GamePlayer.filter(game=game, user__user_id=message.from_user.id).first()

        # 6. TUNDA yozish ruxsatlari
        if night_phase and group_perm:
            if group_perm.night == "all": return
            if (
                (group_perm.night == "alive" and not (player and player.is_alive)) or
                (group_perm.night == "member" and not player) or
                (group_perm.night not in ["all", "member", "alive"])
            ):
                try:
                    await message.chat.restrict(user_id=message.from_user.id, permissions=ChatPermissions(can_send_messages=False), until_date=datetime.now()+timedelta(seconds=35))
                except:
                    pass
                try:
                    await message.delete()
                except: 
                    pass
                return

        # 7. KUNDUZI yozish ruxsatlari
        if day_or_afternoon_phase and group_perm:
            if group_perm.day == "all": return
            if (
                (group_perm.day == "alive" and not (player and player.is_alive)) or
                (group_perm.day == "member" and not player) or
                (group_perm.day not in ["all", "member", "alive"])
            ):
                try:
                    await message.chat.restrict(user_id=message.from_user.id, permissions=ChatPermissions(can_send_messages=False), until_date=datetime.now()+timedelta(seconds=35))
                except:
                    pass
                try:
                    await message.delete()
                except: 
                    pass
                
                return

        # 8. Kutishdan boshqa fazalarda, o‘lik yoki uxlayotgan o‘yinchi yozsa
        if not player or player.is_sleep:
            if game.phase != "waiting":
                try:
                    await message.chat.restrict(user_id=message.from_user.id, permissions=ChatPermissions(can_send_messages=False), until_date=datetime.now()+timedelta(seconds=35))
                except:
                    pass
                try:
                    await message.delete()
                except: 
                    pass
                return


class NightSheriklarMessages(Filter):
    async def __call__(self, message: Message):
        if message.chat.type != "private":
            return False
        user_id = message.from_user.id if message.from_user else 0
        if not user_id:
            return False

        try:
            from utils.redis_game.repositories.player_repository import player_repository as player_repo
            from utils.redis_game.repositories.game_repository import game_repository as game_repo
            from config import mafia_rollar
            from utils.role_names import RoleNames

            game_id = await player_repo.find_player_active_game(user_id)
            if not game_id:
                return False

            game_state = await game_repo.load_game(game_id)
            if not game_state or not game_state.is_active or game_state.phase not in ("night", "day"):
                return False

            player = await player_repo.load_player(game_id, user_id)
            if not player or not player.is_alive:
                return False

            alive_players = await player_repo.get_alive_players(game_id)
            if player.role in mafia_rollar:
                teammates = [p for p in alive_players if p.role in mafia_rollar and p.user_id != user_id]
            elif player.role in (RoleNames.KOMISSAR, RoleNames.SERJANT):
                teammates = [p for p in alive_players if p.role in (RoleNames.KOMISSAR, RoleNames.SERJANT) and p.user_id != user_id]
            else:
                teammates = [p for p in alive_players if p.role == player.role and p.user_id != user_id]

            return len(teammates) > 0
        except Exception:
            return False

class SayLastWordFilter(Filter):
    async def __call__(self, message: Message):
        if not message.text:
            return False
        if message.chat.type != "private": 
            return False
        user_id = message.from_user.id
        
        # 1. Avval Redis o'yinlarida o'lgan va oxirgi so'z aytmagan player borligini tekshiramiz
        try:
            from utils.redis_game.services.player_service import player_service
            redis_res = await player_service.find_player_dead_last_word_game(user_id)
            if redis_res:
                return True
        except Exception:
            pass

        # 2. Eski DB o'yini:
        user = await User.filter(user_id=user_id).first()
        if not user: 
            return False
        player = await GamePlayer.filter(user=user, is_alive=False).last()
        if not player:
            return False
        await player.fetch_related("game")
        game = player.game
        if not game.is_active: 
            return False
        if player.is_sayed_last_word:
            return False
        return True