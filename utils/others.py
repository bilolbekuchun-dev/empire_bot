import os
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

async def _build_profile_text(user_id: int, full_name: str = "", header: str = "") -> tuple[str, Profile]:
    from utils.premium_emojis import (
        get_dollar_display,
        get_diamond_display,
        get_item_display,
        get_vip_prefix
    )
    from utils.i18n import clean_lang, PROFILE_LABELS
    user, profile = await _get_user_and_profile(user_id, full_name)
    lang = clean_lang(user.lang)
    lbls = PROFILE_LABELS.get(lang, PROFILE_LABELS["uz"])

    vip_user = await VipUser.filter(user_id=user_id).first()
    vip_prefix = get_vip_prefix(vip_user) if vip_user else ""
    
    name_disp = f"{vip_prefix}<b>{full_name or user.full_name or lbls['user']}</b>"
    
    dollar_icon = get_dollar_display()
    diamond_icon = get_diamond_display()
    
    himoya_icon = get_item_display("himoya")
    hujjat_icon = get_item_display("hujjat")
    osish_icon = get_item_display("osishdan_himoya")
    qotil_icon = get_item_display("qotildan_himoya")
    miltiq_icon = get_item_display("miltiq")
    dori_icon = get_item_display("doridan_himoya")
    maska_icon = get_item_display("mask")
    slip_icon = get_item_display("slip_himoya")
    geroy_icon = get_item_display("geroy_himoya")

    text = (
        f"{header}"
        f"👤 {name_disp}\n\n"
        f"{dollar_icon} {lbls['dollar']}: <b>{profile.dollar:,}</b>\n"
        f"{diamond_icon} {lbls['diamond']}: <b>{profile.diamond:,}</b>\n\n"
        f"{himoya_icon} {lbls['himoya']}: <b>{profile.himoya}</b>\n"
        f"{hujjat_icon} {lbls['hujjat']}: <b>{profile.hujjat}</b>\n"
        f"{osish_icon} {lbls['osishdan_himoya']}: <b>{profile.osishdan_himoya}</b>\n"
        f"{qotil_icon} {lbls['qotildan_himoya']}: <b>{profile.qotildan_himoya}</b>\n"
        f"{miltiq_icon} {lbls['miltiq']}: <b>{profile.miltiq}</b>\n"
        f"{dori_icon} {lbls['doridan_himoya']}: <b>{profile.doridan_himoya}</b>\n"
        f"{maska_icon} {lbls['maska']}: <b>{profile.maska}</b>\n"
        f"{slip_icon} {lbls['slip_himoya']}: <b>{profile.slip_himoya}</b>\n"
        f"{geroy_icon} {lbls['geroy_himoya']}: <b>{profile.geroy_himoya}</b>\n\n"
        f"🎯 {lbls['wins']}: <b>{profile.wins}</b>\n"
        f"📜 {lbls['games']}: <b>{profile.games_count}</b>\n\n"
        f"{lbls['partner']}: <i>{lbls['none']}</i>\n\n"
        f"🏙️ {lbls['active_roles']}: <i>{lbls['none']}</i>"
    )
    return text, profile

async def send_game_over_profile(bot: Bot, user_id: int, full_name: str, is_winner: bool, reward: int):
    from keyboards.user_keyboards import profile_keyboards_on_private
    from utils.telegram_utils import safe_send_message
    from utils.premium_emojis import get_dollar_display
    from utils.i18n import clean_lang, GAME_OVER_WINNER, GAME_OVER_LOSER
    from models.user import User

    user = await User.get_or_none(user_id=user_id)
    lang = clean_lang(user.lang if user else "uz")
    dollar_icon = get_dollar_display()
    
    tmpl = GAME_OVER_WINNER.get(lang, GAME_OVER_WINNER["uz"]) if is_winner else GAME_OVER_LOSER.get(lang, GAME_OVER_LOSER["uz"])
    header = tmpl.format(reward=reward, dollar_icon=dollar_icon)

    profile_text, profile = await _build_profile_text(user_id, full_name, header=header)
    kb = profile_keyboards_on_private(profile, lang=lang)
    await safe_send_message(
        bot,
        user_id,
        profile_text,
        reply_markup=kb,
        parse_mode="HTML"
    )

async def get_profile(bot: Bot, message: Message):
    from keyboards.user_keyboards import profile_keyboards_on_private
    from utils.i18n import clean_lang
    user = await User.get_or_none(user_id=message.from_user.id)
    lang = clean_lang(user.lang if user else "uz")

    profile_text, profile = await _build_profile_text(
        message.from_user.id,
        message.from_user.full_name
    )
    kb = profile_keyboards_on_private(profile, lang=lang)
    await message.answer(profile_text, reply_markup=kb, parse_mode="HTML")

async def transfer_funds_handler(message: Message, bot: Bot = None):
    """
    /give, /money, /send buyruqlari orqali pul ($) va olmos (💎) o'tkazish.
    Formati:
      - Reply qilib: /give 5 (5 ta olmos)  yoki  /money 50 (50$)
      - ID orqali: /give 123456789 5  yoki  /money 123456789 50
      - Username: /give @username 5  yoki  /money @username 50
    """
    sender_tg = message.from_user
    if not sender_tg:
        return

    text = message.text.strip()
    parts = text.split()
    if len(parts) < 2:
        await message.answer(
            "ℹ️ <b>O'tkazma formati:</b>\n"
            "• Reply qilib: <code>/give 5</code> (olmos) yoki <code>/money 50</code> ($)\n"
            "• ID orqali: <code>/give 123456789 5</code> yoki <code>/money 123456789 50</code>\n"
            "• Username orqali: <code>/give @username 5</code> yoki <code>/money @username 50</code>",
            parse_mode="HTML"
        )
        return

    cmd = parts[0].lower()
    lower_text = text.lower()

    # Valyuta turini aniqlash: /give -> olmos (diamond), /money /pul -> dollar ($)
    if any(k in lower_text for k in ["olmos", "diamond", "💎"]):
        is_diamond = True
    elif any(k in lower_text for k in ["dollar", "pul", "$"]):
        is_diamond = False
    elif cmd.startswith("/give"):
        is_diamond = True
    elif cmd.startswith("/money") or cmd.startswith("/pul"):
        is_diamond = False
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
        if len(parts) < 3:
            await message.answer(
                "ℹ️ <b>O'tkazma formati:</b>\n"
                "• Reply qilib: <code>/give 5</code> (olmos) yoki <code>/money 50</code> ($)\n"
                "• ID orqali: <code>/give 123456789 5</code>\n"
                "• Username orqali: <code>/money @username 50</code>",
                parse_mode="HTML"
            )
            return

        target_arg = parts[1].strip()
        for p in parts[2:]:
            clean_p = p.replace("$", "").replace("💎", "")
            if clean_p.isdigit():
                amount = int(clean_p)
                break

        if not amount:
            for p in parts[1:]:
                clean_p = p.replace("$", "").replace("💎", "")
                if clean_p.isdigit() and (not target_arg.isdigit() or int(clean_p) != int(target_arg)):
                    amount = int(clean_p)
                    break

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
    from utils.premium_emojis import get_diamond_display, get_dollar_display

    if is_diamond:
        if sender_profile.diamond < amount:
            await message.answer(f"❌ Balansingizda yetarli olmos mavjud emas! (Sizda: {sender_profile.diamond} 💎)", parse_mode="HTML")
            return

        async with in_transaction():
            sender_profile.diamond -= amount
            target_profile.diamond += amount
            await sender_profile.save()
            await target_profile.save()

        unit_icon = get_diamond_display()
        unit_name = f"{unit_icon} olmos"
    else:
        if sender_profile.dollar < amount:
            await message.answer(f"❌ Balansingizda yetarli dollar mavjud emas! (Sizda: {sender_profile.dollar:,}$)", parse_mode="HTML")
            return

        async with in_transaction():
            sender_profile.dollar -= amount
            target_profile.dollar += amount
            await sender_profile.save()
            await target_profile.save()

        unit_icon = get_dollar_display()
        unit_name = f"{unit_icon} pul"

    # ✅ Guruhga va shaxsiyga xabar yuborish
    success_msg = f"{sender_db.mention} — {target_user.mention} ga <b>{amount:,} ta {unit_name}</b> o'tkazdi!"
    await message.answer(success_msg, parse_mode="HTML")


    if bot and target_user.user_id != message.chat.id:
        try:
            await bot.send_message(
                chat_id=target_user.user_id,
                text=f"🎉 {sender_db.mention} sizga <b>{amount:,} ta {unit_name}</b> o'tkazdi!",
                parse_mode="HTML"
            )
        except Exception:
            pass







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
    await call.answer("Siz bloklangansiz.", show_alert=True)

# Giveaway va aksiyalar
async def start_game_giveaway(message: Message, bot: Bot):
    await message.answer("🎉 O'yin giveaway tanlovi boshlandi!")

async def game_giveaway_callback(call: CallbackQuery, bot: Bot):
    await call.answer("🎉 Sovg'aga qatnashdingiz!", show_alert=True)

async def start_giveaway_redis(message: Message, bot: Bot):
    await message.answer("🎁 Giveaway e'lon qilindi!")

async def start_giveaway_channel(message: Message, bot: Bot):
    await message.answer("📢 Kanal giveaway e'lon qilindi!")

async def giveaway_callback_redis(call: CallbackQuery, bot: Bot):
    await call.answer("🎁 Qatnashish qabul qilindi!", show_alert=True)

async def giveaway_callback_channel(call: CallbackQuery, bot: Bot):
    await call.answer("📢 Qatnashish qabul qilindi!", show_alert=True)

async def start_qotil_protection_giveaway(message: Message, bot: Bot):
    await message.answer(f"🎁 {EMOJI_QOTIL_HIMOYA} sovg'asi!", parse_mode="HTML")

async def qotil_protection_giveaway_callback(call: CallbackQuery, bot: Bot):
    await call.answer("⛑️ Qotildan himoya sovg'asiga yozildingiz!", show_alert=True)

async def start_ovozdan_protection_giveaway(message: Message, bot: Bot):
    await message.answer("🎁 Ovozdan himoya sovg'asi!", parse_mode="HTML")

async def ovoz_protection_giveaway_callback(call: CallbackQuery, bot: Bot):
    await call.answer("🛡 Ovozdan himoya yozildingiz!", show_alert=True)

async def start_doridan_protection_giveaway(message: Message, bot: Bot):
    await message.answer("🎁 Doridan himoya sovg'asi!", parse_mode="HTML")

async def doridan_protection_giveaway_callback(call: CallbackQuery, bot: Bot):
    await call.answer("💊 Doridan himoya yozildingiz!", show_alert=True)

async def start_miltiq_giveaway(message: Message, bot: Bot):
    await message.answer("🎁 Miltiq sovg'asi!", parse_mode="HTML")

async def miltiq_giveaway_callback(call: CallbackQuery, bot: Bot):
    await call.answer("🔫 Miltiq sovg'asiga yozildingiz!", show_alert=True)

async def start_slip_protection_giveaway(message: Message, bot: Bot):
    await message.answer(f"🎁 {EMOJI_SLIP_HIMOYA} sovg'asi!", parse_mode="HTML")

async def slip_protection_giveaway_callback(call: CallbackQuery, bot: Bot):
    await call.answer("🪤 Sirpanishdan himoya yozildingiz!", show_alert=True)

async def start_geroy_himoya_giveaway(message: Message, bot: Bot):
    await message.answer(f"🎁 {EMOJI_GEROY_HIMOYA} sovg'asi!", parse_mode="HTML")

async def geroy_himoya_giveaway_callback(call: CallbackQuery, bot: Bot):
    await call.answer("🔰 Geroy himoya yozildingiz!", show_alert=True)

async def start_protection_giveaway(message: Message, bot: Bot):
    await message.answer(f"🎁 {EMOJI_HIMOYA} sovg'asi!", parse_mode="HTML")

async def protection_giveaway_callback(call: CallbackQuery, bot: Bot):
    await call.answer("🛡 Himoya yozildingiz!", show_alert=True)

async def start_change_giveaway(message: Message, bot: Bot):
    await message.answer("🔄 Almashtirish konkursi!", parse_mode="HTML")

async def change_giveaway_callback(call: CallbackQuery, bot: Bot):
    await call.answer("Qatnashdingiz!", show_alert=True)

async def start_change_giveaway_channel(message: Message, bot: Bot):
    await message.answer("🔄 Kanal almashtirish konkursi!", parse_mode="HTML")

async def change_giveaway_callback_channel(call: CallbackQuery, bot: Bot):
    await call.answer("Qatnashdingiz!", show_alert=True)

async def start_money_giveaway(message: Message, bot: Bot):
    await message.answer("💵 Pul giveaway tarqatildi!", parse_mode="HTML")

async def money_giveaway_callback(call: CallbackQuery, bot: Bot):
    await call.answer("💵 Pul sovg'asiga qatnashdingiz!", show_alert=True)

# Do'kon va Valyutalar
async def show_shop(call: CallbackQuery):
    await call.message.edit_text("🛒 <b>Do'kon</b>\n\nBarcha xaridlar va olmoslar WebApp da mavjud!", parse_mode="HTML")

async def buy_dollar_callback(call: CallbackQuery):
    await call.answer("Dollar xarid qilish WebApp ilovasi orqali amalga oshiriladi.", show_alert=True)

async def get_dollar_callback(call: CallbackQuery):
    await call.answer("Dollar olish uchun do'kondan foydalaning.", show_alert=True)

async def buy_handler(call: CallbackQuery):
    await call.answer("Xarid qabul qilindi!", show_alert=True)

async def open_protections_menu(call: CallbackQuery):
    await call.message.edit_text("🛡 <b>Himoyalar bo'limi:</b>\n\nHimoyalar holati WebApp da ko'rsatilgan.", parse_mode="HTML")

async def back_profile(call: CallbackQuery, state):
    await call.message.edit_text("👤 Profil menyusi", reply_markup=get_start_markup())

async def get_diamond_hamyonlar(call: CallbackQuery):
    await call.answer("Hamyonlar ro'yxati!", show_alert=True)

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
    from utils.i18n import clean_lang, LANG_SELECT_PROMPT, LANGUAGES

    user_id = message.from_user.id if message.from_user else None
    user = await User.filter(user_id=user_id).first() if user_id else None
    curr_lang = clean_lang(user.lang if user else "uz")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"{LANGUAGES['uz']}" + (" ✅" if curr_lang == "uz" else ""), callback_data="setlang_uz"),
            InlineKeyboardButton(text=f"{LANGUAGES['ru']}" + (" ✅" if curr_lang == "ru" else ""), callback_data="setlang_ru"),
        ],
        [
            InlineKeyboardButton(text=f"{LANGUAGES['en']}" + (" ✅" if curr_lang == "en" else ""), callback_data="setlang_en"),
            InlineKeyboardButton(text=f"{LANGUAGES['tr']}" + (" ✅" if curr_lang == "tr" else ""), callback_data="setlang_tr"),
        ]
    ])

    await message.answer(LANG_SELECT_PROMPT.get(curr_lang, LANG_SELECT_PROMPT["uz"]), reply_markup=kb, parse_mode="HTML")

async def set_lang_callback(call: CallbackQuery):
    from models.user import User
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from utils.i18n import clean_lang, LANG_CONFIRM, LANG_SELECT_PROMPT, LANGUAGES

    lang = clean_lang(call.data.split("_")[1])
    user_id = call.from_user.id
    
    await User.filter(user_id=user_id).update(lang=lang)
    await call.answer(LANG_CONFIRM.get(lang, LANG_CONFIRM["uz"]), show_alert=True)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"{LANGUAGES['uz']}" + (" ✅" if lang == "uz" else ""), callback_data="setlang_uz"),
            InlineKeyboardButton(text=f"{LANGUAGES['ru']}" + (" ✅" if lang == "ru" else ""), callback_data="setlang_ru"),
        ],
        [
            InlineKeyboardButton(text=f"{LANGUAGES['en']}" + (" ✅" if lang == "en" else ""), callback_data="setlang_en"),
            InlineKeyboardButton(text=f"{LANGUAGES['tr']}" + (" ✅" if lang == "tr" else ""), callback_data="setlang_tr"),
        ]
    ])
    try:
        await call.message.edit_text(LANG_SELECT_PROMPT.get(lang, LANG_SELECT_PROMPT["uz"]), reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass
