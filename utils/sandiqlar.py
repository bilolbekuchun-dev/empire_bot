from aiogram.types import Message
from models.user import Profile, User, ActiveRole, OpenSandiqs, VipUser
from models.game_data import Chat
from models.game_data import GamePlayer, Game  # importni yuqoriga olib chiqishingiz mumkin
from models.game_data import Giveaway
from keyboards.user_keyboards import profile_keyboards, shop_keyboard, profile_keyboards_on_private, active_role_keyboard, super_sandiq_menu, sandiqlar_menu, mega_sandiq_menu
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from models.game_set import GroupBalance, GroupGiveSet
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import Bot
import asyncio
from config import ADMINS, CHANNEL_USERNAME, CHANNEL_ID, DIAMOND_SHOP_USERNAME
from utils.api_cliients import get_dollar_rate
from utils.role_names import RoleNames
from datetime import timedelta, datetime, timezone
from aiogram.enums import ChatMemberStatus
from config import INFO_GROUP
import random
from aiogram.fsm.context import FSMContext

async def open_sandiqlar(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("""
<b>🎁 Sandiqlar haqida</b>
Sandiqlarni 1 oyda 1 marta ocha olasiz. Botda 2 xil sandiq mavjud:

<b>💰 Super sandiq</b> – ochish uchun 5000 💵 kerak. Ichida 10 ta raqam yashiringan, ulardan 2 dan 8 tagacha olmos topishingiz mumkin.

<b>💎 Mega sandiq</b> – ochish uchun 15 ta olmos kerak. Unda quyidagilar yashiringan:
\t\t☠️ 8 ta bankrot
\t\t✌️ 1 ta 2x bonus (hisobingiz 2 baravar bo‘ladi!)
\t\t💎 10–30 ta olmosli yutuqlar
                                 
⭐️ Vip User - bunda siz 1 oy mobaynida cheksiz sandiq ochishingiz mumkin. Buning uchun 30 ta olmos to'lov qilishingiz kerak.
""", reply_markup=sandiqlar_menu, parse_mode="HTML")
    await call.answer()

async def buy_vip_user(call: CallbackQuery, state: FSMContext):
    user, _ = await User.get_or_create(
        user_id=call.from_user.id,
        defaults={
            "full_name": call.from_user.full_name,
            "mention": call.from_user.mention_html()
        }
    )
    profile, _ = await Profile.get_or_create(user=user)

    if profile.diamond < 30:
        await call.answer("Vip user bolish uchun kamida 30 ta olmos kerak.", show_alert=True)
        return
    vip_user = await VipUser.get_or_none(user=user)
    if vip_user:
        await call.answer("Siz allaqachon Vip user bo'lgansiz!", show_alert=True)
        return
    profile.diamond -= 30
    await profile.save()
    await call.bot.send_message(
        chat_id=INFO_GROUP,
        text=F"""
<b>🎉 Yangi Vip User!

👤 Foydalanuvchi:</b> {user.mention} (){user.user_id})
<b>💎 Olmoslar soni:</b> 30
""", parse_mode="HTML"
    )
    await VipUser.create(user=user)
    await call.answer("Siz endi Vip user bo'ldingiz! Endi har oyda cheksiz sandiq ochishingiz mumkin.", show_alert=True)

async def start_vip_emoji_change(message: Message, state: FSMContext):
    sender_id = message.from_user.id if message.from_user else 0
    if sender_id not in ADMINS:
        return

    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply(
            "❌ <b>/vipemoji</b> buyrug'ini ishlatish uchun biror foydalanuvchining xabariga <b>reply (javob)</b> qilishingiz kerak!\n\n"
            "Masalan: Foydalanuvchi xabariga reply qilib:\n"
            "<code>/vipemoji</code> (so'ng emojini yuborasiz)\n"
            "yoki to'g'ridan-to'g'ri: <code>/vipemoji [custom_emoji]</code>",
            parse_mode="HTML"
        )
        return

    target_tg_user = message.reply_to_message.from_user
    if target_tg_user.is_bot:
        await message.reply("❌ Botlarga VIP emoji o'rnatib bo'lmaydi!")
        return

    target_user, _ = await User.get_or_create(
        user_id=target_tg_user.id,
        defaults={
            "full_name": target_tg_user.full_name or "Foydalanuvchi",
            "mention": target_tg_user.mention_html()
        }
    )

    # Xabarning o'zida custom emoji bormi?
    custom_emoji = None
    for entity in (message.entities or []):
        if entity.type == "custom_emoji":
            custom_emoji = entity
            break

    if custom_emoji:
        emoji_char = message.text[custom_emoji.offset:custom_emoji.offset + custom_emoji.length]
        vip_user, _ = await VipUser.get_or_create(user=target_user, defaults={"duration_days": 30})
        vip_user.emoji_id = custom_emoji.custom_emoji_id
        vip_user.emoji_char = emoji_char
        await vip_user.save()
        await message.reply(
            f"✅ <b>{target_user.full_name}</b> uchun VIP emoji muvaffaqiyatli o'rnatildi: <tg-emoji emoji-id=\"{custom_emoji.custom_emoji_id}\">{emoji_char}</tg-emoji>",
            parse_mode="HTML"
        )
        return

    from handlers.other_handlers import VipEmojiState
    await state.set_state(VipEmojiState.waiting_for_emoji)
    await state.update_data(target_user_id=target_user.user_id, target_name=target_user.full_name)
    await message.reply(
        f"🎨 <b>{target_user.full_name}</b> uchun o'rnatmoqchi bo'lgan premium (custom) emojini yuboring:",
        parse_mode="HTML"
    )

async def start_vip_emoji_change_call(call: CallbackQuery, state: FSMContext):
    user = await User.get_or_none(user_id=call.from_user.id)
    vip_user = await VipUser.get_or_none(user=user) if user else None
    if not vip_user:
        await call.answer("❗ Bu funksiya faqat VIP userlar uchun!", show_alert=True)
        return
    from handlers.other_handlers import VipEmojiState
    await state.set_state(VipEmojiState.waiting_for_emoji)
    await call.answer()
    await call.message.answer(
        "🎨 Menga o'zingiz tanlagan premium (custom) emojini yuboring — u profilingiz va o'yinchilar ro'yxatida ismingiz oldida ko'rinadi.",
        parse_mode="HTML"
    )

async def process_vip_emoji_message(message: Message, state: FSMContext):
    sender_id = message.from_user.id if message.from_user else 0
    state_data = await state.get_data()
    target_user_id = state_data.get("target_user_id")
    await state.clear()

    # Agar admin foydalanuvchiga o'rnatayotgan bo'lsa
    if target_user_id:
        if sender_id not in ADMINS:
            return

        custom_emoji = None
        for entity in (message.entities or []):
            if entity.type == "custom_emoji":
                custom_emoji = entity
                break
        if not custom_emoji:
            await message.reply("❗ Iltimos, premium (custom) emoji yuboring.")
            return

        target_user = await User.get_or_none(user_id=target_user_id)
        if not target_user:
            await message.reply("❌ Foydalanuvchi topilmadi.")
            return

        vip_user, _ = await VipUser.get_or_create(user=target_user, defaults={"duration_days": 30})
        emoji_char = message.text[custom_emoji.offset:custom_emoji.offset + custom_emoji.length]
        vip_user.emoji_id = custom_emoji.custom_emoji_id
        vip_user.emoji_char = emoji_char
        await vip_user.save()
        await message.reply(
            f"✅ <b>{target_user.full_name}</b> uchun VIP emoji muvaffaqiyatli o'rnatildi: <tg-emoji emoji-id=\"{custom_emoji.custom_emoji_id}\">{emoji_char}</tg-emoji>",
            parse_mode="HTML"
        )
        return

    # Foydalanuvchi o'ziga o'rnatayotgan bo'lsa
    custom_emoji = None
    for entity in (message.entities or []):
        if entity.type == "custom_emoji":
            custom_emoji = entity
            break
    if not custom_emoji:
        await message.answer("❗ Iltimos, premium (custom) emoji yuboring.")
        return

    user = await User.get_or_none(user_id=message.from_user.id)
    vip_user = await VipUser.get_or_none(user=user) if user else None
    if not vip_user:
        await message.answer("❗ Bu funksiya faqat VIP userlar uchun!")
        return

    emoji_char = message.text[custom_emoji.offset:custom_emoji.offset + custom_emoji.length]
    vip_user.emoji_id = custom_emoji.custom_emoji_id
    vip_user.emoji_char = emoji_char
    await vip_user.save()
    await message.answer(
        f"✅ VIP emojingiz muvaffaqiyatli o'rnatildi: <tg-emoji emoji-id=\"{custom_emoji.custom_emoji_id}\">{emoji_char}</tg-emoji>",
        parse_mode="HTML"
    )

async def open_super_sandiq(call: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    if state_data.get("super_sandiq_opened", False):
        await call.answer("Siz allaqachon super sandiq ochgansiz!", show_alert=True)
        return

    await state.update_data(super_sandiq_opened=True)
    try:
        data_parts = call.data.split("-")

        user, _ = await User.get_or_create(
            user_id=call.from_user.id,
            defaults={
                "full_name": call.from_user.full_name,
                "mention": call.from_user.mention_html()
            }
        )
        profile, _ = await Profile.get_or_create(user=user)
        # 1) Menyu ochish bosqichi
        if len(data_parts) == 1:
            if profile.dollar < 5000:
                await call.answer("Super sandiqni ochish uchun kamida 5000$ kerak.", show_alert=True)
                return

            is_opened_sandiq = await OpenSandiqs.get_or_none(user=user, sandiq_type="super")
            is_vip_user = await VipUser.get_or_none(user=user)

            if is_opened_sandiq:
                bugun = datetime.now(timezone.utc)
                updated = is_opened_sandiq.updated_at

                if bugun - updated < timedelta(days=30) and not is_vip_user:
                    await call.answer("Super sandiqni faqat 1 oyda 1 marta ochishingiz mumkin!", show_alert=True)
                    return

                # ruxsat berildi – tamg'ani yangilaymiz
                is_opened_sandiq.updated_at = bugun
                await is_opened_sandiq.save()
            else:
                await OpenSandiqs.create(user=user, sandiq_type="super")



            # Eslatma: super_sandiq_menu agar builder bo‘lsa -> .as_markup()
            # va agar funksiya bo‘lsa, kerak bo‘lsa await qiling:
            # reply_markup = await super_sandiq_menu() yoki super_sandiq_menu.as_markup()
            await call.message.answer(
                "Super sandiqdan birini tanlang! Qaysi raqamni ochamiz?",
                reply_markup=super_sandiq_menu  # <-- shu obyekt to‘g‘ri ekanini tekshiring
            )
            await call.answer()
            return

        # 2) Raqam tanlangan bosqich
        elif len(data_parts) == 2 and data_parts[1].isdigit():
            number = int(data_parts[1])
            diamonds = random.randint(2, 5)
            profile.diamond += diamonds
            profile.dollar -= 5000
            await profile.save()

            await call.message.edit_text(
                f"🎉 Tabriklaymiz! Siz {diamonds} ta olmos yutib oldingiz!"
            )
            await call.bot.send_message(
                chat_id=INFO_GROUP,
                text=F"""<b>🎉 Foydalanuvchi super sandiqni ochdi!
            
👤 Foydalanuvchi:</b> {user.mention} ({user.user_id})
<b>💎 Yutuq:</b> {diamonds}
            """, parse_mode="HTML"
            )
            await call.answer()
            return

        else:
            await call.answer("Noto'g'ri so'rov!", show_alert=True)
            return

    finally:
        # 1 soniya bloklab turamiz, keyin har doim o‘chirib qo‘yamiz
        await asyncio.sleep(1)
        await state.update_data(super_sandiq_opened=False)

import random
from aiogram.types import CallbackQuery

async def open_mega_sandiq(call: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    if state_data.get("mega_sandiq_opened", False):
        await call.answer("Siz allaqachon mega sandiq ochgansiz!", show_alert=True)
        return
    await state.update_data(mega_sandiq_opened=True)
    data_parts = call.data.split("-")

    user, _ = await User.get_or_create(
        user_id=call.from_user.id,
        defaults={
            "full_name": call.from_user.full_name,
            "mention": call.from_user.mention_html()
        }
    )
    profile, _ = await Profile.get_or_create(user=user)

    if len(data_parts) == 1:
        if profile.diamond < 15:
            await call.answer("Mega sandiqni ochish uchun kamida 15 ta olmos kerak.", show_alert=True)
            await asyncio.sleep(1)
            await state.update_data(mega_sandiq_opened=False)
            return

        is_opened_sandiq = await OpenSandiqs.get_or_none(user=user, sandiq_type="mega")
        is_vip_user = await VipUser.get_or_none(user=user)
        if is_opened_sandiq:
            bugun = datetime.now(timezone.utc)
            updated = is_opened_sandiq.updated_at

            delta_days = (bugun - updated).days
            if delta_days < 30 and not is_vip_user:
                await call.answer("Mega sandiqni faqat 1 oyda 1 marta ochishingiz mumkin!", show_alert=True)
                await asyncio.sleep(1)
                await state.update_data(mega_sandiq_opened=False)
                return
            else:
                is_opened_sandiq.updated_at = bugun
                await is_opened_sandiq.save()
        else:
            await OpenSandiqs.create(user=user, sandiq_type="mega")


        await call.message.answer(
            "Mega sandiqdan birini tanlang! Qaysi raqamni ochamiz?",
            reply_markup=mega_sandiq_menu
        )
        await call.answer()
        await state.update_data(mega_sandiq_opened=True)
        await asyncio.sleep(1)
        await state.update_data(mega_sandiq_opened=False)

    elif len(data_parts) == 2 and data_parts[1].isdigit():
        outcomes = [
            *[{
                "type": "bankrot",
                "text": "☠️ Afsuski, siz bankrot bo'ldingiz va barcha olmos hamda pulingiz yo'qoladi!",
            } for _ in range(8)],
            {
                "type": "2x",
                "text": "✌️ Ajoyib! Hisobingizdagi olmoslar va pullar 2 barobar oshirildi!",
            }
        ]

        result = random.choice(outcomes)

        if result["type"] == "bankrot":
            profile.dollar = 0
            profile.diamond = 0
            await profile.save()
            await call.message.edit_text(result["text"])
            await call.bot.send_message(
                chat_id=INFO_GROUP,
                text=F"""<b>☠️ Foydalanuvchi bankrot bo'ldi!

👤 Foydalanuvchi:</b> {user.mention} ({user.user_id})
"""
            , parse_mode="HTML"
            )
        else:
            profile.dollar *= 2
            profile.diamond *= 2
            profile.diamond -= 15
            await profile.save()
            await call.message.edit_text(result["text"])
            await call.bot.send_message(
                chat_id=INFO_GROUP,
                text=F"""<b>✌️ Foydalanuvchi 2x bonusni oldi!
👤 Foydalanuvchi:</b> {user.mention} ({user.user_id})
""", parse_mode="HTML"
            )
        await state.update_data(mega_sandiq_opened=True)
        await asyncio.sleep(1)
        await state.update_data(mega_sandiq_opened=False)
        await call.answer()
    else:
        await call.answer("Noto'g'ri so'rov!", show_alert=True)
        await asyncio.sleep(1)
        await state.update_data(mega_sandiq_opened=False)
