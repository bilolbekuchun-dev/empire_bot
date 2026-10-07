import html
import logging
import unicodedata
from typing import Any, Optional

from aiogram import BaseMiddleware, types
from aiogram.enums import ChatType, ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

# --- Sizning loyihangizdagi modellaringizni import qiling ---
# Tortoise ORM deb faraz qildim; nomlar sizdagidek:
# Chat, User, Blocked_user, WriteGroupPermis, Game, GamePlayer, GamePhase, ADMINS
from models.game_data import Chat, Game, GamePlayer, GamePhase
from models.user import User, Blocked_user
from models.game_set import WriteGroupPermis
from config import ADMINS
import time

logger = logging.getLogger(__name__)

bot_admin_cache = {}
chat_sync_cache = {}
user_sync_cache = {}
group_perm_cache = {}
game_phase_cache = {}
player_status_cache = {}

class GroupWriteGuardMiddleware(BaseMiddleware):
    """
    Guruhdagi yozish qoidalarini nazorat qiluvchi middleware:
    - Bot adminligi va delete ruxsatini tekshiradi
    - Guruh (title, invite_link) va user (full_name, mention) ni DB bilan sinxronlaydi
    - Slash (/) komandalarni o‘chiradi
    - TUN/KUN (day/afternoon) fazalarida group_perm asosida yozish cheklovlarini qo‘llaydi
    - Adminlarga '!' buyruqlariga faza va sozlamaga mos shartli ruxsat
    - O‘lik/uxlayotgan o‘yinchilarni (waitingdan boshqa fazalarda) cheklaydi

    Muhim: handler’ga uzatish uchun `return await handler(event, data)`; aks holda “zanjir” shu yerda tugaydi.
    """

    def __init__(self, *, warn_user_if_cant_delete: bool = False) -> None:
        """
        warn_user_if_cant_delete=True qilinsa, bot o‘chira olmasa ham foydalanuvchini ogohlantirishga urinadi.
        """
        super().__init__()
        self.warn_user_if_cant_delete = warn_user_if_cant_delete

    # --------------- Yordamchi funksiyalar ---------------

    @staticmethod
    def _is_group(message: types.Message) -> bool:
        return message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP)

    @staticmethod
    def _is_admin_status(status_value: Any) -> bool:
        sv = status_value.value if isinstance(status_value, ChatMemberStatus) else str(status_value)
        sv = sv.lower()
        return sv in {ChatMemberStatus.CREATOR.value, ChatMemberStatus.ADMINISTRATOR.value}

    @staticmethod
    def _sanitize_display_name(name: str) -> str:
        if not name:
            return name
        cleaned = "".join(ch for ch in name if unicodedata.category(ch) not in ("Mn", "Me", "Mc"))
        return cleaned if cleaned.strip() else "O'yinchi"

    @staticmethod
    async def _delete_quietly(message: types.Message) -> None:
        try:
            await message.delete()
        except Exception:
            pass

    async def _bot_admin_and_can_delete(self, message: types.Message, force: bool = False) -> tuple[bool, bool]:
        now = time.time()
        chat_id = message.chat.id
        if not force and chat_id in bot_admin_cache and now - bot_admin_cache[chat_id]['time'] < 300:
            return bot_admin_cache[chat_id]['is_admin'], bot_admin_cache[chat_id]['can_delete']

        try:
            me = await message.bot.get_chat_member(message.chat.id, message.bot.id)
        except (TelegramForbiddenError, TelegramBadRequest):
            bot_admin_cache[chat_id] = {'time': now, 'is_admin': False, 'can_delete': False}
            return False, False
        except Exception as e:
            logger.warning("Bot admin check failed transiently for chat %s: %r", chat_id, e)
            if chat_id in bot_admin_cache:
                return bot_admin_cache[chat_id]['is_admin'], bot_admin_cache[chat_id]['can_delete']
            return True, True

        can_delete = True
        if hasattr(me, "can_delete_messages"):
            try:
                can_delete = bool(me.can_delete_messages)
            except Exception:
                can_delete = True

        is_admin = self._is_admin_status(getattr(me, "status", ""))
        bot_admin_cache[chat_id] = {'time': now, 'is_admin': is_admin, 'can_delete': can_delete}
        return is_admin, can_delete

    async def _sync_chat_db(self, message: types.Message) -> None:
        now = time.time()
        chat_id = message.chat.id
        cached = chat_sync_cache.get(chat_id)
        if cached and now - cached['time'] < 120 and cached.get('title') == message.chat.title:
            return

        chat, _ = await Chat.get_or_create(
            chat_id=message.chat.id,
            defaults={"title": message.chat.title, "type": str(message.chat.type)},
        )

        updated = False
        if message.chat.title and message.chat.title != chat.title:
            chat.title = message.chat.title
            updated = True

        if message.chat.username:
            new_link = f"https://t.me/{message.chat.username}"
            if new_link != chat.invite_link:
                chat.invite_link = new_link
                updated = True

        if updated:
            await chat.save()

        chat_sync_cache[chat_id] = {'time': now, 'title': message.chat.title}

    async def _sync_user_db_or_blocked(self, message: types.Message) -> bool:
        if not message.from_user:
            return True

        fu = message.from_user
        now = time.time()
        cached = user_sync_cache.get(fu.id)
        if cached and now - cached['time'] < 120 and cached.get('full_name') == fu.full_name:
            return cached.get('is_blocked', False)

        clean_full_name = html.escape(self._sanitize_display_name((fu.full_name or "")[:100]))
        mention = fu.mention_html(clean_full_name)

        user, _ = await User.get_or_create(
            user_id=fu.id,
            defaults={"full_name": clean_full_name, "mention": mention, "is_bot": fu.is_bot},
        )

        updated = False
        if user.full_name != clean_full_name:
            user.full_name = clean_full_name
            updated = True
        if user.mention != mention:
            user.mention = mention
            updated = True
        if updated:
            await user.save()

        is_blocked = bool(await Blocked_user.filter(user=user).first())
        user_sync_cache[fu.id] = {'time': now, 'full_name': fu.full_name, 'is_blocked': is_blocked}
        return is_blocked

    @staticmethod
    def _admin_command_allowed(phase: str | None, group_perm: Optional[WriteGroupPermis]) -> bool:
        """
        Adminlar uchun '!' buyruqlariga ruxsat siyosati:
        - night faza: group_perm.night != "ega" bo‘lsa ruxsat
        - day/afternoon: group_perm.day  != "ega" bo‘lsa ruxsat
        - boshqa hollarda: default False (faqat o‘yin fazalarida ishlasin)
        """
        if not group_perm:
            return False
        if phase == "night":
            return getattr(group_perm, "night", None) != "ega"
        if phase in ("day", "afternoon"):
            return getattr(group_perm, "day", None) != "ega"
        return False

    @staticmethod
    def _who_can_write(mode_value: Optional[str], *, is_player: bool, is_alive: bool) -> bool:
        """
        'all'    → hamma
        'member' → faqat o‘yinchilar (tirik/o'lgan)
        'alive'  → faqat tirik o‘yinchilar
        boshqasi ('ega', 'admin') → ruxsat yo‘q
        """
        if not mode_value:
            return True
        mode_value = mode_value.lower()
        if mode_value == "all":
            return True
        if mode_value == "member":
            return is_player
        if mode_value == "alive":
            return is_player and is_alive
        return False

    async def _phase_info(self, game: Game) -> tuple[Optional[str], bool]:
        night_phase = await GamePhase.filter(game=game, phase_type="night", is_end=False).first()
        if night_phase:
            return "night", False

        day_or_afternoon = await GamePhase.filter(
            game=game, phase_type__in=["day", "afternoon", "morning"], is_end=False
        ).first()
        if day_or_afternoon:
            return day_or_afternoon.phase_type, False

        is_waiting = getattr(game, "phase", "") == "waiting"
        phase_key = getattr(game, "phase", None)
        return phase_key, is_waiting

    # --------------- Asosiy chaqiruv ---------------

    async def __call__(self, handler, event: types.Message, data: dict) -> Any:
        if not isinstance(event, types.Message):
            return await handler(event, data)

        message = event
        
        # Xizmat xabarlarini o'tkazib yuborish
        if getattr(message, "new_chat_members", None) or getattr(message, "left_chat_member", None) or getattr(message, "new_chat_title", None):
            return await handler(event, data)

        # Private chat — bu middleware cheklamaydi
        if message.chat.type == ChatType.PRIVATE:
            return await handler(event, data)

        if not self._is_group(message):
            return await handler(event, data)

        # 1) Bot adminligi va delete ruxsatlari
        bot_is_admin, bot_can_delete = await self._bot_admin_and_can_delete(message)
        if not bot_is_admin:
            bot_is_admin, bot_can_delete = await self._bot_admin_and_can_delete(message, force=True)
        if not bot_is_admin:
            try:
                await message.answer(
                    "<b>❗️ Bot guruhda admin emas! Bot muammosiz ishlashi uchun botni guruhga admin qiling "
                    "va xabarlarni o‘chirish ruxsatini bering.</b>",
                    parse_mode="HTML",
                )
            except Exception:
                pass
            return

        # 2) Chat ma'lumotini DB bilan sinxronlash (title, invite_link)
        try:
            await self._sync_chat_db(message)
        except Exception as e:
            logger.warning("Chat sync failed: %r", e)

        # 3) Userni DB bilan sinxronlash; bloklangan bo‘lsa — to‘xtaymiz
        try:
            if await self._sync_user_db_or_blocked(message):
                if bot_can_delete:
                    await self._delete_quietly(message)
                return
        except Exception as e:
            logger.warning("User sync failed: %r", e)

        # 4) Redis va DB o'yini hamda fazasini aniqlash
        chat_id = message.chat.id
        msg_text = (message.text or message.caption or "").strip()
        phase_key = None
        is_game_active = False

        try:
            from utils.redis_game.repositories.game_repository import game_repository
            redis_game_id = await game_repository.get_active_game(chat_id)
            if redis_game_id:
                rg = await game_repository.load_game(redis_game_id)
                if rg and rg.is_active:
                    phase_key = rg.phase
                    is_game_active = (rg.phase != "waiting")
        except Exception:
            pass

        group_perm: Optional[WriteGroupPermis] = await WriteGroupPermis.filter(
            chat_id=chat_id
        ).first()

        game: Optional[Game] = None
        if not is_game_active:
            game = await Game.filter(chat__chat_id=chat_id, is_active=True).first()
            if game:
                p_key, is_waiting = await self._phase_info(game)
                if not is_waiting:
                    phase_key = p_key
                    is_game_active = True

        # 5) TUN FAZASI UCHUN MAXSUS CHEKLOV:
        # Adminlar faqat boshiga '!' qo'yib, yoki VIP obunasi borlar yozishi mumkin.
        # Qolgan barcha xabarlar (shu jumladan owner'ning oddiy xabarlari ham) o'chiriladi!
        if is_game_active and phase_key == "night":
            is_vip = False
            if message.from_user:
                try:
                    from models.user import VipUser
                    is_vip = bool(await VipUser.filter(user__user_id=message.from_user.id).first())
                except Exception:
                    is_vip = False

            if is_vip:
                return await handler(message, data)

            is_admin = False
            if message.from_user:
                if message.from_user.id in set(ADMINS):
                    is_admin = True
                else:
                    try:
                        m = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
                        is_admin = self._is_admin_status(getattr(m, "status", ""))
                    except Exception:
                        is_admin = False

            if is_admin and msg_text.startswith("!"):
                return await handler(message, data)

            if bot_can_delete:
                await self._delete_quietly(message)
            return

        # 6) Slash komandalar — o‘chiramiz va to‘g‘ridan-to‘g‘ri handlerlarga uzatamiz
        if msg_text and (msg_text.startswith("/") or msg_text.startswith("!")):
            if bot_can_delete:
                await self._delete_quietly(message)
            return await handler(message, data)

        # 7) Superadmin aniqlash
        is_superadmin = message.from_user and (message.from_user.id in set(ADMINS))
        if is_superadmin:
            return await handler(message, data)

        # O‘yin bo‘lmasa — hech qanday cheklov yo‘q
        if not is_game_active and not game:
            return await handler(message, data)

        # 8) O‘yinchi ma’lumotlarini tekshirish (Redis hamda DB o'yinlari uchun)
        is_player = False
        is_alive = False
        is_sleep = False

        if message.from_user:
            user_id = message.from_user.id
            if active_redis_id:
                try:
                    from utils.redis_game.repositories.player_repository import player_repository
                    rp = await player_repository.load_player(active_redis_id, user_id)
                    if rp:
                        is_player = True
                        is_alive = rp.is_alive
                        is_sleep = getattr(rp, "is_sleep", False)
                except Exception:
                    pass

            if not is_player and game:
                gp = await GamePlayer.filter(game=game, user__user_id=user_id).first()
                if gp:
                    is_player = True
                    is_alive = gp.is_alive
                    is_sleep = getattr(gp, "is_sleep", False)

        # 9) O'lik yoki uxlayotgan o'yinchi o'yin davomida yozsa — XABARNI O'CHIRISH!
        if is_player and (not is_alive or is_sleep):
            if bot_can_delete:
                await self._delete_quietly(message)
            return

        # 10) Guruh ruxsatlariga mos ravishda kunduzgi yozish tekshiruvi
        if phase_key in ("day", "afternoon", "morning", "day_actions") and group_perm:
            day_mode = getattr(group_perm, "day", "all")
            allowed = self._who_can_write(day_mode, is_player=is_player, is_alive=is_alive)
            if not allowed:
                if bot_can_delete:
                    await self._delete_quietly(message)
                return

        # Hammasi joyida: handlerlarga uzatamiz
        return await handler(message, data)
