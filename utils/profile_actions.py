from aiogram.types import Message
from models.user import Profile, User, ActiveRole, ChangeDiamondGiveAway, VipUser, Blocked_user
from models.game_data import Chat, Geroys
from models.game_data import GamePlayer, Game, PlayersGameBall  # importni yuqoriga olib chiqishingiz mumkin
from models.game_data import Giveaway
from keyboards.user_keyboards import back_profile_menu, approve_transfer_profile_btn, blocking_users, profile_keyboards, shop_keyboard, profile_keyboards_on_private, active_role_keyboard
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from models.game_set import GroupBalance, GroupGiveSet
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import Bot
from .giveaways_redis import create_giveaway, get_giveaway, update_giveaway, save_giveaway,delete_giveaway
from .roles_text import Roles
import asyncio
from config import ADMINS, CHANNEL_USERNAME, CHANNEL_ID, DIAMOND_SHOP_USERNAME
from utils.api_cliients import get_dollar_rate
from utils.role_names import RoleNames
from aiogram.enums import ChatMemberStatus
from config import INFO_GROUP, ADMINS
from random import choice
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from config import INFO_GROUP
from tortoise.functions import Count
from tortoise.transactions import in_transaction

class TransferProfileState(StatesGroup):
    waiting_for_transfer_profile = State()


async def transfer_profile(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("""
<b>🔄 Profil almashish</b>
                                 
O'tkazmoqchi bo'layotgan odamingizni telegram id raqamini yuboring.
Profilni almashish narxi: 5 💎
    """, reply_markup=back_profile_menu, parse_mode="HTML")
    await state.set_state(TransferProfileState.waiting_for_transfer_profile)

async def process_transfer_profile(message: Message, state: FSMContext):
    user, _ = await User.get_or_create(
        user_id=message.from_user.id,
        defaults={
            "full_name": message.from_user.full_name,
            "mention": message.from_user.mention_html()
        }
    )
    profile, _ = await Profile.get_or_create(user=user)
    target_user_id_text = message.text.strip()

    try:
        target_user_id = int(target_user_id_text)
    except ValueError:
        await message.answer("Telegram id noto'g'ri!")
        await state.set_state(None)
        return
    if target_user_id == message.from_user.id:
        await message.answer("O'zingiz bilan profil almashishingiz mumkin emas.")
        return
    if profile.diamond < 5:
        await message.answer("Profilni almashish uchun kamida 5 ta olmos kerak.")
        return

    target_user = await User.get_or_none(user_id=target_user_id)
    if not target_user:
        await message.answer("Bunday foydalanuvchi topilmadi.")
        return

    target_profile = await Profile.get_or_none(user=target_user)
    if not target_profile:
        await message.answer("Bu foydalanuvchida profil mavjud emas.")
        return

    await message.bot.send_message(
        target_user.user_id,
        f"Sizga {message.from_user.full_name} tomonidan profil almashish taklifi berilmoqda, qabul qilasizmi?"
        ,reply_markup=approve_transfer_profile_btn(message.from_user.id)
    )
    await message.answer("Profil almashish taklifi yuborildi. Javobni kuting.")
    await state.set_state(None)

async def approve_transfer_profile(call: CallbackQuery, state: FSMContext):
    data_parts = call.data.split("_")
    action = data_parts[1]
    from_user_id = int(data_parts[2])

    to_user = await User.get_or_none(user_id=call.from_user.id)
    from_user = await User.get_or_none(user_id=from_user_id)
    if not to_user or not from_user:
        await call.answer("Foydalanuvchi topilmadi!", show_alert=True)
        return

    from_profile, _ = await Profile.get_or_create(user=from_user)
    to_profile, _ = await Profile.get_or_create(user=to_user)

    if action == "approve":
        if from_profile.diamond < 5:
            await call.answer("Profilni almashish uchun sizga taklifni bergan odamdan kamida 5 ta olmos kerak.", show_alert=True)
            return

        try:
            async with in_transaction():
                from_profile.diamond -= 5
                await from_profile.save()

                # Vaqtincha "band" qiymatga o'tkazib qo'yamiz — ikkala qatorda user_id
                # bir vaqtda bir xil bo'lib qolishining (unique to'qnashuv/chalkashish) oldini oladi.
                to_user_id_new = from_user_id
                from_user_id_new = call.from_user.id
                to_user.user_id = -to_user.id
                await to_user.save(update_fields=["user_id"])
                from_user.user_id = from_user_id_new
                await from_user.save(update_fields=["user_id"])
                to_user.user_id = to_user_id_new
                await to_user.save(update_fields=["user_id"])
        except Exception as e:
            await call.answer("Xatolik yuz berdi, profil almashinmadi. Qaytadan urinib ko'ring yoki admin bilan bog'laning.", show_alert=True)
            print(f"⚠️ approve_transfer_profile xato: {e}")
            return

        await call.message.edit_text("Profil muvaffaqiyatli almashildi!")
        await call.bot.send_message(
            chat_id=INFO_GROUP,
                    text=F"""<b>🔄 Profil almashindi!
                    
👤 Foydalanuvchi 1:</b> {from_user.mention} ({from_user.user_id})
💎 Olmos: {from_profile.diamond}
💵 Dollar: {from_profile.dollar}

👤 Foydalanuvchi 2:</b> {to_user.mention} ({to_user.user_id})
💎 Olmos: {to_profile.diamond}
💵 Dollar: {to_profile.dollar}
""", parse_mode="HTML"
                    )
        await call.answer("Siz profilni muvaffaqiyatli almashtirdingiz.", show_alert=True)
    
        await call.bot.send_message(
            chat_id=from_user_id,
            text=f"Siz {to_user.full_name} bilan profilni muvaffaqiyatli almashdingiz!"
        )
    else:
        await call.bot.send_message(
            chat_id=from_user_id,
            text=f"{to_user.full_name} profil almashishni rad etdi."
        )
        await call.message.edit_text("Profil almashish bekor qilindi.")
        await call.answer("Siz profil almashishni bekor qildingiz.", show_alert=True)