import re
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice
from aiogram import Bot
from models.user import User, Profile, VipUser
from models.game_data import Giveaway, Chat, GamePlayer, Game
from config import ADMINS, DIAMOND_SHOP_USERNAME, SUPPORT_ADMIN
from keyboards.main_keyboard import get_start_markup
from aiogram.utils.keyboard import InlineKeyboardBuilder

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
    if message.from_user.id not in ADMINS:
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
    if message.from_user.id not in ADMINS:
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

    text = (
        f"👤 <b>{html.escape(user.full_name)}</b>{vip_text}\n\n"
        f"💵 Dollar: <b>{profile.dollar:,}</b>\n"
        f"💎 Olmos: <b>{profile.diamond:,}</b>\n\n"
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
      - ID orqali: /give 123456789 100  yoki  /give 123456789 10 olmos
      - Username: /give @username 50
    """
    sender_tg = message.from_user
    if not sender_tg:
        return

    text = message.text.strip()
    parts = text.split()
    if len(parts) < 2:
        await message.answer(
            "ℹ️ <b>O'tkazma formati:</b>\n"
            "• Reply qilib: <code>/give 100</code> yoki <code>/give 5 olmos</code>\n"
            "• ID orqali: <code>/give 123456789 100</code>\n"
            "• Username orqali: <code>/give @username 50</code>",
            parse_mode="HTML"
        )
        return

    # Valyuta turini aniqlash (dollar yoki olmos)
    lower_text = text.lower()
    cmd = parts[0].lower()

    if cmd.startswith("/give"):
        # /give buyrug'i sukut bo'yicha olmos (💎 / almaz) o'tkazadi
        if any(k in lower_text for k in ["dollar", "dolar", "$", "💵", "pul"]):
            is_diamond = False
        else:
            is_diamond = True
    else:
        # /money, /send va boshqa buyruqlar sukut bo'yicha dollar (💵) o'tkazadi
        if any(k in lower_text for k in ["olmos", "diamond", "💎", "almaz"]):
            is_diamond = True
        else:
            is_diamond = False

    target_user = None
    amount = 0

    # 1. Reply bo'lsa
    if message.reply_to_message and message.reply_to_message.from_user:
        target_tg = message.reply_to_message.from_user
        if target_tg.id == sender_tg.id:
            await message.answer("❌ O'zingizga o'tkaza olmaysiz!", parse_mode="HTML")
            return

        target_user, _ = await User.get_or_create(
            user_id=target_tg.id,
            defaults={"full_name": target_tg.full_name, "mention": target_tg.mention_html()}
        )
        for p in parts[1:]:
            clean_p = p.replace("$", "").replace("💎", "")
            if clean_p.isdigit():
                amount = int(clean_p)
                break
    else:
        # 2. ID yoki Username orqali
        target_arg = parts[1].strip()
        for p in parts[1:]:
            clean_p = p.replace("$", "").replace("💎", "")
            if clean_p.isdigit():
                if target_arg.isdigit() and int(clean_p) == int(target_arg):
                    continue
                amount = int(clean_p)

        if target_arg.isdigit():
            target_id = int(target_arg)
            if target_id == sender_tg.id:
                await message.answer("❌ O'zingizga o'tkaza olmaysiz!", parse_mode="HTML")
                return
            target_user = await User.filter(user_id=target_id).first()
        else:
            clean_un = target_arg.lstrip("@").lower()
            target_user = await User.filter(username__iexact=clean_un).first()

    if not target_user:
        await message.answer("❌ Qabul qiluvchi foydalanuvchi topilmadi!", parse_mode="HTML")
        return

    if target_user.user_id == sender_tg.id:
        await message.answer("❌ O'zingizga o'tkaza olmaysiz!", parse_mode="HTML")
        return

    if amount <= 0:
        await message.answer("❌ Noto'g'ri miqdor! (Kamida 1 bo'lishi kerak)", parse_mode="HTML")
        return

    sender_db, sender_profile = await _get_user_and_profile(
        sender_tg.id, sender_tg.full_name, sender_tg.mention_html()
    )
    target_profile, _ = await Profile.get_or_create(user=target_user)

    from tortoise.transactions import in_transaction

    if is_diamond:
        if sender_profile.diamond < amount:
            await message.answer(f"❌ Balansingizda yetarli olmos mavjud emas! (Sizda: {sender_profile.diamond} 💎)", parse_mode="HTML")
            return

        async with in_transaction():
            sender_profile.diamond -= amount
            target_profile.diamond += amount
            await sender_profile.save()
            await target_profile.save()

        unit_name = "💎"
    else:
        if sender_profile.dollar < amount:
            await message.answer(f"❌ Balansingizda yetarli dollar mavjud emas! (Sizda: {sender_profile.dollar:,}$)", parse_mode="HTML")
            return

        async with in_transaction():
            sender_profile.dollar -= amount
            target_profile.dollar += amount
            await sender_profile.save()
            await target_profile.save()

        unit_name = "💵"

    # ✅ <name1> - <name2> ga <soni> ta <pul/almaz> yubordi!
    success_msg = f"{sender_db.mention} - {target_user.mention} ga <b>{amount:,} ta {unit_name}</b> yubordi!"
    await message.answer(success_msg, parse_mode="HTML")

    if bot:
        try:
            await bot.send_message(
                chat_id=target_user.user_id,
                text=f"🎉 {sender_db.mention} sizga <b>{amount:,} ta {unit_name}</b> yubordi!",
                parse_mode="HTML"
            )
        except Exception:
            pass

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
    from utils.i18n import get_chat_lang
    lang = await get_chat_lang(message.chat.id)
    strs = GIVEAWAY_STRINGS.get(lang, GIVEAWAY_STRINGS["uz"])
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
    from utils.giveaways_redis import is_collected_user, add_collected_user, is_processing, mark_as_processing, unmark_as_processing
    from utils.i18n import get_chat_lang
    import random

    chat_id = call.message.chat.id if call.message else 0
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

        reward = random.randint(1, 3)
        profile.diamond += reward
        await profile.save()

        add_collected_user(giveaway_id, user_id)
        new_remaining = remaining - 1

        kb = InlineKeyboardBuilder()
        if new_remaining > 0:
            cb_prefix = "channel-giveaway" if is_channel else "giveaway"
            kb.button(text=strs["btn_enter"].format(remaining=new_remaining), callback_data=f"{cb_prefix}_{giveaway_id}_{new_remaining}_{total}")
        else:
            kb.button(text=strs["btn_ended"], callback_data="giveaway_ended")

        if call.message:
            try:
                await call.message.edit_reply_markup(reply_markup=kb.as_markup())
            except Exception:
                pass

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

async def start_change_giveaway(message: Message, bot: Bot):
    count = _parse_giveaway_count(message)
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Qatnashish", callback_data=f"change_{count}")
    msg = (
        f"🔄 <b>Almashtirish konkursi!</b>\n\n"
        f"🔢 Soni: <b>{count} ta</b>\n"
        f"<i>Qatnashish uchun tugmani bosing!</i>"
    )
    await message.answer(msg, reply_markup=kb.as_markup(), parse_mode="HTML")
    if message.from_user:
        await send_big_giveaway_report(bot, message.from_user, message.chat, "Almashtirish konkursi", count)

async def change_giveaway_callback(call: CallbackQuery, bot: Bot):
    await call.answer("Qatnashdingiz!", show_alert=True)

async def start_change_giveaway_channel(message: Message, bot: Bot):
    count = _parse_giveaway_count(message)
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Qatnashish", callback_data=f"channel-change_{count}")
    msg = (
        f"🔄 <b>Kanal almashtirish konkursi!</b>\n\n"
        f"🔢 Soni: <b>{count} ta</b>\n"
        f"<i>Qatnashish uchun tugmani bosing!</i>"
    )
    await message.answer(msg, reply_markup=kb.as_markup(), parse_mode="HTML")
    if message.from_user:
        await send_big_giveaway_report(bot, message.from_user, message.chat, "Kanal almashtirish konkursi", count)

async def change_giveaway_callback_channel(call: CallbackQuery, bot: Bot):
    await call.answer("Qatnashdingiz!", show_alert=True)

async def start_money_giveaway(message: Message, bot: Bot):
    amount = _parse_giveaway_count(message, default=100)
    kb = InlineKeyboardBuilder()
    kb.button(text="💵 Qatnashish", callback_data=f"mgive_{amount}")
    msg = (
        f"💵 <b>Pul giveaway tarqatildi!</b>\n\n"
        f"💰 Miqdori: <b>{amount:,} $</b>\n"
        f"<i>Qatnashish uchun tugmani bosing!</i>"
    )
    await message.answer(msg, reply_markup=kb.as_markup(), parse_mode="HTML")
    if message.from_user:
        await send_big_giveaway_report(bot, message.from_user, message.chat, "Pul giveaway", amount)

async def money_giveaway_callback(call: CallbackQuery, bot: Bot):
    await call.answer("💵 Pul sovg'asiga qatnashdingiz!", show_alert=True)

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
