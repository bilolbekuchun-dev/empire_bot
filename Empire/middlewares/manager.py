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
        # ChatMemberStatus (str, Enum) bo'lgani uchun str(...) uning nomini
        # ("ChatMemberStatus.ADMINISTRATOR") qaytaradi, qiymatini emas — shu sabab
        # to'g'ridan-to'g'ri .value (yoki oddiy string) bilan solishtiramiz.
        sv = status_value.value if isinstance(status_value, ChatMemberStatus) else str(status_value)
        sv = sv.lower()
        # 'creator' (eski), 'owner' (yangi), 'administrator' — hammasini qo‘llab
        return sv in {ChatMemberStatus.CREATOR.value, ChatMemberStatus.ADMINISTRATOR.value}

    @staticmethod
    def _sanitize_display_name(name: str) -> str:
        """
        Ba'zi foydalanuvchilar ismini "zalgo" uslubida — ko'plab birikuvchi
        (combining) belgilar bilan — yozadi. Bunday ismni <a href=...>NAME</a>
        HTML mention ichiga qo'yilganda Telegram ba'zan "ENTITY_TEXT_INVALID"
        xatosi bilan BUTUN xabarni rad etadi (tungi o'yinchilar ro'yxati,
        "kimga ovoz berasiz" kabi xabarlar shu sabab yuborilmay qoladi).
        Shu sabab combining belgilarni olib tashlaymiz.
        """
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
        """
        Bot guruhda bormi / adminmi va xabar o‘chirish ruxsati bormi?
        (is_admin, can_delete)
        `force=True` — keshni chetlab, Telegram'dan darhol qayta so'raydi
        (masalan, bot hozirgina admin qilingan bo'lishi mumkin bo'lgan holatda).
        """
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
            # Vaqtinchalik xato (tarmoq, rate-limit) — "admin emas" deb keshlab guruhni bloklamaymiz
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
        """
        Chat nomi DB bilan sinxronlash (API chaqiruvlarsiz).
        """
        chat, _ = await Chat.get_or_create(
            chat_id=message.chat.id,
            defaults={"title": message.chat.title, "type": str(message.chat.type)},
        )

        updated = False
        # Title o‘zgargan bo‘lsa yangilaymiz
        if message.chat.title and message.chat.title != chat.title:
            chat.title = message.chat.title
            updated = True

        # Username orqali invite link aniqlash
        if message.chat.username:
            new_link = f"https://t.me/{message.chat.username}"
            if new_link != chat.invite_link:
                chat.invite_link = new_link
                updated = True

        if updated:
            await chat.save()

    async def _sync_user_db_or_blocked(self, message: types.Message) -> bool:
        """
        Userni DB bilan sinxronlash, bloklangan bo‘lsa True qaytaradi (ya'ni to‘xtash kerak).
        """
        if not message.from_user:
            # sender_chat orqali kelgan xabarlar (kanal nomidan), xavfsiz variant — to‘xtatamiz
            return True

        fu = message.from_user
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

        # Bloklanganmi?
        if await Blocked_user.filter(user=user).first():
            return True

        return False

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
        'member' → faqat o‘yinchilar (tirik/ölgan farqi yo‘q)
        'alive'  → faqat tirik o‘yinchilar
        boshqasi → ruxsat yo‘q
        """
        if not mode_value:
            # Sozlanmagan bo‘lsa, default ruxsat beramiz (bahsli, ammo amaliy)
            return True
        mode_value = mode_value.lower()
        if mode_value == "all":
            return True
        if mode_value == "member":
            return is_player
        if mode_value == "alive":
            return is_player and is_alive
        # 'ega' yoki noma'lum qiymatlar — ruxsat yo‘q (faqat admin '!' bo‘lishi mumkin)
        return False

    async def _phase_info(self, game: Game) -> tuple[Optional[str], bool]:
        """
        Joriy fazani aniqlash:
        - Agar night is_end=False bo‘lsa → 'night'
        - Agar day/afternoon is_end=False bo‘lsa → 'day' (yoki 'afternoon' ni ham 'day' deb olamiz)
        - Aks holda: game.phase stringidan qaytamiz (masalan, 'waiting' va h.k.)
        return: (phase_key, is_waiting)
        """
        night_phase = await GamePhase.filter(game=game, phase_type="night", is_end=False).first()
        if night_phase:
            return "night", False

        day_or_afternoon = await GamePhase.filter(
            game=game, phase_type__in=["day", "afternoon"], is_end=False
        ).first()
        if day_or_afternoon:
            # ichki farqlash kerak bo‘lsa day_or_afternoon.phase_type ni qaytaring
            return day_or_afternoon.phase_type, False

        # Hech biri ochiq emas — game.phase ga tayansak bo‘ladi
        is_waiting = getattr(game, "phase", "") == "waiting"
        phase_key = getattr(game, "phase", None)
        return phase_key, is_waiting

    # --------------- Asosiy chaqiruv ---------------

    async def __call__(self, handler, event: types.Message, data: dict) -> Any:
        # Faqat Message bilan ishlaymiz
        if not isinstance(event, types.Message):
            return await handler(event, data)

        message = event
        
        # Xizmat xabarlarini o'tkazib yuborish (qotib qolish va mute qilishni oldini olish)
        if getattr(message, "new_chat_members", None) or getattr(message, "left_chat_member", None) or getattr(message, "new_chat_title", None):
            return await handler(event, data)

        # Private chat — bu middleware cheklamaydi
        if message.chat.type == ChatType.PRIVATE:
            return await handler(event, data)

        # Guruh/kanal bo‘lmasa ham ishlatmaslik
        if not self._is_group(message):
            return await handler(event, data)

        # 1) Bot adminligi va delete ruxsatlari
        bot_is_admin, bot_can_delete = await self._bot_admin_and_can_delete(message)
        if not bot_is_admin:
            # Kesh eskirgan bo'lishi mumkin (bot hozirgina admin qilingan) — xabar ko'rsatishdan
            # oldin Telegram'dan darhol qayta tekshiramiz, shunda yolg'on ogohlantirish chiqmaydi.
            bot_is_admin, bot_can_delete = await self._bot_admin_and_can_delete(message, force=True)
        if not bot_is_admin:
            # Foydalanuvchini ogohlantiramiz (bir marta bo‘lishi mumkin, spamlab yubormaslik uchun logger)
            try:
                await message.answer(
                    "<b>❗️ Bot guruhda admin emas! Bot muammosiz ishlashi uchun botni guruhga admin qiling "
                    "va xabarlarni o‘chirish ruxsatini bering.</b>",
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

        # 3) Userni DB bilan sinxronlash; bloklangan bo‘lsa — to‘xtaymiz
        try:
            if await self._sync_user_db_or_blocked(message):
                # bloklangan user — xabarni ham o‘chirib yuboramiz
                if bot_can_delete:
                    await self._delete_quietly(message)
                return
        except Exception as e:
            logger.warning("User sync failed: %r", e)
            # xatoga qaramay davom etamiz

        # 4) Slash komandalar — o‘chiramiz va to‘g‘ridan-to‘g‘ri handlerlarga uzatamiz
        if message.text and message.text.startswith("/"):
            if bot_can_delete:
                await self._delete_quietly(message)
            return await handler(message, data)

        # 5) Superadmin aniqlash
        is_superadmin = message.from_user and (message.from_user.id in set(ADMINS))

        # 6) Guruh yozish sozlamalari va aktiv o‘yin
        group_perm: Optional[WriteGroupPermis] = await WriteGroupPermis.filter(
            chat_id=message.chat.id
        ).first()

        game: Optional[Game] = await Game.filter(
            chat__chat_id=message.chat.id, is_active=True
        ).first()

        # O‘yin bo‘lmasa — hech qanday cheklov yo‘q
        if not game:
            return await handler(message, data)
        if is_superadmin:
            # Superadminlarga cheklanmagan ruxsat (loyihangiz siyosatiga mos)
            return await handler(message, data)
        # 7) Joriy fazani olish
        phase_key, is_waiting = await self._phase_info(game)  # phase_key: 'night' / 'day' / 'afternoon' / ...
        # group_perm.night == "all" bo‘lsa — tunda hamma yozishi mumkin (eng keng ruxsat)
        if phase_key == "night" and group_perm and getattr(group_perm, "night", None) == "all":
            return await handler(message, data)

        # 8) Adminlar uchun "!" komandasi — faza va sozlamaga qarab shartli ruxsat
        if message.text and message.text.startswith("!"):
            is_admin = False
            if message.from_user:
                try:
                    m = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
                    is_admin = self._is_admin_status(getattr(m, "status", ""))
                except Exception:
                    is_admin = False
            
            if is_admin and self._admin_command_allowed(phase_key, group_perm):
                return await handler(message, data)
            # Ruxsat berilmagan "!" — o‘chirib tashlaymiz
            if bot_can_delete:
                await self._delete_quietly(message)
            elif self.warn_user_if_cant_delete:
                pass
            return
        

        # 9) O‘yinchi ma’lumotlari (rol/holat tekshiruvi uchun)
        player = None
        if message.from_user:
            player = await GamePlayer.filter(
                game=game, user__user_id=message.from_user.id
            ).first()

        is_player = bool(player)
        is_alive = bool(player and player.is_alive)
        is_sleep = bool(player and getattr(player, "is_sleep", False))

        # 10) Fazaga qarab yozish ruxsati
        if phase_key == "night" and group_perm:
            allowed = self._who_can_write(group_perm.night, is_player=is_player, is_alive=is_alive)
            if not allowed:
                if bot_can_delete:
                    await self._delete_quietly(message)
                elif self.warn_user_if_cant_delete:
                    pass
                return

        elif phase_key in ("day", "afternoon") and group_perm:
            allowed = self._who_can_write(group_perm.day, is_player=is_player, is_alive=is_alive)
            if not allowed:
                if bot_can_delete:
                    await self._delete_quietly(message)
                elif self.warn_user_if_cant_delete:
                    pass
                return

        # 11) Kutishdan boshqa fazalarda: o‘lik yoki uxlayotgan o‘yinchi yozsa — taqiqlash
        if not is_waiting and (not is_player or not is_alive or is_sleep):
            if bot_can_delete:
                await self._delete_quietly(message)
            elif self.warn_user_if_cant_delete:
                pass
            return

        # Hammasi joyida: handlerlarga uzatamiz
        return await handler(message, data)
