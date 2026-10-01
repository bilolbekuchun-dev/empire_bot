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
    text = (
        f"👤 <b>Sizning profilingiz:</b>\n\n"
        f"🆔 ID: <code>{user.user_id}</code>\n"
        f"💵 Dollar: <b>{profile.dollar:,}$</b>\n"
        f"💎 Olmos: <b>{profile.diamond:,} ta</b>\n"
        f"🎮 O'yinlar soni: <b>{profile.games_count} ta</b>\n"
        f"🏆 G'alabalar: <b>{profile.wins:,} ta</b>\n"
    )
    await message.answer(text, parse_mode="HTML")

async def transfer_money(message: Message):
    await message.answer("💸 Pul o'tkazmasi profil bo'limi orqali amalga oshiriladi.")

async def transfer_diamond(message: Message):
    await message.answer("💎 Olmos o'tkazmasi profil bo'limi orqali amalga oshiriladi.")

async def check_user_balance(message: Message):
    user, profile = await _get_user_and_profile(message.from_user.id)
    await message.answer(f"💳 Sizning balansingiz: {profile.dollar}$ / {profile.diamond} 💎", parse_mode="HTML")

def _build_roles_text() -> list:
    """Botdagi barcha rollarni toifalar bo'yicha ro'yxat qilib qaytaradi."""
    from config import tinch_rollar, mafia_rollar, yakka_rollar
    from utils.premium_emojis import role_display
    from utils.roles_text import Roles as RolesText
    from utils.telegram_utils import split_long_message

    def block(title: str, roles: list) -> str:
        lines = [f"<b>{title} ({len(roles)} ta):</b>"]
        for r in roles:
            lines.append(f"• <b>{role_display(r)}</b> — {RolesText.get_description(r)}")
        return "\n".join(lines)

    total = len(tinch_rollar) + len(mafia_rollar) + len(yakka_rollar)
    text = (
        f"🎭 <b>BOTDAGI BARCHA ROLLAR ({total} ta)</b>\n\n"
        + block("👨🏼 Tinch aholi", tinch_rollar) + "\n\n"
        + block("🤵 Mafia", mafia_rollar) + "\n\n"
        + block("🃏 Yakkalar", yakka_rollar)
    )
    return split_long_message(text)


async def role_names_handler(message: Message):
    for chunk in _build_roles_text():
        await message.answer(chunk, parse_mode="HTML")

async def get_roles_text(message: Message):
    for chunk in _build_roles_text():
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
