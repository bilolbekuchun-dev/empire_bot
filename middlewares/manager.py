import html
import logging
import unicodedata
from typing import Any, Optional
from collections import OrderedDict
from time import monotonic, time

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

logger = logging.getLogger(__name__)

# LRU cache for bot admin status - prevents unbounded growth
_MAX_ADMIN_CACHE_SIZE = 1000
_ADMIN_CACHE_TTL = 300  # 5 minutes
bot_admin_cache = OrderedDict()

def _get_bot_admin_status(chat_id: int, is_admin: bool, can_delete: bool) -> dict:
    """Get or set bot admin status with LRU eviction."""
    now = monotonic()
    
    # Evict old entries
    while len(bot_admin_cache) > _MAX_ADMIN_CACHE_SIZE:
        bot_admin_cache.popitem(last=False)
    
    # Remove entries older than TTL
    expired_keys = [cid for cid, data in bot_admin_cache.items() 
                   if now - data['time'] > _ADMIN_CACHE_TTL]
    for cid in expired_keys:
        bot_admin_cache.pop(cid, None)
    
    # Add or update entry
    bot_admin_cache[chat_id] = {'time': now, 'is_admin': is_admin, 'can_delete': can_delete}
    bot_admin_cache.move_to_end(chat_id)
    
    return bot_admin_cache[chat_id]

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
        self._user_sync_cache: dict[int, float] = {}
        self._chat_sync_cache: dict[int, float] = {}
        self._blocked_users_cache: set[int] = set()
        self._last_blocked_cache_time: float = 0.0

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

    async def _bot_admin_and_can_delete(self, message: types.Message, force: bool = False) -> tuple[bool, bool, list[str]]:
        now = monotonic()
        chat_id = message.chat.id
        if not force and chat_id in bot_admin_cache and now - bot_admin_cache[chat_id]['time'] < _ADMIN_CACHE_TTL:
            return bot_admin_cache[chat_id]['is_admin'], bot_admin_cache[chat_id]['can_delete'], bot_admin_cache[chat_id].get('missing', [])

        try:
            from utils.bot_permissions import check_bot_group_permissions
            is_valid, missing = await check_bot_group_permissions(message.bot, chat_id)
            _get_bot_admin_status(chat_id, is_valid, is_valid)
            bot_admin_cache[chat_id]['missing'] = missing
            return is_valid, is_valid, missing
        except Exception as e:
            logger.warning("Bot admin check failed transiently for chat %s: %r", chat_id, e)
            if chat_id in bot_admin_cache:
                return bot_admin_cache[chat_id]['is_admin'], bot_admin_cache[chat_id]['can_delete'], bot_admin_cache[chat_id].get('missing', [])
            return True, True, []

    async def _sync_chat_db(self, message: types.Message) -> None:
        """
        Chat nomi DB bilan sinxronlash (300s TTL kesh bilan).
        """
        now = monotonic()
        chat_id = message.chat.id
        if chat_id in self._chat_sync_cache and now - self._chat_sync_cache[chat_id] < 300:
            return

        chat, _ = await Chat.get_or_create(
            chat_id=chat_id,
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

        self._chat_sync_cache[chat_id] = now
        if len(self._chat_sync_cache) > 1000:
            expired = [cid for cid, t in self._chat_sync_cache.items() if now - t > 300]
            for cid in expired:
                del self._chat_sync_cache[cid]
            while len(self._chat_sync_cache) > 1000:
                self._chat_sync_cache.pop(next(iter(self._chat_sync_cache)))

    async def _sync_user_db_or_blocked(self, message: types.Message) -> bool:
        """
        Userni DB bilan sinxronlash (300s TTL kesh bilan).
        """
        if not message.from_user:
            return True

        fu = message.from_user
        now = monotonic()

        if fu.id not in self._user_sync_cache or (now - self._user_sync_cache[fu.id] >= 300):
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

            self._user_sync_cache[fu.id] = now
            if len(self._user_sync_cache) > 5000:
                expired = [uid for uid, t in self._user_sync_cache.items() if now - t > 300]
                for uid in expired:
                    del self._user_sync_cache[uid]
                while len(self._user_sync_cache) > 5000:
                    self._user_sync_cache.pop(next(iter(self._user_sync_cache)))

        # Refresh blocked users cache every 60 seconds
        if now - self._last_blocked_cache_time > 60:
            blocked_rows = await Blocked_user.all().prefetch_related('user').values_list('user__user_id', flat=True)
            self._blocked_users_cache = set(blocked_rows)
            self._last_blocked_cache_time = now

        return fu.id in self._blocked_users_cache

    @staticmethod
    def _admin_command_allowed(phase: str | None, group_perm: Optional[WriteGroupPermis]) -> bool:
        if not group_perm:
            return False
        if phase == "night":
            return getattr(group_perm, "night", None) != "ega"
        if phase in ("day", "afternoon"):
            return getattr(group_perm, "day", None) != "ega"
        return False

    @staticmethod
    def _who_can_write(mode_value: Optional[str], *, is_player: bool, is_alive: bool) -> bool:
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
        """
        Joriy fazani aniqlash:
        Pervichno game.phase dan foydalanadi (night, day, afternoon, waiting), 
        kerak bo'lganda GamePhase holatini tekshiradi.
        """
        is_waiting = getattr(game, "phase", "") == "waiting"
        phase_key = getattr(game, "phase", None)
        if phase_key in ("night", "day", "afternoon", "waiting"):
            return phase_key, is_waiting

        night_phase = await GamePhase.filter(game=game, phase_type="night", is_end=False).first()
        if night_phase:
            return "night", False

        day_or_afternoon = await GamePhase.filter(
            game=game, phase_type__in=["day", "afternoon"], is_end=False
        ).first()
        if day_or_afternoon:
            return day_or_afternoon.phase_type, False

        return phase_key, is_waiting

    # --------------- Asosiy chaqiruv ---------------

    async def __call__(self, handler, event: types.TelegramObject, data: dict) -> Any:
        # CallbackQuery uchun ban tekshiruvi
        if isinstance(event, types.CallbackQuery):
            if event.from_user:
                try:
                    is_blocked = bool(await Blocked_user.filter(user__user_id=event.from_user.id).first())
                    if is_blocked:
                        await event.answer("🚫 Sizga botdan foydalanish taqiqlangan! (Siz bloklangansiz)", show_alert=True)
                        return
                except Exception:
                    pass
            return await handler(event, data)

        # Faqat Message bilan ishlaymiz
        if not isinstance(event, types.Message):
            return await handler(event, data)

        message = event
        
        # Xizmat xabarlarini o'tkazib yuborish (qotib qolish va mute qilishni oldini olish)
        if getattr(message, "new_chat_members", None) or getattr(message, "left_chat_member", None) or getattr(message, "new_chat_title", None):
            return await handler(event, data)

        # Private chat — bloklangan foydalanuvchilar uchun taqiq ko'rsatish
        if message.chat.type == ChatType.PRIVATE:
            if message.from_user:
                try:
                    is_blocked = bool(await Blocked_user.filter(user__user_id=message.from_user.id).first())
                    if is_blocked:
                        await message.answer(
                            "<b>🚫 Sizga botdan foydalanish taqiqlangan!</b>\n"
                            "<i>Siz bot adminlari tomonidan bloklangansiz.</i>",
                            parse_mode="HTML"
                        )
                        return
                except Exception:
                    pass
            return await handler(event, data)

        # Guruh/kanal bo‘lmasa ham ishlatmaslik
        if not self._is_group(message):
            return await handler(event, data)

        # 1) Bot adminligi va 3 ta majburiy ruxsatlar
        bot_is_admin, bot_can_delete, missing_perms = await self._bot_admin_and_can_delete(message)
        if not bot_is_admin:
            # Kesh eskirgan bo'lishi mumkin (bot hozirgina admin qilingan) — xabar ko'rsatishdan
            # oldin Telegram'dan darhol qayta tekshiramiz, shunda yolg'on ogohlantirish chiqmaydi.
            bot_is_admin, bot_can_delete, missing_perms = await self._bot_admin_and_can_delete(message, force=True)
        if not bot_is_admin:
            # Foydalanuvchini ogohlantiramiz (komanda bo'lsa javob beramiz, spam qilmaslik uchun)
            msg_text = (message.text or message.caption or "").strip()
            if msg_text and (msg_text.startswith("/") or msg_text.startswith("!")):
                try:
                    from utils.bot_permissions import get_permission_warning_text
                    await message.answer(
                        get_permission_warning_text(missing_perms),
                        parse_mode="HTML",
                    )
                except Exception:
                    pass
            # Handlerga uzatmaymiz — bu bot o‘zi ishlay olmaydi
            return

        # 2) Chat ma'lumotini DB bilan sinxronlash (title, invite_link)
        try:
            await self._sync_chat_db(message)
        except Exception as e:
            logger.warning("Chat sync failed: %r", e)

        # 3) Userni DB bilan sinxronlash va bloklanganligini tekshirish
        try:
            if await self._sync_user_db_or_blocked(message):
                msg_text = (message.text or message.caption or "").strip()
                # Guruhda oddiy suhbatlashishi mumkin, lekin bot buyruqlari (/give, /money, /para va hk) taqiqlanadi!
                if msg_text and (msg_text.startswith("/") or msg_text.startswith("!")):
                    if bot_can_delete:
                        await self._delete_quietly(message)
                    return
        except Exception as e:
            logger.warning("User sync failed: %r", e)

        # VIP foydalanuvchilar istagan vaqtida (tunda ham, o'lgan bo'lsa ham) yozishi mumkin
        if message.from_user:
            try:
                from models.user import VipUser
                if await VipUser.filter(user__user_id=message.from_user.id).exists():
                    msg_text = (message.text or message.caption or "").strip()
                    if msg_text and (msg_text.startswith("/") or msg_text.startswith("!")):
                        if bot_can_delete:
                            await self._delete_quietly(message)
                    return await handler(message, data)
            except Exception:
                pass

        # 4) Redis va DB o'yini hamda fazasini aniqlash
        chat_id = message.chat.id
        msg_text = (message.text or message.caption or "").strip()
        phase_key = None
        is_game_active = False
        redis_game_id = None

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

        game: Optional[Game] = None
        if not is_game_active:
            game = await Game.filter(chat__chat_id=chat_id, is_active=True).first()
            if game:
                p_key, is_waiting = await self._phase_info(game)
                if not is_waiting:
                    phase_key = p_key
                    is_game_active = True

        group_perm: Optional[WriteGroupPermis] = await WriteGroupPermis.filter(
            chat_id=chat_id
        ).first()

        # 5) O‘YINCHI MA’LUMOTLARINI TEKSHIRISH (Redis hamda DB o'yinlari uchun)
        is_player = False
        is_alive = False
        is_sleep = False

        if message.from_user and (is_game_active or game or redis_game_id):
            user_id = message.from_user.id
            if redis_game_id:
                try:
                    from utils.redis_game.repositories.player_repository import player_repository
                    rp = await player_repository.load_player(redis_game_id, user_id)
                    if rp:
                        is_player = True
                        is_alive = bool(rp.is_alive)
                        is_sleep = bool(getattr(rp, "is_sleep", False))
                except Exception:
                    pass

            if not is_player and game:
                try:
                    gp = await GamePlayer.filter(game=game, user__user_id=user_id).first()
                    if gp:
                        is_player = True
                        is_alive = bool(gp.is_alive)
                        is_sleep = bool(getattr(gp, "is_sleep", False))
                except Exception:
                    pass

        # 6) O'LGAN YOKI UXLAYOTGAN O'YINCHI TEKSHIRUVI:
        # O'tgan/o'lgan o'yinchi har qanday vaqtda (kunduzi ham, tunda ham) guruhda yozsa — XABARI DARHOL O'CHIRILADI!
        if is_player and (not is_alive or is_sleep):
            if bot_can_delete:
                await self._delete_quietly(message)
            return

        # 7) TUN FAZASI UCHUN CHEKLOV:
        # Tun payti:
        #   - Xabar boshiga '!' qo'yib yozilsa -> xabar O'CHIRILMAYDI (guruhda saqlanib qoladi)
        #   - '/' bilan boshlansa -> slash buyruq o'chiriladi va bajariladi
        #   - '!' qo'yilmasdan yozilsa -> xabar O'CHIRILADI
        if is_game_active and phase_key == "night":
            if msg_text.startswith("!"):
                # Undov (!) bilan yozilgan xabar tunda o'chirilmaydi
                return await handler(message, data)
            elif msg_text.startswith("/"):
                # Slash (/) buyruq bo'lsa — buyruq xabari o'chiriladi va bajariladi
                if bot_can_delete:
                    await self._delete_quietly(message)
                return await handler(message, data)
            else:
                # Undov (!) qo'yilmagan oddiy xabar — tunda o'chiriladi
                if bot_can_delete:
                    await self._delete_quietly(message)
                return

        # 8) Slash buyruqlar (/start, /profile, /give, ! va hk)
        if msg_text and (msg_text.startswith("/") or msg_text.startswith("!")):
            if bot_can_delete:
                await self._delete_quietly(message)
            return await handler(message, data)

        # 9) Superadmin oshkora ruxsati (o'yinda faol o'yinchi bo'lmasa)
        is_superadmin = message.from_user and (message.from_user.id in set(ADMINS))
        if is_superadmin:
            return await handler(message, data)

        # O‘yin bo‘lmasa — oddiy xabarlarga ruxsat
        if not is_game_active and not game:
            return await handler(message, data)

        # 10) Guruh ruxsatlariga mos ravishda kunduzgi yozish tekshiruvi
        if phase_key in ("day", "afternoon", "morning", "day_actions") and group_perm:
            day_mode = getattr(group_perm, "day", "all")
            allowed = self._who_can_write(day_mode, is_player=is_player, is_alive=is_alive)
            if not allowed:
                if bot_can_delete:
                    await self._delete_quietly(message)
                return

        return await handler(message, data)
