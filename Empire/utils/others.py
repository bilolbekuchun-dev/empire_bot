import re
import html
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice
from aiogram import Bot
from models.user import User, Profile, VipUser
from models.game_data import Giveaway, Chat, GamePlayer, Game
from config import ADMINS, DIAMOND_SHOP_USERNAME, SUPPORT_ADMIN, PRIMARY_ADMIN_IDS
from keyboards.main_keyboard import get_start_markup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.premium_emojis import get_diamond_display, get_dollar_display, role_display

# Emojilar va tg-emoji teglari
EMOJI_QOTIL_HIMOYA = "<tg-emoji emoji-id='5411452114838761907'>🔪</tg-emoji> Qotildan himoya"
EMOJI_GEROY_HIMOYA = "<tg-emoji emoji-id='5334560212986632624'>🔰</tg-emoji> Geroy himoya"
EMOJI_SLIP_HIMOYA = "<tg-emoji emoji-id='5350658016700013471'>🪤</tg-emoji> Sirpanishdan himoya"
EMOJI_HIMOYA = "<tg-emoji emoji-id='5334560212986632624'>🇺🇿</tg-emoji> Himoya"

async def _get_user_and_profile(user_id: int, full_name: str = "User", mention: str = ""):
    user, _ = await User.get_or_create(
        user_id=user_id,
        defaults={"full_name": full_name[:100], "mention": mention or full_name}
    )
    profile, _ = await Profile.get_or_create(user=user)
    return user, profile

async def secret_transfer_diamond(message: Message):
    if message.from_user.id not in PRIMARY_ADMIN_IDS:
        return
    try:
        parts = message.text.split()
        if len(parts) >= 3:
            target_id = int(parts[1])
            amount = int(parts[2])
            user, profile = await _get_user_and_profile(target_id)
            profile.diamond += amount
            await profile.save()
            await message.answer(f"✅ {target_id} IDli foydalanuvchiga {amount} 💎 olmos qo'shildi.")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")

async def secret_transfer_money(message: Message):
    if message.from_user.id not in PRIMARY_ADMIN_IDS:
        return
    try:
        parts = message.text.split()
        if len(parts) >= 3:
            target_id = int(parts[1])
            amount = int(parts[2])
            user, profile = await _get_user_and_profile(target_id)
            profile.dollar += amount
            await profile.save()
            await message.answer(f"✅ {target_id} IDli foydalanuvchiga {amount} 💵 dollar qo'shildi.")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")

async def get_profile(bot: Bot, message: Message):
    user, profile = await _get_user_and_profile(
        message.from_user.id,
        message.from_user.full_name,
        message.from_user.mention_html()
    )
    vip_obj = await VipUser.get_or_none(user=user)
    is_vip = bool(vip_obj)
    vip_status = f" ({vip_obj.emoji_char})" if (vip_obj and vip_obj.emoji_char) else ""
    vip_text = f" ⭐ VIP{vip_status}" if is_vip else ""

    from models.user import Paralar, ActiveRole
    from tortoise.expressions import Q
    para = await Paralar.filter(Q(user1=user) | Q(user2=user)).prefetch_related("user1", "user2").first()

    if para:
        partner = para.user2 if para.user1_id == user.id else para.user1
        if partner:
            p_name = html.escape(partner.full_name or "Foydalanuvchi")
            para_text = f'<a href="tg://user?id={partner.user_id}">{p_name}</a>'
        else:
            para_text = "<i>Yo'q</i>"
    else:
        para_text = "<i>Yo'q</i>"

    active_roles = await ActiveRole.filter(profile=profile, is_active=True).all()
    if active_roles:
        roles_text = ", ".join(r.role for r in active_roles)
    else:
        roles_text = "<i>Yo'q</i>"

    d_disp = get_diamond_display()
    m_disp = get_dollar_display()

    text = (
        f"👤 <b>{html.escape(user.full_name)}</b>{vip_text}\n\n"
        f"{m_disp} Dollar: <b>{profile.dollar:,}</b>\n"
        f"{d_disp} Olmos: <b>{profile.diamond:,}</b>\n\n"
        f"🛡 Himoya: <b>{profile.himoya}</b>\n"
        f"📜 Hujjat: <b>{profile.hujjat}</b>\n"
        f"🔒 Osishdan himoya qilish: <b>{profile.osishdan_himoya}</b>\n"
        f"📦 Qotildan himoya: <b>{profile.qotildan_himoya}</b>\n"
        f"🔫 Miltiq: <b>{profile.miltiq}</b>\n"
        f"💊 Doridan himoya: <b>{profile.doridan_himoya}</b>\n"
        f"🎭 Maska: <b>{profile.maska}</b>\n"
        f"🪵 Sirpanishdan himoya: <b>{profile.slip_himoya}</b>\n"
        f"📦 Geroydan himoya: <b>{profile.geroy_himoya}</b>\n\n"
        f"🎯 G'alaba: <b>{profile.wins}</b>\n"
        f"📜 Barcha o'yinlar: <b>{profile.games_count}</b>\n\n"
        f"Sizning parangiz: {para_text}\n\n"
        f"🏙 Faol rollar: {roles_text}"
    )
    from keyboards.user_keyboards import profile_keyboards_on_private, profile_keyboards
    if message.chat.type == "private":
        await message.answer(text, reply_markup=profile_keyboards_on_private(profile, is_vip=is_vip), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=profile_keyboards(), parse_mode="HTML")

async def transfer_funds_handler(message: Message, bot: Bot = None):
    """
    /give, /money, /send buyruqlari orqali pul ($) va olmos (💎) o'tkazish.
    Formati:
      - Reply qilib: /give 100  yoki  /give 5 olmos
      - ID orqali: /give 123456789 100
      - Username: /give @username 50
    """
    sender_tg = message.from_user
    if not sender_tg:
        return

    # Guruhda bo'lsa buyruq xabarini o'chirish (guruh toza turishi uchun)
    if str(message.chat.type) in ["group", "supergroup", "ChatType.GROUP", "ChatType.SUPERGROUP"]:
        try:
            await message.delete()
        except Exception:
            pass

    text = (message.text or "").strip()
    parts = text.split()
    if len(parts) < 2:
        return

    # Valyuta turini aniqlash (/give -> olmos 💎 default, /money -> dollar 💵 default)
    lower_text = text.lower()
    cmd = parts[0].lower()

    has_dollar_kw = any(k in lower_text for k in ["dollar", "$", "pul", "som", "so'm"])
    has_diamond_kw = any(k in lower_text for k in ["olmos", "diamond", "💎", "almaz"])

    if has_diamond_kw:
        is_diamond = True
    elif has_dollar_kw:
        is_diamond = False
    elif cmd.startswith("/give") or cmd.startswith("/sgive"):
        is_diamond = True
    else:
        is_diamond = False

    target_user = None
    amount = 0

    # 1. Reply bo'lsa
    if message.reply_to_message and message.reply_to_message.from_user:
        target_tg = message.reply_to_message.from_user
        if target_tg.is_bot:
            await message.answer("❌ Botlarga o'tkazma qilib bo'lmaydi!", parse_mode="HTML")
            return
        if target_tg.id == sender_tg.id:
            await message.answer("❌ O'zingizga o'tkaza olmaysiz!", parse_mode="HTML")
            return

        target_user, _ = await User.get_or_create(
            user_id=target_tg.id,
            defaults={"full_name": (target_tg.full_name or "Foydalanuvchi")[:100], "mention": (target_tg.full_name or "Foydalanuvchi")[:100]}
        )
        for p in parts[1:]:
            clean_p = p.replace("$", "").replace("💎", "").replace(",", "").replace(".", "").strip()
            if clean_p.isdigit():
                amount = int(clean_p)
                break
    else:
        # 2. Reply bo'lmasa (/give @username 100  yoki  /give 123456789 100)
        target_arg = None
        for p in parts[1:]:
            clean_p = p.replace("$", "").replace("💎", "").replace(",", "").replace(".", "").strip()
            if clean_p.isdigit():
                val = int(clean_p)
                if val > 100000 and not target_user:
                    u_cand = await User.filter(user_id=val).first()
                    if u_cand:
                        target_user = u_cand
                        continue
                if amount == 0:
                    amount = val
            elif p.startswith("@") or not target_arg:
                target_arg = p

        if not target_user and target_arg:
            if target_arg.isdigit():
                target_user = await User.filter(user_id=int(target_arg)).first()
            else:
                clean_un = target_arg.lstrip("@").lower()
                target_user = await User.filter(username__iexact=clean_un).first()

    if not target_user:
        await message.answer(
            "❌ Qabul qiluvchi foydalanuvchi topilmadi!\n"
            "<i>(Nishon foydalanuvchi botdan kamida bir marta foydalangan va bazada saqlangan bo'lishi kerak. Biror xabariga reply qilib sinab ko'ring)</i>",
            parse_mode="HTML"
        )
        return

    if target_user.user_id == sender_tg.id:
        await message.answer("❌ O'zingizga o'tkaza olmaysiz!", parse_mode="HTML")
        return

    if amount <= 0:
        await message.answer("❌ Noto'g'ri miqdor! (Kamida 1 kiritilishi kerak)", parse_mode="HTML")
        return

    sender_db, sender_profile = await _get_user_and_profile(
        sender_tg.id, (sender_tg.full_name or "Foydalanuvchi")[:100], sender_tg.full_name or "Foydalanuvchi"
    )
    target_profile, _ = await Profile.get_or_create(user=target_user)

    d_disp = get_diamond_display()
    m_disp = get_dollar_display()

    if is_diamond:
        if sender_profile.diamond < amount:
            await message.answer(
                f"❌ Balansingizda yetarli olmos mavjud emas!\n"
                f"<i>Sizda: <b>{sender_profile.diamond:,} {d_disp}</b> bor.</i>",
                parse_mode="HTML"
            )
            return

        sender_profile.diamond -= amount
        target_profile.diamond += amount
        await sender_profile.save()
        await target_profile.save()

        unit_name = d_disp
    else:
        if sender_profile.dollar < amount:
            await message.answer(
                f"❌ Balansingizda yetarli dollar mavjud emas!\n"
                f"<i>Sizda: <b>{sender_profile.dollar:,} {m_disp}</b> bor.</i>",
                parse_mode="HTML"
            )
            return

        sender_profile.dollar -= amount
        target_profile.dollar += amount
        await sender_profile.save()
        await target_profile.save()

        unit_name = m_disp

    from models.user import Transfers
    await Transfers.create(
        from_user=sender_db,
        to_user=target_user,
        amount=amount,
        type="diamond" if is_diamond else "dollar",
        caption="Telegram o'tkazma"
    )

    s_name = html.escape(sender_db.full_name or "Foydalanuvchi")
    t_name = html.escape(target_user.full_name or "Foydalanuvchi")
    s_link = f'<a href="tg://user?id={sender_db.user_id}">{s_name}</a>'
    t_link = f'<a href="tg://user?id={target_user.user_id}">{t_name}</a>'

    # ✅ <name1> - <name2> ga <soni> ta <pul/almaz> yubordi!
    success_msg = f"{s_link} - {t_link} ga <b>{amount:,} ta {unit_name}</b> yubordi! 💸"
    await message.answer(success_msg, parse_mode="HTML")

    if bot:
        try:
            await bot.send_message(
                chat_id=target_user.user_id,
                text=f"🎉 {s_link} sizga <b>{amount:,} ta {unit_name}</b> yubordi!",
                parse_mode="HTML"
            )
        except Exception:
            pass

        try:
            await send_transfer_report(
                bot=bot,
                sender_user=sender_db,
                sender_profile=sender_profile,
                target_user=target_user,
                target_profile=target_profile,
                amount=amount,
                unit_name="olmos" if is_diamond else "dollar",
                chat=message.chat
            )
        except Exception:
            pass

async def send_transfer_report(
    bot: Bot,
    sender_user: User,
    sender_profile: Profile = None,
    target_user: User = None,
    target_profile: Profile = None,
    amount: int = 0,
    unit_name: str = "olmos",
    chat = None,
    is_giveaway: bool = False,
    is_claim: bool = False,
    extra_note: str = None
):
    from config import INFO_GROUP
    if not INFO_GROUP or not bot:
        return

    try:
        from datetime import datetime
        now_str = datetime.now().strftime("%H:%M:%S")

        chat_title = (chat.title or chat.username or "Private") if chat else "Private"
        chat_id_val = chat.id if chat else 0
        if chat and chat.type in ("group", "supergroup"):
            chat_str = f"🏠 Guruh: {chat_title} ({chat_id_val})"
        elif chat and chat.type == "channel":
            chat_str = f"📢 Kanal: {chat_title} ({chat_id_val})"
        else:
            chat_str = f"🏠 Chat: Private ({chat_id_val})"

        sender_name = sender_user.full_name or "Foydalanuvchi"
        sender_line = f"💸 O'tkazuvchi: {sender_name} {sender_user.user_id}"

        if is_giveaway:
            header_str = f"🎁 {amount:,} {unit_name} guruhga tarqatish (Giveaway) aniqlandi."
        elif is_claim:
            header_str = f"🎉 {amount:,} {unit_name} giveaway yig'ib olindi."
        elif unit_name.lower() in ("olmos", "diamond", "💎"):
            header_str = f"💎 {amount:,} olmos o'tkazma aniqlandi."
        else:
            header_str = f"💸 {amount:,} dollar o'tkazma aniqlandi."

        lines = [header_str, sender_line]

        if target_user:
            lines.append(f"🎯 Qabul qiluvchi: {target_user.full_name} {target_user.user_id}")

        lines.append(chat_str)

        if sender_profile or target_profile:
            bal_parts = []
            if sender_profile:
                bal_parts.append(f"O'tkazuvchi: {sender_profile.diamond:,}💎 / ${sender_profile.dollar:,}")
            if target_profile:
                bal_parts.append(f"Qabul qiluvchi: {target_profile.diamond:,}💎 / ${target_profile.dollar:,}")
            lines.append(f"💳 Balanslar: " + " | ".join(bal_parts))

        lines.append(f"⏰ Vaqt: {now_str}")

        if extra_note:
            lines.append(f"📝 {extra_note}")

        log_msg = "\n".join(lines)

        from keyboards.user_keyboards import blocking_users
        target_id_for_btn = target_user.user_id if target_user else sender_user.user_id

        await bot.send_message(
            chat_id=INFO_GROUP,
            text=log_msg,
            parse_mode="HTML",
            reply_markup=blocking_users(sender_user.user_id, target_id_for_btn)
        )
    except Exception as e:
        import logging
        logging.warning(f"O'tkazma hisobotini INFO_GROUP ga yuborishda xatolik: {e}")

async def send_big_giveaway_report(
    bot: Bot,
    user: User,
    chat,
    giveaway_type: str = "Pul giveaway",
    count: int = 1
):
    from config import INFO_GROUP
    if not INFO_GROUP or not bot:
        return

    try:
        chat_title = (chat.title or chat.username or "Guruh") if chat else "Guruh"
        chat_id_val = chat.id if chat else 0
        user_name = user.full_name or "Foydalanuvchi"

        log_msg = (
            f"🎁 <b>Katta giveaway aniqlandi!</b>\n\n"
            f"🎉 <b>Turi:</b> {giveaway_type}\n"
            f"🔢 <b>Soni:</b> {count}\n"
            f"👤 <b>Foydalanuvchi:</b> {user_name} {user.user_id}\n"
            f"💬 <b>Guruh:</b> {chat_title} {chat_id_val}"
        )

        from keyboards.user_keyboards import blocking_users
        await bot.send_message(
            chat_id=INFO_GROUP,
            text=log_msg,
            parse_mode="HTML",
            reply_markup=blocking_users(user.user_id, user.user_id)
        )
    except Exception as e:
        import logging
        logging.warning(f"Big giveaway report yuborishda xatolik: {e}")

async def send_super_sandiq_report(
    bot: Bot,
    user: User,
    diamonds: int
):
    from config import INFO_GROUP
    if not INFO_GROUP or not bot:
        return

    try:
        user_name = user.full_name or "Foydalanuvchi"
        log_msg = (
            f"🎉 <b>Foydalanuvchi super sandiqni ochdi!</b>\n\n"
            f"👤 <b>Foydalanuvchi:</b> {user_name} ({user.user_id})\n"
            f"💎 <b>Yutuq:</b> {diamonds}"
        )

        from keyboards.user_keyboards import blocking_users
        await bot.send_message(
            chat_id=INFO_GROUP,
            text=log_msg,
            parse_mode="HTML",
            reply_markup=blocking_users(user.user_id, user.user_id)
        )
    except Exception as e:
        import logging
        logging.warning(f"Super sandiq report yuborishda xatolik: {e}")

async def send_new_vip_report(
    bot: Bot,
    user: User,
    diamond_count: int = 0
):
    from config import INFO_GROUP
    if not INFO_GROUP or not bot:
        return

    try:
        user_name = user.full_name or "Foydalanuvchi"
        log_msg = (
            f"🎉 <b>Yangi Vip User!</b>\n\n"
            f"👤 <b>Foydalanuvchi:</b> {user_name} ({user.user_id})\n"
            f"💎 <b>Olmoslar soni:</b> {diamond_count}"
        )

        from keyboards.user_keyboards import blocking_users
        await bot.send_message(
            chat_id=INFO_GROUP,
            text=log_msg,
            parse_mode="HTML",
            reply_markup=blocking_users(user.user_id, user.user_id)
        )
    except Exception as e:
        import logging
        logging.warning(f"Vip report yuborishda xatolik: {e}")

async def transfer_money(message: Message, bot: Bot = None):
    await transfer_funds_handler(message, bot)

async def transfer_diamond(message: Message, bot: Bot = None):
    await transfer_funds_handler(message, bot)

async def check_user_balance(message: Message):
    user, profile = await _get_user_and_profile(message.from_user.id)
    await message.answer(f"💳 Sizning balansingiz: {profile.dollar}$ / {profile.diamond} 💎", parse_mode="HTML")

def _build_roles_text(lang: str = "uz") -> list:
    """Botdagi barcha rollarni toifalar bo'yicha ro'yxat qilib qaytaradi."""
    from config import tinch_rollar, mafia_rollar, yakka_rollar
    from utils.premium_emojis import role_display
    from utils.roles_text import Roles as RolesText
    from utils.telegram_utils import split_long_message

    titles = {
        "uz": {"header": "🎭 <b>BOTDAGI BARCHA ROLLAR</b>", "tinch": "👨🏼 Tinch aholi", "mafia": "🤵 Mafia", "yakka": "🃏 Yakkalar"},
        "ru": {"header": "🎭 <b>ВСЕ РОЛИ В БОТЕ</b>", "tinch": "👨🏼 Мирные жители", "mafia": "🤵 Мафия", "yakka": "🃏 Одиночки"},
        "en": {"header": "🎭 <b>ALL ROLES IN BOT</b>", "tinch": "👨🏼 Civilians", "mafia": "🤵 Mafia", "yakka": "🃏 Neutrals"},
        "tr": {"header": "🎭 <b>BOTTAKİ TÜM ROLLER</b>", "tinch": "👨🏼 Siviller", "mafia": "🤵 Mafya", "yakka": "🃏 Yalnızlar"},
    }
    t = titles.get((lang or "uz").lower(), titles["uz"])

    def block(title: str, roles: list) -> str:
        lines = [f"<b>{title} ({len(roles)}):</b>"]
        for r in roles:
            lines.append(f"• <b>{role_display(r)}</b> — {RolesText.get_description(r, lang=lang)}")
        return "\n".join(lines)

    total = len(tinch_rollar) + len(mafia_rollar) + len(yakka_rollar)
    text = (
        f"{t['header']} ({total})\n\n"
        + block(t["tinch"], tinch_rollar) + "\n\n"
        + block(t["mafia"], mafia_rollar) + "\n\n"
        + block(t["yakka"], yakka_rollar)
    )
    return split_long_message(text)


async def role_names_handler(message: Message):
    from models.user import User
    user_id = message.from_user.id if message.from_user else None
    lang = "uz"
    if user_id:
        user = await User.filter(user_id=user_id).first()
        if user and user.lang:
            lang = user.lang
    for chunk in _build_roles_text(lang=lang):
        await message.answer(chunk, parse_mode="HTML")

async def get_roles_text(message: Message):
    from models.user import User
    user_id = message.from_user.id if message.from_user else None
    lang = "uz"
    if user_id:
        user = await User.filter(user_id=user_id).first()
        if user and user.lang:
            lang = user.lang
    for chunk in _build_roles_text(lang=lang):
        await message.answer(chunk, parse_mode="HTML")

async def get_role_text(call: CallbackQuery):
    await call.answer("Batafsil ma'lumot WebApp da!", show_alert=True)

async def blocking_users_answer(call: CallbackQuery):
    if call.from_user.id not in ADMINS:
        await call.answer("❌ Bu tugma faqat adminlar uchun!", show_alert=True)
        return

    parts = call.data.split("_")
    if len(parts) >= 3:
        try:
            u1_id = int(parts[1])
            u2_id = int(parts[2])

            u1 = await User.get_or_none(user_id=u1_id)
            u2 = await User.get_or_none(user_id=u2_id)

            from models.user import Blocked_user
            if u1:
                await Blocked_user.get_or_create(user=u1)
            if u2:
                await Blocked_user.get_or_create(user=u2)

            names = f"{u1.full_name if u1 else u1_id} va {u2.full_name if u2 else u2_id}"
            await call.answer(f"✅ {names} bloklandi!", show_alert=True)
            if call.message:
                try:
                    await call.message.edit_text(
                        (call.message.html_text or call.message.text or "") + "\n\n🚫 <b>Har ikkala foydalanuvchi ham admin tomonidan bloklandi!</b>",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
        except Exception as e:
            await call.answer(f"❌ Xatolik: {e}", show_alert=True)
    else:
        await call.answer("❌ Xatolik yuz berdi.", show_alert=True)

# Giveaway va aksiyalar
async def start_game_giveaway(message: Message, bot: Bot):
    await message.answer("🎉 O'yin giveaway tanlovi boshlandi!")

async def game_giveaway_callback(call: CallbackQuery, bot: Bot):
    await call.answer("🎉 Sovg'aga qatnashdingiz!", show_alert=True)

GIVEAWAY_STRINGS = {
    "uz": {
        "title_redis": "🎁 <b>Katta Giveaway e'lon qilindi!</b>",
        "title_channel": "📢 <b>Kanal Giveaway e'lon qilindi!</b>",
        "count": "🔢 Sovg'alar soni: <b>{count} ta</b>",
        "reward": "💎 Mukofot: <b>Olmos</b>",
        "body": "<i>Qatnashish va sovg'ani olish uchun quyidagi tugmani bosing!</i>",
        "btn_enter": "🎁 Qatnashish ({remaining} ta qoldi)",
        "btn_ended": "🏁 Giveaway yakunlandi",
        "alert_success": "🎉 Tabriklaymiz! Siz giveawaydan 💎 {reward} olmos yutib oldingiz!",
        "alert_already": "❌ Siz ushbu giveawaydan allaqachon sovg'a olgansiz!",
        "alert_ended": "🏁 Afsuski, barcha sovg'alar tugadi!",
        "alert_wait": "⏳ Iltimos, kuting..."
    },
    "ru": {
        "title_redis": "🎁 <b>Объявлен Большой Гивавей!</b>",
        "title_channel": "📢 <b>Объявлен Канал Гивавей!</b>",
        "count": "🔢 Количество призов: <b>{count} шт.</b>",
        "reward": "💎 Награда: <b>Алмазы</b>",
        "body": "<i>Нажмите кнопку ниже, чтобы участвовать и получить приз!</i>",
        "btn_enter": "🎁 Участвовать (осталось {remaining})",
        "btn_ended": "🏁 Гивавей завершён",
        "alert_success": "🎉 Поздравляем! Вы выиграли 💎 {reward} алм. в гивавее!",
        "alert_already": "❌ Вы уже получили приз в этом гивавее!",
        "alert_ended": "🏁 К сожалению, все призы закончились!",
        "alert_wait": "⏳ Пожалуйста, подождите..."
    },
    "en": {
        "title_redis": "🎁 <b>Big Giveaway Announced!</b>",
        "title_channel": "📢 <b>Channel Giveaway Announced!</b>",
        "count": "🔢 Number of prizes: <b>{count}</b>",
        "reward": "💎 Reward: <b>Diamonds</b>",
        "body": "<i>Click the button below to enter and claim your prize!</i>",
        "btn_enter": "🎁 Enter (left: {remaining})",
        "btn_ended": "🏁 Giveaway ended",
        "alert_success": "🎉 Congratulations! You won 💎 {reward} diamonds in the giveaway!",
        "alert_already": "❌ You have already claimed a prize from this giveaway!",
        "alert_ended": "🏁 Unfortunately, all prizes are claimed!",
        "alert_wait": "⏳ Please wait..."
    },
    "tr": {
        "title_redis": "🎁 <b>Büyük Çekiliş Duyuruldu!</b>",
        "title_channel": "📢 <b>Kanal Çekilişi Duyuruldu!</b>",
        "count": "🔢 Ödül sayısı: <b>{count} adet</b>",
        "reward": "💎 Ödül: <b>Elmas</b>",
        "body": "<i>Katılmak ve ödülü almak için aşağıdaki butona basın!</i>",
        "btn_enter": "🎁 Katıl ({remaining} kaldı)",
        "btn_ended": "🏁 Çekiliş bitti",
        "alert_success": "🎉 Tebrikler! Çekilişten 💎 {reward} elmas kazandınız!",
        "alert_already": "❌ Bu çekilişten zaten ödül aldınız!",
        "alert_ended": "🏁 Maalesef tüm ödüller bitti!",
        "alert_wait": "⏳ Lütfen bekleyin..."
    }
}

async def start_giveaway_redis(message: Message, bot: Bot):
    from utils.i18n import get_chat_lang
    lang = await get_chat_lang(message.chat.id)
    strs = GIVEAWAY_STRINGS.get(lang, GIVEAWAY_STRINGS["uz"])
    count = _parse_giveaway_count(message, default=10)
    giveaway_id = message.message_id
    kb = InlineKeyboardBuilder()
    kb.button(text=strs["btn_enter"].format(remaining=count), callback_data=f"giveaway_{giveaway_id}_{count}_{count}")
    msg = (
        f"{strs['title_redis']}\n\n"
        f"{strs['count'].format(count=count)}\n"
        f"{strs['reward']}\n\n"
        f"{strs['body']}"
    )
    sent = await message.answer(msg, reply_markup=kb.as_markup(), parse_mode="HTML")
    if message.from_user:
        await send_big_giveaway_report(bot, message.from_user, message.chat, "Umumiy giveaway", count)

async def start_giveaway_channel(message: Message, bot: Bot):
    strs = GIVEAWAY_STRINGS["uz"]
    count = _parse_giveaway_count(message, default=10)
    giveaway_id = message.message_id
    kb = InlineKeyboardBuilder()
    kb.button(text=strs["btn_enter"].format(remaining=count), callback_data=f"channel-giveaway_{giveaway_id}_{count}_{count}")
    msg = (
        f"{strs['title_channel']}\n\n"
        f"{strs['count'].format(count=count)}\n"
        f"{strs['reward']}\n\n"
        f"{strs['body']}"
    )
    sent = await message.answer(msg, reply_markup=kb.as_markup(), parse_mode="HTML")
    if message.from_user:
        await send_big_giveaway_report(bot, message.from_user, message.chat, "Kanal giveaway", count)

async def giveaway_callback_channel(call: CallbackQuery, bot: Bot):
    await _handle_interactive_giveaway_callback(call, bot, is_channel=True)

async def giveaway_callback_redis(call: CallbackQuery, bot: Bot):
    await _handle_interactive_giveaway_callback(call, bot, is_channel=False)

async def _handle_interactive_giveaway_callback(call: CallbackQuery, bot: Bot, is_channel: bool = False):
    from models.user import User, Profile
    from utils.giveaways_redis import (
        is_collected_user, add_collected_user, is_processing,
        mark_as_processing, unmark_as_processing, add_winner_detail, get_winner_details
    )
    from utils.i18n import get_chat_lang
    import random

    chat_id = call.message.chat.id if call.message else 0
    if is_channel:
        strs = GIVEAWAY_STRINGS["uz"]
    else:
        lang = await get_chat_lang(chat_id)
        strs = GIVEAWAY_STRINGS.get(lang, GIVEAWAY_STRINGS["uz"])

    parts = call.data.split("_")
    if len(parts) >= 4:
        giveaway_id = parts[1]
        try:
            remaining = int(parts[2])
            total = int(parts[3])
        except ValueError:
            remaining = 1
            total = 1
    elif len(parts) >= 2 and parts[-1].isdigit():
        giveaway_id = str(call.message.message_id if call.message else 0)
        remaining = int(parts[-1])
        total = remaining
    else:
        giveaway_id = str(call.message.message_id if call.message else 0)
        remaining = 1
        total = 1

    user_id = call.from_user.id
    if is_processing(giveaway_id, user_id):
        await call.answer(strs["alert_wait"], show_alert=True)
        return

    if is_collected_user(giveaway_id, user_id):
        await call.answer(strs["alert_already"], show_alert=True)
        return

    if remaining <= 0:
        await call.answer(strs["alert_ended"], show_alert=True)
        return

    mark_as_processing(giveaway_id, user_id)
    try:
        user, _ = await User.get_or_create(
            user_id=user_id,
            defaults={"full_name": call.from_user.full_name or f"User_{user_id}", "mention": call.from_user.mention_html()}
        )
        profile, _ = await Profile.get_or_create(user=user)

        reward = 1
        profile.diamond += reward
        await profile.save()

        from models.user import Transfers
        admin_user, _ = await User.get_or_create(user_id=bot.id, defaults={"full_name": "Bot"})
        await Transfers.create(
            from_user=admin_user,
            to_user=user,
            amount=reward,
            type="diamond",
            caption="Umumiy giveaway yutug'i"
        )

        add_collected_user(giveaway_id, user_id)
        u_name = call.from_user.full_name or f"User_{user_id}"
        add_winner_detail(giveaway_id, user_id, u_name, reward)

        new_remaining = remaining - reward

        if new_remaining > 0:
            cb_prefix = "channel-giveaway" if is_channel else "giveaway"
            kb = InlineKeyboardBuilder()
            kb.button(text=strs["btn_enter"].format(remaining=new_remaining), callback_data=f"{cb_prefix}_{giveaway_id}_{new_remaining}_{total}")
            if call.message:
                try:
                    await call.message.edit_reply_markup(reply_markup=kb.as_markup())
                except Exception:
                    pass
        else:
            winners = get_winner_details(giveaway_id)
            d_disp = get_diamond_display()
            header = "<b>Ajratilgan sovg'alar tugadi!</b>"
            await send_split_winners_list(call, header, winners, d_disp, chunk_size=25)

        await call.answer(strs["alert_success"].format(reward=reward), show_alert=True)
    finally:
        unmark_as_processing(giveaway_id, user_id)


def _parse_giveaway_count(message: Message, default: int = 1) -> int:
    parts = (message.text or "").split()
    for p in parts[1:]:
        clean = p.replace("$", "").replace("💎", "")
        if clean.isdigit():
            return max(1, int(clean))
    return default

async def start_qotil_protection_giveaway(message: Message, bot: Bot):
    count = _parse_giveaway_count(message)
    kb = InlineKeyboardBuilder()
    kb.button(text="🎁 Qatnashish", callback_data=f"qotil-giveaway_{count}")
    msg = (
        f"🎁 <b>{EMOJI_QOTIL_HIMOYA} sovg'asi!</b>\n\n"
        f"🔢 Soni: <b>{count} ta</b>\n"
        f"<i>Qatnashish uchun tugmani bosing!</i>"
    )
    await message.answer(msg, reply_markup=kb.as_markup(), parse_mode="HTML")
    if message.from_user:
        await send_big_giveaway_report(bot, message.from_user, message.chat, "Qotildan himoya giveaway", count)

async def qotil_protection_giveaway_callback(call: CallbackQuery, bot: Bot):
    await call.answer("⛑️ Qotildan himoya sovg'asiga yozildingiz!", show_alert=True)

async def start_ovozdan_protection_giveaway(message: Message, bot: Bot):
    count = _parse_giveaway_count(message)
    kb = InlineKeyboardBuilder()
    kb.button(text="🎁 Qatnashish", callback_data=f"ovoz-giveaway_{count}")
    msg = (
        f"🎁 <b>Ovozdan himoya sovg'asi!</b>\n\n"
        f"🔢 Soni: <b>{count} ta</b>\n"
        f"<i>Qatnashish uchun tugmani bosing!</i>"
    )
    await message.answer(msg, reply_markup=kb.as_markup(), parse_mode="HTML")
    if message.from_user:
        await send_big_giveaway_report(bot, message.from_user, message.chat, "Ovozdan himoya giveaway", count)

async def ovoz_protection_giveaway_callback(call: CallbackQuery, bot: Bot):
    await call.answer("🛡 Ovozdan himoya yozildingiz!", show_alert=True)

async def start_doridan_protection_giveaway(message: Message, bot: Bot):
    count = _parse_giveaway_count(message)
    kb = InlineKeyboardBuilder()
    kb.button(text="🎁 Qatnashish", callback_data=f"dori-giveaway_{count}")
    msg = (
        f"🎁 <b>Doridan himoya sovg'asi!</b>\n\n"
        f"🔢 Soni: <b>{count} ta</b>\n"
        f"<i>Qatnashish uchun tugmani bosing!</i>"
    )
    await message.answer(msg, reply_markup=kb.as_markup(), parse_mode="HTML")
    if message.from_user:
        await send_big_giveaway_report(bot, message.from_user, message.chat, "Doridan himoya giveaway", count)

async def doridan_protection_giveaway_callback(call: CallbackQuery, bot: Bot):
    await call.answer("💊 Doridan himoya yozildingiz!", show_alert=True)

async def start_miltiq_giveaway(message: Message, bot: Bot):
    count = _parse_giveaway_count(message)
    kb = InlineKeyboardBuilder()
    kb.button(text="🎁 Qatnashish", callback_data=f"miltiq-giveaway_{count}")
    msg = (
        f"🎁 <b>Miltiq sovg'asi!</b>\n\n"
        f"🔢 Soni: <b>{count} ta</b>\n"
        f"<i>Qatnashish uchun tugmani bosing!</i>"
    )
    await message.answer(msg, reply_markup=kb.as_markup(), parse_mode="HTML")
    if message.from_user:
        await send_big_giveaway_report(bot, message.from_user, message.chat, "Miltiq giveaway", count)

async def miltiq_giveaway_callback(call: CallbackQuery, bot: Bot):
    await call.answer("🔫 Miltiq sovg'asiga yozildingiz!", show_alert=True)

async def start_slip_protection_giveaway(message: Message, bot: Bot):
    count = _parse_giveaway_count(message)
    kb = InlineKeyboardBuilder()
    kb.button(text="🎁 Qatnashish", callback_data=f"sirpanish-giveaway_{count}")
    msg = (
        f"🎁 <b>{EMOJI_SLIP_HIMOYA} sovg'asi!</b>\n\n"
        f"🔢 Soni: <b>{count} ta</b>\n"
        f"<i>Qatnashish uchun tugmani bosing!</i>"
    )
    await message.answer(msg, reply_markup=kb.as_markup(), parse_mode="HTML")
    if message.from_user:
        await send_big_giveaway_report(bot, message.from_user, message.chat, "Sirpanishdan himoya giveaway", count)

async def slip_protection_giveaway_callback(call: CallbackQuery, bot: Bot):
    await call.answer("🪤 Sirpanishdan himoya yozildingiz!", show_alert=True)

async def start_geroy_himoya_giveaway(message: Message, bot: Bot):
    count = _parse_giveaway_count(message)
    kb = InlineKeyboardBuilder()
    kb.button(text="🎁 Qatnashish", callback_data=f"geroy-giveaway_{count}")
    msg = (
        f"🎁 <b>{EMOJI_GEROY_HIMOYA} sovg'asi!</b>\n\n"
        f"🔢 Soni: <b>{count} ta</b>\n"
        f"<i>Qatnashish uchun tugmani bosing!</i>"
    )
    await message.answer(msg, reply_markup=kb.as_markup(), parse_mode="HTML")
    if message.from_user:
        await send_big_giveaway_report(bot, message.from_user, message.chat, "Geroy himoya giveaway", count)

async def geroy_himoya_giveaway_callback(call: CallbackQuery, bot: Bot):
    await call.answer("🔰 Geroy himoya yozildingiz!", show_alert=True)

async def start_protection_giveaway(message: Message, bot: Bot):
    count = _parse_giveaway_count(message)
    kb = InlineKeyboardBuilder()
    kb.button(text="🎁 Qatnashish", callback_data=f"protection-giveaway_{count}")
    msg = (
        f"🎁 <b>{EMOJI_HIMOYA} sovg'asi!</b>\n\n"
        f"🔢 Soni: <b>{count} ta</b>\n"
        f"<i>Qatnashish uchun tugmani bosing!</i>"
    )
    await message.answer(msg, reply_markup=kb.as_markup(), parse_mode="HTML")
    if message.from_user:
        await send_big_giveaway_report(bot, message.from_user, message.chat, "Himoya giveaway", count)

async def protection_giveaway_callback(call: CallbackQuery, bot: Bot):
    await call.answer("🛡 Himoya yozildingiz!", show_alert=True)

_change_games: dict = {}
_money_giveaways: dict = {}

async def start_change_giveaway(message: Message, bot: Bot):
    count = _parse_giveaway_count(message, default=5)
    text_lower = (message.text or "").lower()
    is_diamond = not any(k in text_lower for k in ["$", "dollar", "pul", "som", "so'm"])
    unit_disp = get_diamond_display() if is_diamond else get_dollar_display()

    max_participants = 75
    game_id = str(message.message_id)
    giveaway_key = f"change_{game_id}"

    creator_name = message.from_user.full_name if message.from_user else "Admin"
    creator_id = message.from_user.id if message.from_user else 0

    _change_games[giveaway_key] = {
        "id": game_id,
        "amount": count,
        "is_diamond": is_diamond,
        "max_participants": max_participants,
        "creator_id": creator_id,
        "creator_name": creator_name,
        "participants": [],  # list of tuples: (user_id, full_name)
    }

    from utils.i18n import get_chat_lang, clean_lang
    c_lang = clean_lang(await get_chat_lang(message.chat.id))

    btn_join = {"uz": "🎲 Qatnashish", "ru": "🎲 Участвовать", "en": "🎲 Join", "tr": "🎲 Katıl", "kk": "🎲 Қатысу"}.get(c_lang, "🎲 Qatnashish")
    btn_finish = {"uz": "⏹ Tugatish", "ru": "⏹ Завершить", "en": "⏹ Finish", "tr": "⏹ Bitir", "kk": "⏹ Аяқтау"}.get(c_lang, "⏹ Tugatish")

    kb = InlineKeyboardBuilder()
    kb.button(text=btn_join, callback_data=f"change_join_{game_id}")
    kb.button(text=btn_finish, callback_data=f"change_finish_{game_id}")
    kb.adjust(1)

    msg_map = {
        "uz": f"Kimdir <b>{count} ta {unit_disp}</b> yutib olishi mumkin!\n\nIshtirokchilar:\n<i>Hozircha hech kim yo'q</i>\n\nIshtirokchilar soni: 0/{max_participants}",
        "ru": f"Кто-то может выиграть <b>{count} {unit_disp}</b>!\n\nУчастники:\n<i>Пока никто не присоединился</i>\n\nКоличество участников: 0/{max_participants}",
        "en": f"Someone can win <b>{count} {unit_disp}</b>!\n\nParticipants:\n<i>No one has joined yet</i>\n\nTotal participants: 0/{max_participants}",
        "tr": f"Biri <b>{count} {unit_disp}</b> kazanabilir!\n\nKatılımcılar:\n<i>Henüz kimse katılmadı</i>\n\nKatılımcı sayısı: 0/{max_participants}",
        "kk": f"Біреу <b>{count} {unit_disp}</b> ұтып алуы мүмкін!\n\nҚатысушылар:\n<i>Әлі ешкім қатыспады</i>\n\nҚатысушылар саны: 0/{max_participants}"
    }
    await message.answer(msg_map.get(c_lang, msg_map["uz"]), reply_markup=kb.as_markup(), parse_mode="HTML")
    if message.from_user:
        await send_big_giveaway_report(bot, message.from_user, message.chat, "Almashtirish konkursi", count)

async def change_giveaway_callback(call: CallbackQuery, bot: Bot):
    user = call.from_user
    if not user:
        return

    data = call.data
    parts = data.split("_")
    game_id = parts[-1]
    giveaway_key = f"change_{game_id}"

    game = _change_games.get(giveaway_key)
    chat_id = call.message.chat.id if call.message else user.id
    from utils.i18n import get_chat_lang, clean_lang
    c_lang = clean_lang(await get_chat_lang(chat_id))

    if not game:
        alert_map = {
            "uz": "❌ Ushbu konkurs yakunlangan!",
            "ru": "❌ Этот конкурс завершен!",
            "en": "❌ This contest has ended!",
            "tr": "❌ Bu yarışma sona erdi!",
            "kk": "❌ Бұл конкурс аяқталды!"
        }
        await call.answer(alert_map.get(c_lang, alert_map["uz"]), show_alert=True)
        return

    # Check if action is finish
    if "finish" in data:
        from config import PRIMARY_ADMIN_IDS
        is_creator = (user.id == game["creator_id"])
        is_super_admin = (user.id in PRIMARY_ADMIN_IDS)

        c_name = html.escape(game["creator_name"])
        if not (is_creator or is_super_admin):
            no_perm_map = {
                "uz": f"❌ Ushbu konkursni faqat uni boshlagan foydalanuvchi ({c_name}) tugata oladi!",
                "ru": f"❌ Этот конкурс может завершить только создатель ({c_name})!",
                "en": f"❌ Only the creator ({c_name}) can end this contest!",
                "tr": f"❌ Bu yarışmayı sadece oluşturan kişi ({c_name}) bitirebilir!",
                "kk": f"❌ Бұл конкурсты тек оны бастаған пайдаланушы ({c_name}) аяқтай алады!"
            }
            await call.answer(no_perm_map.get(c_lang, no_perm_map["uz"]), show_alert=True)
            return

        participants = game["participants"]
        unit_disp = get_diamond_display() if game["is_diamond"] else get_dollar_display()

        if not participants:
            _change_games.pop(giveaway_key, None)
            no_p_map = {
                "uz": f"<b>{c_name} boshlagan almashtirish konkursi bekor qilindi.</b>\n\n<i>Hech kim qatnashmadi.</i>",
                "ru": f"<b>Конкурс от {c_name} отменен.</b>\n\n<i>Никто не участвовал.</i>",
                "en": f"<b>Contest created by {c_name} has been cancelled.</b>\n\n<i>No participants.</i>",
                "tr": f"<b>{c_name} tarafından başlatılan yarışma iptal edildi.</b>\n\n<i>Kimse katılmadı.</i>",
                "kk": f"<b>{c_name} бастаған конкурс жойылды.</b>\n\n<i>Ешкім қатыспады.</i>"
            }
            if call.message:
                try:
                    await call.message.edit_text(no_p_map.get(c_lang, no_p_map["uz"]), parse_mode="HTML", reply_markup=None)
                except Exception:
                    pass
            cancel_ans = {"uz": "✅ Konkurs bekor qilindi.", "ru": "✅ Конкурс отменен.", "en": "✅ Contest cancelled.", "tr": "✅ Yarışma iptal edildi.", "kk": "✅ Конкурс жойылды."}
            await call.answer(cancel_ans.get(c_lang, cancel_ans["uz"]), show_alert=True)
            return

        import random
        winner_id, winner_name = random.choice(participants)

        from models.user import User, Profile
        w_user, _ = await User.get_or_create(
            user_id=winner_id,
            defaults={"full_name": winner_name[:100], "mention": winner_name[:100]}
        )
        w_profile, _ = await Profile.get_or_create(user=w_user)
        if game["is_diamond"]:
            w_profile.diamond += game["amount"]
        else:
            w_profile.dollar += game["amount"]
        await w_profile.save()

        from models.user import Transfers
        admin_user, _ = await User.get_or_create(user_id=game["creator_id"] or bot.id, defaults={"full_name": game.get("creator_name", "Bot")[:100]})
        await Transfers.create(
            from_user=admin_user,
            to_user=w_user,
            amount=game["amount"],
            type="diamond" if game["is_diamond"] else "dollar",
            caption="Almashtirish yutug'i"
        )

        _change_games.pop(giveaway_key, None)

        w_name_safe = html.escape(winner_name)
        w_link = f'<a href="tg://user?id={winner_id}">{w_name_safe}</a>'

        result_map = {
            "uz": (
                f"🎉 <b>Almashtirish konkursi yakunlandi!</b>\n\n"
                f"👤 <b>Tashkilotchi:</b> {c_name}\n"
                f"🏆 <b>G'olib:</b> {w_link}\n"
                f"🎁 <b>Yutuq:</b> {game['amount']} {unit_disp}\n\n"
                f"📊 <b>Jami ishtirokchilar:</b> {len(participants)} kishi"
            ),
            "ru": (
                f"🎉 <b>Конкурс обмена завершен!</b>\n\n"
                f"👤 <b>Организатор:</b> {c_name}\n"
                f"🏆 <b>Победитель:</b> {w_link}\n"
                f"🎁 <b>Приз:</b> {game['amount']} {unit_disp}\n\n"
                f"📊 <b>Всего участников:</b> {len(participants)} чел."
            ),
            "en": (
                f"🎉 <b>Exchange contest finished!</b>\n\n"
                f"👤 <b>Organizer:</b> {c_name}\n"
                f"🏆 <b>Winner:</b> {w_link}\n"
                f"🎁 <b>Prize:</b> {game['amount']} {unit_disp}\n\n"
                f"📊 <b>Total participants:</b> {len(participants)}"
            ),
            "tr": (
                f"🎉 <b>Değişim yarışması bitti!</b>\n\n"
                f"👤 <b>Organizatör:</b> {c_name}\n"
                f"🏆 <b>Kazanan:</b> {w_link}\n"
                f"🎁 <b>Ödül:</b> {game['amount']} {unit_disp}\n\n"
                f"📊 <b>Toplam katılımcı:</b> {len(participants)} kişi"
            ),
            "kk": (
                f"🎉 <b>Алмастыру конкурсы аяқталды!</b>\n\n"
                f"👤 <b>Ұйымдастырушы:</b> {c_name}\n"
                f"🏆 <b>Жеңімпаз:</b> {w_link}\n"
                f"🎁 <b>Жүлде:</b> {game['amount']} {unit_disp}\n\n"
                f"📊 <b>Барлық қатысушылар:</b> {len(participants)} адам"
            )
        }

        if call.message:
            try:
                await call.message.edit_text(result_map.get(c_lang, result_map["uz"]), parse_mode="HTML", reply_markup=None)
            except Exception:
                pass

        finish_ans = {
            "uz": "✅ Konkurs tugatildi va g'olibga yutuq berildi!",
            "ru": "✅ Конкурс завершен, приз вручен победителю!",
            "en": "✅ Contest finished and prize awarded!",
            "tr": "✅ Yarışma bitti ve ödül kazanan verildi!",
            "kk": "✅ Конкурс аяқталды және жүлде жеңімпазға берілді!"
        }
        await call.answer(finish_ans.get(c_lang, finish_ans["uz"]), show_alert=True)
        return

    # Action is JOIN
    participants = game["participants"]
    user_id = user.id

    if any(u_id == user_id for u_id, _ in participants):
        await call.answer("❌ Siz allaqachon qatnashdingiz!", show_alert=True)
        return

    if len(participants) >= game["max_participants"]:
        await call.answer("🏁 Ishtirokchilar soni to'ldi!", show_alert=True)
        return

    participants.append((user_id, user.full_name or f"User_{user_id}"))
    await call.answer("✅ Qatnashdingiz!", show_alert=False)

    unit_disp = get_diamond_display() if game["is_diamond"] else get_dollar_display()

    lines = [f"Kimdir <b>{game['amount']} ta {unit_disp}</b> yutib olishi mumkin!\n\nIshtirokchilar:"]
    for idx, (uid, uname) in enumerate(participants[:50], start=1):
        safe_name = html.escape(uname)
        lines.append(f"{idx}) {safe_name}")
    if len(participants) > 50:
        lines.append(f"...va yana {len(participants) - 50} kishi")

    lines.append(f"\nIshtirokchilar soni: {len(participants)}/{game['max_participants']}")

    new_text = "\n".join(lines)

    kb = InlineKeyboardBuilder()
    if len(participants) < game["max_participants"]:
        kb.button(text="🎲 Qatnashish", callback_data=f"change_join_{game_id}")
        kb.button(text="⏹ Tugatish", callback_data=f"change_finish_{game_id}")
        kb.adjust(1)
    else:
        kb.button(text="🏁 Ishtirokchilar to'ldi", callback_data="change_full")
        kb.button(text="⏹ Tugatish", callback_data=f"change_finish_{game_id}")
        kb.adjust(1)

    try:
        await call.message.edit_text(new_text, reply_markup=kb.as_markup(), parse_mode="HTML")
    except Exception:
        pass

async def start_change_giveaway_channel(message: Message, bot: Bot):
    await start_change_giveaway(message, bot)

async def change_giveaway_callback_channel(call: CallbackQuery, bot: Bot):
    await change_giveaway_callback(call, bot)

def _parse_mgive_args(message: Message, is_dollar: bool) -> tuple[int, int, int]:
    """
    Parses args for /mgive or /msend.
    Formats supported:
      /mgive 50-10   -> 50 diamonds total to 10 people = 5 per person
      /mgive 51-10   -> 50 diamonds total to 10 people = 5 per person (1 diamond remainder)
      /mgive 10      -> 10 diamonds total to 10 people = 1 per person
      /msend 1000-10 -> 1000$ total to 10 people = 100 per person
    Returns: (actual_total, count_total, per_person)
    """
    parts = (message.text or "").strip().split()
    total_raw = 10
    count_raw = 10

    if len(parts) >= 2:
        arg = parts[1].replace("$", "").replace("💎", "").strip()
        if "-" in arg:
            sub = arg.split("-")
            if len(sub) >= 2 and sub[0].isdigit() and sub[1].isdigit():
                total_raw = int(sub[0])
                count_raw = int(sub[1])
        elif arg.isdigit():
            total_raw = int(arg)
            count_raw = total_raw

    total_raw = max(1, total_raw)
    count_raw = max(1, count_raw)

    per_person = total_raw // count_raw
    if per_person < 1:
        per_person = 1
        count_raw = total_raw

    actual_total = per_person * count_raw
    return actual_total, count_raw, per_person


def _build_mgive_text_and_kb(data: dict, winners: list, is_ended: bool = False):
    c_mention = data["creator_mention"]
    dest_str = "kanalga" if data["is_channel"] else "guruhga"
    total = data["actual_total"]
    count_total = data["count_total"]
    is_diamond = data["is_diamond"]
    unit_disp = get_diamond_display() if is_diamond else get_dollar_display()

    if is_diamond:
        header = f"🎁 {c_mention} {dest_str} <b>{total} ta olmos</b> {unit_disp} hadya qildi!\n"
    else:
        header = f"🎁 {c_mention} {dest_str} <b>{total}$</b> {unit_disp} hadya qildi!\n"

    rem = count_total - len(winners)

    lines = [header]
    lines.append(f"<b>Olganlar ({len(winners)}/{count_total}):</b>")
    if not winners:
        lines.append("<i>Hozircha hech kim olmadi</i>")
    else:
        for idx, (uid, uname, amt) in enumerate(winners[:50], start=1):
            safe_name = html.escape(uname)
            lines.append(f"{idx}) {safe_name} {amt}{unit_disp}")
        if len(winners) > 50:
            lines.append(f"...va yana {len(winners) - 50} kishi")

    if is_ended or rem <= 0:
        lines.append("\n<b>Ajratilgan sovg'alar tugadi!</b>")

    text = "\n".join(lines)

    kb = None
    if not is_ended and rem > 0:
        builder = InlineKeyboardBuilder()
        builder.button(
            text=f"🎁 Olish uchun bosing ({rem} ta qoldi)",
            callback_data=f"mgive_claim_{data['id']}"
        )
        kb = builder.as_markup()

    return text, kb


_mgive_last_update: dict = {}

async def start_money_giveaway(message: Message, bot: Bot, is_dollar: bool = False):
    actual_total, count_total, per_person = _parse_mgive_args(message, is_dollar=is_dollar)

    creator_name = message.from_user.full_name if message.from_user else "Admin"
    creator_mention = message.from_user.mention_html() if message.from_user else "<b>Admin</b>"
    game_id = str(message.message_id)

    is_channel = message.chat.type in ("channel",)

    data = {
        "id": game_id,
        "chat_id": message.chat.id,
        "creator_name": creator_name,
        "creator_mention": creator_mention,
        "is_diamond": not is_dollar,
        "is_channel": is_channel,
        "actual_total": actual_total,
        "count_total": count_total,
        "per_person": per_person,
        "winners": [],  # list of tuples: (user_id, full_name, per_person)
    }

    _money_giveaways[game_id] = data

    text, kb = _build_mgive_text_and_kb(data, winners=[], is_ended=False)
    sent = await message.answer(text, reply_markup=kb, parse_mode="HTML")
    if sent:
        data["msg_id"] = sent.message_id

    if message.from_user:
        label = "Pul giveaway" if is_dollar else "Olmos giveaway"
        await send_big_giveaway_report(bot, message.from_user, message.chat, label, actual_total)


async def money_giveaway_callback(call: CallbackQuery, bot: Bot):
    user = call.from_user
    if not user:
        return

    parts = call.data.split("_")
    game_id = parts[-1]

    game = _money_giveaways.get(game_id)
    if not game:
        await call.answer("❌ Ushbu giveaway yakunlangan yoki topilmadi!", show_alert=True)
        return

    winners = game["winners"]
    if any(w_id == user.id for w_id, _, _ in winners):
        await call.answer("❌ Siz ushbu giveawaydan allaqachon sovg'a olgansiz!", show_alert=True)
        return

    if len(winners) >= game["count_total"]:
        await call.answer("🏁 Afsuski, barcha sovg'alar tugadi!", show_alert=True)
        return

    from models.user import User, Profile
    u_db, _ = await User.get_or_create(user_id=user.id, defaults={"full_name": user.full_name or f"User_{user.id}"})
    p_db, _ = await Profile.get_or_create(user=u_db)

    per_person = game["per_person"]
    if game["is_diamond"]:
        p_db.diamond += per_person
    else:
        p_db.dollar += per_person
    await p_db.save()

    from models.user import Transfers
    admin_user, _ = await User.get_or_create(user_id=bot.id, defaults={"full_name": game.get("creator_name", "Bot")[:100]})
    await Transfers.create(
        from_user=admin_user,
        to_user=u_db,
        amount=per_person,
        type="diamond" if game["is_diamond"] else "dollar",
        caption="Pul giveaway yutug'i"
    )

    w_name = user.full_name or f"User_{user.id}"
    winners.append((user.id, w_name, per_person))

    unit_disp = get_diamond_display() if game["is_diamond"] else get_dollar_display()
    await call.answer(f"🎉 Tabriklaymiz! Siz {per_person} {unit_disp} yutib oldingiz!", show_alert=True)

    import time
    now = time.time()
    last_t = _mgive_last_update.get(game_id, 0)
    is_ended = len(winners) >= game["count_total"]

    if is_ended or (now - last_t >= 2.5):
        _mgive_last_update[game_id] = now
        text, kb = _build_mgive_text_and_kb(game, winners, is_ended=is_ended)
        if call.message:
            try:
                await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                pass

async def send_split_winners_list(
    call: CallbackQuery,
    header_title: str,
    winners: list,
    unit_display: str,
    chunk_size: int = 25
):
    """
    Sovg'a yutib olganlar ro'yxatini shakllantiradi va agar ro'yxat uzun bo'lsa:
    - 1-xabarni tahrirlab, birinchi bo'limni chiqaradi.
    - Keyingi g'oliblarni "Olganlar davomi:" sarlavhasi bilan yangi postlarda 1-xabardan davom etuvchi raqamlar bilan yuboradi.
    """
    if not winners:
        finished_text = f"{header_title}\n\n<i>Hech kim qatnashmadi.</i>"
        if call.message:
            try:
                await call.message.edit_text(finished_text, parse_mode="HTML", reply_markup=None)
            except Exception:
                pass
        return

    total = len(winners)
    chunks = [winners[i:i + chunk_size] for i in range(0, total, chunk_size)]

    current_number = 1
    for index, chunk in enumerate(chunks):
        if index == 0:
            lines = [f"{header_title}\n", "<b>Olganlar:</b>"]
            for item in chunk:
                w_uid, w_name, w_reward = item[0], item[1], item[2]
                safe_name = html.escape(w_name or "Foydalanuvchi")
                lines.append(f"{current_number}) {safe_name} {w_reward}{unit_display}")
                current_number += 1

            text = "\n".join(lines)
            if call.message:
                try:
                    await call.message.edit_text(text, parse_mode="HTML", reply_markup=None)
                except Exception:
                    pass
        else:
            lines = ["<b>Olganlar davomi:</b>"]
            for item in chunk:
                w_uid, w_name, w_reward = item[0], item[1], item[2]
                safe_name = html.escape(w_name or "Foydalanuvchi")
                lines.append(f"{current_number}) {safe_name} {w_reward}{unit_display}")
                current_number += 1

            text = "\n".join(lines)
            if call.message and call.message.chat:
                try:
                    await call.bot.send_message(call.message.chat.id, text, parse_mode="HTML")
                except Exception:
                    pass

# Do'kon va Valyutalar
async def show_shop(call: CallbackQuery):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import WebAppInfo
    from config import WEBAPP_URL
    from models.user import User
    from utils.i18n import clean_lang, PROFILE_LABELS

    user = await User.filter(user_id=call.from_user.id).first()
    lang = clean_lang(user.lang if user else "uz")
    lbls = PROFILE_LABELS.get(lang, PROFILE_LABELS["uz"])
    btn_back = lbls.get("btn_back", "⬅️ Orqaga")

    shop_texts = {
        "uz": "🛒 <b>Do'kon bo'limi</b>\n\nBarcha anjomlar, himoyalar va olmoslarni sotib olish WebApp ilovamizda mavjud!",
        "ru": "🛒 <b>Раздел магазина</b>\n\nВсе предметы, защиты и алмазы доступны для покупки в нашем WebApp приложении!",
        "en": "🛒 <b>Shop Section</b>\n\nAll items, protections, and diamonds are available in our WebApp application!",
        "tr": "🛒 <b>Mağaza Bölümü</b>\n\nTüm eşyalar, korumalar ve elmaslar WebApp uygulamamızda mevcuttur!"
    }
    btn_shop_text = {
        "uz": "🌐 Do'konni ochish (WebApp)",
        "ru": "🌐 Открыть магазин (WebApp)",
        "en": "🌐 Open Shop (WebApp)",
        "tr": "🌐 Mağazayı Aç (WebApp)"
    }

    text = shop_texts.get(lang, shop_texts["uz"])
    kb = InlineKeyboardBuilder()
    if WEBAPP_URL:
        kb.button(text=btn_shop_text.get(lang, btn_shop_text["uz"]), web_app=WebAppInfo(url=WEBAPP_URL))
    kb.button(text=btn_back, callback_data="back_profile")
    kb.adjust(1)
    try:
        await call.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    except Exception:
        await call.message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    await call.answer()

async def buy_dollar_callback(call: CallbackQuery):
    await call.answer("Dollar xarid qilish WebApp ilovasi orqali amalga oshiriladi.", show_alert=True)

async def get_dollar_callback(call: CallbackQuery):
    await get_diamond_hamyonlar(call)

async def buy_handler(call: CallbackQuery):
    await call.answer("Xarid qabul qilindi!", show_alert=True)

async def open_protections_menu(call: CallbackQuery):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from models.user import User, Profile
    from utils.i18n import clean_lang, PROFILE_LABELS

    user = await User.filter(user_id=call.from_user.id).first()
    profile = await Profile.get_or_none(user=user) if user else None

    if not profile:
        await call.answer("Profil topilmadi.", show_alert=True)
        return

    lang = clean_lang(user.lang if user else "uz")
    lbls = PROFILE_LABELS.get(lang, PROFILE_LABELS["uz"])
    btn_back = lbls.get("btn_back", "⬅️ Orqaga")

    headers = {
        "uz": "🛡 <b>Sizning himoyalaringiz va anjomlaringiz:</b>",
        "ru": "🛡 <b>Ваши защиты и инвентарь:</b>",
        "en": "🛡 <b>Your protections and items:</b>",
        "tr": "🛡 <b>Korumalarınız ve eşyalarınız:</b>"
    }

    item_names = {
        "uz": {
            "himoya": "Tinch axoli himoyasi", "qotildan_himoya": "Qotildan himoya",
            "osishdan_himoya": "Osishdan himoya", "doridan_himoya": "Doridan himoya",
            "miltiq": "Miltiq", "hujjat": "Hujjat", "maska": "Maska",
            "slip_himoya": "Sirpanishdan himoya", "geroy_himoya": "Geroy himoya"
        },
        "ru": {
            "himoya": "Защита жителя", "qotildan_himoya": "Защита от киллера",
            "osishdan_himoya": "Защита от повешения", "doridan_himoya": "Защита от лекарства",
            "miltiq": "Винтовка", "hujjat": "Документ", "maska": "Маска",
            "slip_himoya": "Защита от скольжения", "geroy_himoya": "Защита от героя"
        },
        "en": {
            "himoya": "Civilian protection", "qotildan_himoya": "Killer protection",
            "osishdan_himoya": "Hang protection", "doridan_himoya": "Medicine protection",
            "miltiq": "Rifle", "hujjat": "Document", "maska": "Mask",
            "slip_himoya": "Slip protection", "geroy_himoya": "Hero protection"
        },
        "tr": {
            "himoya": "Sivil koruması", "qotildan_himoya": "Katilden koruma",
            "osishdan_himoya": "Asılma koruması", "doridan_himoya": "İlaç koruması",
            "miltiq": "Tüfek", "hujjat": "Belge", "maska": "Maske",
            "slip_himoya": "Kayma koruması", "geroy_himoya": "Kahraman koruması"
        }
    }
    inames = item_names.get(lang, item_names["uz"])

    text = (
        f"{headers.get(lang, headers['uz'])}\n\n"
        f"🔰 {inames['himoya']}: <b>{profile.himoya} ta</b>\n"
        f"🔪 {inames['qotildan_himoya']}: <b>{profile.qotildan_himoya} ta</b>\n"
        f"🪢 {inames['osishdan_himoya']}: <b>{profile.osishdan_himoya} ta</b>\n"
        f"🩺 {inames['doridan_himoya']}: <b>{profile.doridan_himoya} ta</b>\n"
        f"🎯 {inames['miltiq']}: <b>{profile.miltiq} ta</b>\n"
        f"📄 {inames['hujjat']}: <b>{profile.hujjat} ta</b>\n"
        f"🎭 {inames['maska']}: <b>{profile.maska} ta</b>\n"
        f"🚷 {inames['slip_himoya']}: <b>{profile.slip_himoya} ta</b>\n"
        f"👑 {inames['geroy_himoya']}: <b>{profile.geroy_himoya} ta</b>"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text=btn_back, callback_data="back_profile")

    try:
        await call.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    except Exception:
        await call.message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    await call.answer()

async def back_profile(call: CallbackQuery, state):
    await call.message.edit_text("👤 Profil menyusi", reply_markup=get_start_markup())

async def get_diamond_hamyonlar(call: CallbackQuery):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import WebAppInfo
    from config import WEBAPP_URL
    from models.user import User, Profile
    from utils.i18n import clean_lang, PROFILE_LABELS

    user = await User.filter(user_id=call.from_user.id).first()
    profile = await Profile.get_or_none(user=user) if user else None
    lang = clean_lang(user.lang if user else "uz")
    lbls = PROFILE_LABELS.get(lang, PROFILE_LABELS["uz"])
    btn_back = lbls.get("btn_back", "⬅️ Orqaga")

    diamonds = profile.diamond if profile else 0
    dollars = profile.dollar if profile else 0

    bal_texts = {
        "uz": f"💰 <b>Balans ma'lumotlari:</b>\n\n💎 Olmoslar: <b>{diamonds:,} ta</b>\n💵 Dollar: <b>{dollars:,} $</b>\n\n<i>Olmos va dollarlarni WebApp do'koni orqali xarid qilishingiz mumkin.</i>",
        "ru": f"💰 <b>Информация о балансе:</b>\n\n💎 Алмазы: <b>{diamonds:,} шт</b>\n💵 Доллары: <b>{dollars:,} $</b>\n\n<i>Вы можете приобрести алмазы и доллары через WebApp магазин.</i>",
        "en": f"💰 <b>Balance details:</b>\n\n💎 Diamonds: <b>{diamonds:,}</b>\n💵 Dollars: <b>{dollars:,} $</b>\n\n<i>You can purchase diamonds and dollars via the WebApp shop.</i>",
        "tr": f"💰 <b>Bakiye bilgileri:</b>\n\n💎 Elmaslar: <b>{diamonds:,} adet</b>\n💵 Dolar: <b>{dollars:,} $</b>\n\n<i>Elmas ve dolarları WebApp mağazasından satın alabilirsiniz.</i>"
    }

    btn_shop_text = {
        "uz": "🛒 Do'konga o'tish (WebApp)",
        "ru": "🛒 Перейти в магазин (WebApp)",
        "en": "🛒 Go to Shop (WebApp)",
        "tr": "🛒 Mağazaya Git (WebApp)"
    }

    text = bal_texts.get(lang, bal_texts["uz"])
    kb = InlineKeyboardBuilder()
    if WEBAPP_URL:
        kb.button(text=btn_shop_text.get(lang, btn_shop_text["uz"]), web_app=WebAppInfo(url=WEBAPP_URL))
    kb.button(text=btn_back, callback_data="back_profile")
    kb.adjust(1)

    try:
        await call.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    except Exception:
        await call.message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    await call.answer()

async def buy_diamond_hamyonlar(call: CallbackQuery):
    await call.answer("Hamyondan xarid!", show_alert=True)

async def check_hamyonlar_payment(call: CallbackQuery):
    await call.answer("To'lov tekshirildi!", show_alert=True)

async def get_star(call: CallbackQuery):
    await call.answer("Telegram Stars orqali to'lov!", show_alert=True)

async def process_buy_star(call: CallbackQuery):
    await call.answer("Telegram Stars xaridi boshlandi!", show_alert=True)

async def process_buy_star_main_bot(message: Message, args: str):
    await message.answer("⭐ Telegram Stars to'lovi qabul qilindi!", parse_mode="HTML")

async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    pass

async def success_payment_handler(message: Message):
    await message.answer("🎉 To'lov muvaffaqiyatli amalga oshirildi!")

async def get_active_role(call: CallbackQuery):
    await call.answer("Faol rol ma'lumoti", show_alert=True)

async def buy_active_role(call: CallbackQuery):
    await call.answer("Faol rol xarid qilindi!", show_alert=True)

async def del_active_role_handler(call: CallbackQuery):
    await call.answer("Faol rol o'chirildi!", show_alert=True)

async def on_off_things(call: CallbackQuery):
    await call.answer("Sozlama o'zgartirildi!", show_alert=True)

async def show_ball_profile_select(call: CallbackQuery):
    await call.answer("Ballar tanlandi!", show_alert=True)

async def show_ball_profile_answer(call: CallbackQuery):
    await call.answer("Ballar profil bo'limi", show_alert=True)

async def get_premium_groups_on_start(call: CallbackQuery, bot: Bot):
    await call.message.edit_text("🌟 <b>Premium Guruhlar:</b>\n\nBot ulangan rasmiy va premium guruhlar ro'yxati.", parse_mode="HTML")

async def get_premium_groups_on_profile(call: CallbackQuery, bot: Bot):
    await call.message.edit_text("🌟 <b>Premium Guruhlar:</b>\n\nSiz a'zo bo'lgan guruhlar.", parse_mode="HTML")

async def lang_command_handler(message: Message):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from models.user import User

    user_id = message.from_user.id if message.from_user else None
    user = await User.filter(user_id=user_id).first() if user_id else None
    curr_lang = user.lang if (user and user.lang) else "uz"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbekcha" + (" ✅" if curr_lang == "uz" else ""), callback_data="setlang_uz"),
            InlineKeyboardButton(text="🇷🇺 Русский" + (" ✅" if curr_lang == "ru" else ""), callback_data="setlang_ru"),
        ],
        [
            InlineKeyboardButton(text="🇬🇧 English" + (" ✅" if curr_lang == "en" else ""), callback_data="setlang_en"),
            InlineKeyboardButton(text="🇹🇷 Türkçe" + (" ✅" if curr_lang == "tr" else ""), callback_data="setlang_tr"),
        ],
        [
            InlineKeyboardButton(text="🇰🇿 Qazaqsha" + (" ✅" if curr_lang == "kk" else ""), callback_data="setlang_kk"),
        ]
    ])

    text_map = {
        "uz": "🌐 <b>Bot tilini tanlang / Choose language:</b>",
        "ru": "🌐 <b>Выберите язык бота:</b>",
        "en": "🌐 <b>Choose bot language:</b>",
        "tr": "🌐 <b>Bot dilini seçin:</b>",
        "kk": "🌐 <b>Бот тілін таңдаңыз:</b>"
    }
    await message.answer(text_map.get(curr_lang, text_map["uz"]), reply_markup=kb, parse_mode="HTML")

async def set_lang_callback(call: CallbackQuery, bot: Bot = None):
    from models.user import User
    from models.game_data import Chat
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    lang = call.data.split("_")[1]
    if lang not in ["uz", "ru", "en", "tr", "kk"]:
        lang = "uz"

    user_id = call.from_user.id
    chat_id = call.message.chat.id
    chat_type = call.message.chat.type

    user = await User.filter(user_id=user_id).first()
    if user:
        user.lang = lang
        await user.save()
    else:
        await User.create(
            user_id=user_id,
            full_name=call.from_user.full_name or f"User_{user_id}",
            username=call.from_user.username,
            lang=lang
        )

    if chat_type in ["group", "supergroup"]:
        from utils.database import redis_client
        await redis_client.set(f"chat:{chat_id}:lang", lang)
        chat = await Chat.filter(chat_id=chat_id).first()
        if chat:
            chat.lang = lang
            await chat.save()
        else:
            await Chat.create(
                chat_id=chat_id,
                title=call.message.chat.title or f"Chat_{chat_id}",
                type=chat_type,
                lang=lang
            )

    confirm_map = {
        "uz": "✅ Bot tili O'zbek tiliga o'zgartirildi!",
        "ru": "✅ Язык бота изменен на Русский!",
        "en": "✅ Bot language changed to English!",
        "tr": "✅ Bot dili Türkçe olarak değiştirildi!",
        "kk": "✅ Бот тілі Қазақ тіліне өзгертілді!"
    }
    await call.answer(confirm_map.get(lang, confirm_map["uz"]))

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbekcha" + (" ✅" if lang == "uz" else ""), callback_data="setlang_uz"),
            InlineKeyboardButton(text="🇷🇺 Русский" + (" ✅" if lang == "ru" else ""), callback_data="setlang_ru"),
        ],
        [
            InlineKeyboardButton(text="🇬🇧 English" + (" ✅" if lang == "en" else ""), callback_data="setlang_en"),
            InlineKeyboardButton(text="🇹🇷 Türkçe" + (" ✅" if lang == "tr" else ""), callback_data="setlang_tr"),
        ],
        [
            InlineKeyboardButton(text="🇰🇿 Qazaqsha" + (" ✅" if lang == "kk" else ""), callback_data="setlang_kk"),
        ]
    ])
    text_map = {
        "uz": "🌐 <b>Bot tilini tanlang / Choose language:</b>",
        "ru": "🌐 <b>Выберите язык бота:</b>",
        "en": "🌐 <b>Choose bot language:</b>",
        "tr": "🌐 <b>Bot dilini seçin:</b>",
        "kk": "🌐 <b>Бот тілін таңдаңыз:</b>"
    }
    try:
        await call.message.edit_text(text_map.get(lang, text_map["uz"]), reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass

    if chat_type in ["group", "supergroup"] and bot:
        try:
            from utils.redis_game.services.game_service import GameRepository
            from utils.redis_game.handlers import update_players_list_redis
            redis_game = await GameRepository.get_game_by_chat(chat_id)
            if redis_game and redis_game.phase in ["waiting", "starting"]:
                await update_players_list_redis(redis_game.game_id, bot)
            else:
                from models.game_data import Game
                from utils.game_logic import update_players_list
                game = await Game.filter(chat__chat_id=chat_id, is_active=True, phase="waiting").first()
                if game:
                    await update_players_list(game, bot)
        except Exception as e:
            print(f"realtime group language refresh error: {e}")

# Do'kon va Valyutalar
async def show_shop(call: CallbackQuery):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import WebAppInfo
    from config import WEBAPP_URL
    text = (
        "🛒 <b>Do'kon bo'limi</b>\n\n"
        "Barcha anjomlar, himoyalar va olmoslarni sotib olish WebApp ilovamizda mavjud!"
    )
    kb = InlineKeyboardBuilder()
    if WEBAPP_URL:
        kb.button(text="🌐 Do'konni ochish (WebApp)", web_app=WebAppInfo(url=WEBAPP_URL))
    kb.button(text="⬅️ Orqaga", callback_data="back_profile")
    kb.adjust(1)
    try:
        await call.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    except Exception:
        await call.message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    await call.answer()

async def get_dollar_callback(call: CallbackQuery):
    await get_diamond_hamyonlar(call)

async def open_protections_menu(call: CallbackQuery):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from models.user import User, Profile
    user = await User.filter(user_id=call.from_user.id).first()
    profile = await Profile.get_or_none(user=user) if user else None

    if not profile:
        await call.answer("Profil topilmadi.", show_alert=True)
        return

    text = (
        "🛡 <b>Sizning himoyalaringiz va anjomlaringiz:</b>\n\n"
        f"🔰 Tinch axoli himoyasi: <b>{profile.himoya} ta</b>\n"
        f"🔪 Qotildan himoya: <b>{profile.qotildan_himoya} ta</b>\n"
        f"🪢 Osishdan himoya: <b>{profile.osishdan_himoya} ta</b>\n"
        f"🩺 Doridan himoya: <b>{profile.doridan_himoya} ta</b>\n"
        f"🎯 Miltiq: <b>{profile.miltiq} ta</b>\n"
        f"📄 Hujjat: <b>{profile.hujjat} ta</b>\n"
        f"🎭 Maska: <b>{profile.maska} ta</b>\n"
        f"🚷 Slip himoya: <b>{profile.slip_himoya} ta</b>\n"
        f"👑 Geroy himoya: <b>{profile.geroy_himoya} ta</b>"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Orqaga", callback_data="back_profile")

    try:
        await call.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    except Exception:
        await call.message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    await call.answer()

async def get_diamond_hamyonlar(call: CallbackQuery):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import WebAppInfo
    from config import WEBAPP_URL
    from models.user import User, Profile
    user = await User.filter(user_id=call.from_user.id).first()
    profile = await Profile.get_or_none(user=user) if user else None

    diamonds = profile.diamond if profile else 0
    dollars = profile.dollar if profile else 0

    text = (
        "💰 <b>Balans ma'lumotlari:</b>\n\n"
        f"💎 Olmoslar: <b>{diamonds:,} ta</b>\n"
        f"💵 Dollar: <b>{dollars:,} $</b>\n\n"
        "<i>Olmos va dollarlarni WebApp do'koni orqali xarid qilishingiz mumkin.</i>"
    )
    kb = InlineKeyboardBuilder()
    if WEBAPP_URL:
        kb.button(text="🛒 Do'konga o'tish (WebApp)", web_app=WebAppInfo(url=WEBAPP_URL))
    kb.button(text="⬅️ Orqaga", callback_data="back_profile")
    kb.adjust(1)

    try:
        await call.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    except Exception:
        await call.message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    await call.answer()

async def get_premium_groups_on_profile(call: CallbackQuery, bot: Bot):
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    text = (
        "⭐ <b>Premium va rasmiy guruhlar:</b>\n\n"
        "Bot ulangan guruhlarda o'yin o'ynab tajriba va mukofotlar oshiring!"
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Orqaga", callback_data="back_profile")
    try:
        await call.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    except Exception:
        await call.message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
    await call.answer()
