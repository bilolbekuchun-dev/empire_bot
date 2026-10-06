from datetime import datetime, timezone, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from models.user import User, Profile
from models.airdrop import UserAirdrop
from utils.airdrop_logic import calculate_reward, apply_reward
from utils.role_spin import process_role_spin

router = Router()

def get_airdrop_menu_kb() -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton(text="🎁 Kunlik Drop (1 💎)", callback_data="claim_airdrop:daily"),
            InlineKeyboardButton(text="📦 Haftalik Drop (7 💎)", callback_data="claim_airdrop:weekly")
        ],
        [
            InlineKeyboardButton(text="💎 Oylik Drop (30 💎)", callback_data="claim_airdrop:monthly")
        ],
        [
            InlineKeyboardButton(text="🎰 Haftalik Rol Spin (2 💎)", callback_data="spin_role_action")
        ],
        [
            InlineKeyboardButton(text="🔄 Yangilash", callback_data="refresh_airdrop_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.message(F.text == "🪂 Airdroplar")
@router.message(F.text == "/airdrop")
async def airdrop_main_menu(message: Message):
    user = await User.get_or_none(user_id=message.from_user.id)
    if not user:
        await message.answer("Foydalanuvchi topilmadi.")
        return

    profile = await Profile.get_or_none(user=user)
    diamonds = profile.diamond if profile else 0

    text = (
        "🪂 <b>EMPIRE AIRDROP VA SPINNER MARKAZI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 Balansingiz: <b>{diamonds:,} almaz</b>\n\n"
        "<b>Mavjud Airdroplar va Muddati:</b>\n"
        "• 🎁 <b>Kunlik Drop:</b> 1 Almaz (12 soatda yo'qoladi)\n"
        "• 📦 <b>Haftalik Drop:</b> 7 Almaz (24 soatda yo'qoladi)\n"
        "• 💎 <b>Oylik Drop:</b> 30 Almaz (48 soatda yo'qoladi)\n\n"
        "<b>🎰 Haftalik Rol Spin (2 Almaz):</b>\n"
        "• Barcha faol rollardan birini tasodifiy yutib olish imkoniyati!\n\n"
        "<i>Kerakli Airdrop yoki Spin tugmasini bosing:</i>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_airdrop_menu_kb())

@router.callback_query(F.data.startswith("claim_airdrop:"))
async def on_claim_airdrop(call: CallbackQuery):
    airdrop_type = call.data.split(":")[1]  # daily, weekly, monthly
    costs = {"daily": 1, "weekly": 7, "monthly": 30}
    cost = costs.get(airdrop_type, 1)

    user = await User.get_or_none(user_id=call.from_user.id)
    if not user:
        await call.answer("Foydalanuvchi topilmadi.", show_alert=True)
        return

    profile = await Profile.get_or_none(user=user)
    if not profile or profile.diamond < cost:
        await call.answer(f"❌ Ushbu Airdrop uchun sizda kamida {cost} almaz bo'lishi kerak!", show_alert=True)
        return

    # Almaz yechish
    profile.diamond -= cost
    await profile.save()

    # Mukofot yaratish va berish
    rew_text, rew_data = calculate_reward(airdrop_type)
    await apply_reward(call.from_user.id, rew_data)

    now = datetime.now(timezone.utc)
    durations = {"daily": 12, "weekly": 24, "monthly": 48}
    expires_at = now + timedelta(hours=durations.get(airdrop_type, 12))

    # DB Log
    await UserAirdrop.create(
        user=user,
        airdrop_type=airdrop_type,
        cost_diamonds=cost,
        is_claimed=True,
        claimed_reward_text=rew_text,
        expires_at=expires_at,
        is_notified=True
    )

    await call.message.edit_text(
        f"🎉 <b>AIRDROP OCHILDI!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{rew_text}\n\n"
        f"💎 Qolgan balansingiz: <b>{profile.diamond:,} almaz</b>",
        parse_mode="HTML",
        reply_markup=get_airdrop_menu_kb()
    )
    await call.answer()

@router.callback_query(F.data == "spin_role_action")
async def on_role_spin(call: CallbackQuery):
    success, msg = await process_role_spin(call.from_user.id)
    await call.answer()
    if not success:
        await call.message.answer(msg, parse_mode="HTML")
    else:
        user = await User.get_or_none(user_id=call.from_user.id)
        profile = await Profile.get_or_none(user=user)
        d_val = profile.diamond if profile else 0
        await call.message.edit_text(
            f"{msg}\n\n💎 Qolgan balansingiz: <b>{d_val:,} almaz</b>",
            parse_mode="HTML",
            reply_markup=get_airdrop_menu_kb()
        )

@router.callback_query(F.data == "refresh_airdrop_menu")
async def on_refresh_menu(call: CallbackQuery):
    user = await User.get_or_none(user_id=call.from_user.id)
    profile = await Profile.get_or_none(user=user)
    diamonds = profile.diamond if profile else 0

    text = (
        "🪂 <b>EMPIRE AIRDROP VA SPINNER MARKAZI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 Balansingiz: <b>{diamonds:,} almaz</b>\n\n"
        "<b>Mavjud Airdroplar va Muddati:</b>\n"
        "• 🎁 <b>Kunlik Drop:</b> 1 Almaz (12 soatda yo'qoladi)\n"
        "• 📦 <b>Haftalik Drop:</b> 7 Almaz (24 soatda yo'qoladi)\n"
        "• 💎 <b>Oylik Drop:</b> 30 Almaz (48 soatda yo'qoladi)\n\n"
        "<b>🎰 Haftalik Rol Spin (2 Almaz):</b>\n"
        "• Barcha faol rollardan birini tasodifiy yutib olish imkoniyati!\n\n"
        "<i>Kerakli Airdrop yoki Spin tugmasini bosing:</i>"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=get_airdrop_menu_kb())
    await call.answer("Yangilandi!")
