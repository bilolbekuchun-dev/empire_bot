from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from models.game_data import Geroys
from models.user import User, Profile
from aiogram.fsm.context import FSMContext
from states.game_states import GeroyNameState
from config import ADMINS, INFO_GROUP
from utils.premium_emojis import get_diamond_display, get_dollar_display
import asyncio

BALL_PRICE = 50
SHIELD_PRICE = 64
GUN_PRICE = 95
NAME_PRICE = 780

def get_geroy_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ 1000 Ball", callback_data="geroy_update-ball")
    builder.button(text="🛡 Himoyani yangilash", callback_data="geroy_update-shield")
    builder.button(text="🩸 Qurolni o'qlash", callback_data="geroy_update-gun")
    builder.button(text="🖋 Geroy nomini o'zgartirish", callback_data="geroy_update-name")
    builder.button(text="⭐️ Darajalar haqida", callback_data="geroy_levels-list")
    builder.button(text="🛒 Geroy Marketga qo'shish", callback_data="add_my_geroy_market")
    builder.button(text="⬅️ Orqaga", callback_data="back_profile")
    builder.adjust(1)
    return builder.as_markup()

def get_back_geroy_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Orqaga", callback_data="my_geroy")
    return builder.as_markup()

async def my_geroy_info_handler(call: CallbackQuery):
    user, _ = await User.get_or_create(
        user_id=call.from_user.id,
        defaults={"full_name": call.from_user.full_name, "mention": call.from_user.mention_html()}
    )
    geroy = await Geroys.get_or_none(user=user)
    if not geroy:
        await call.answer("🥷 Sizda Geroy mavjud emas!", show_alert=True)
        return
    
    calculated_level = max(1, geroy.ball // 1100 + 1)
    if calculated_level != geroy.level:
        geroy.level = calculated_level
        await geroy.save()
    
    min_dmg = 40 + (geroy.level - 1) * 7
    max_dmg = 40 + geroy.level * 7
    dmg_text = "maksimal uradi" if min_dmg >= 100 else f"{min_dmg}-{max_dmg} oralig'ida"
    max_himoya = int(10 * max(1, geroy.level / 1.2))
    
    dia_icon = get_diamond_display()
    d_icon = get_dollar_display()
    
    text = (
        f"🥷 <b>Geroy:</b> {geroy.name}\n\n"
        f"⭐️ <b>Daraja:</b> {geroy.level}\n"
        f"👊 <b>Kuch:</b> {dmg_text}\n"
        f"🖤 <b>Himoya:</b> {geroy.himoya}\n"
        f"♥️ <b>Max himoya:</b> {max_himoya}\n"
        f"🩸 <b>Zaryad miqdori:</b> {geroy.patron}/10\n"
        f"☑️ <b>Jami ballari:</b> {geroy.ball} ball\n\n"
        f"⏫ <b>Keyingi daraja</b> = {geroy.level + 1} => {1100 * geroy.level} ball\n\n"
        f"🛒 <b>Xaridlar uchun:</b>\n"
        f"➕ 1000 Ball qo'shish = {dia_icon} {BALL_PRICE}\n"
        f"🛡 Himoyani yangilash = {d_icon} {SHIELD_PRICE + (geroy.level * 100)}\n"
        f"🩸 Qurolni zaryadlash = {d_icon} {GUN_PRICE + (geroy.level * 100)}\n"
        f"🖋 Geroy nomini o'zgartirish = {d_icon} {NAME_PRICE}"
    )
    
    try:
        await call.message.edit_text(text=text, parse_mode="HTML", reply_markup=get_geroy_menu())
    except Exception:
        await call.message.answer(text=text, parse_mode="HTML", reply_markup=get_geroy_menu())
    await call.answer()

async def geroy_info_handler(message: Message):
    """
    /geroyinfo [user_id / @username] yoki reply orqali:
    Geroy ma'lumotlarini ko'rish.
    """
    target_user = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target_uid = message.reply_to_message.from_user.id
        target_user = await User.filter(user_id=target_uid).first()
        if not target_user:
            target_user, _ = await User.get_or_create(
                user_id=target_uid,
                defaults={
                    "full_name": message.reply_to_message.from_user.full_name,
                    "mention": message.reply_to_message.from_user.mention_html(),
                    "username": message.reply_to_message.from_user.username
                }
            )
    else:
        parts = message.text.strip().split()
        if len(parts) >= 2:
            arg = parts[1].strip()
            if arg.isdigit():
                target_uid = int(arg)
                target_user = await User.filter(user_id=target_uid).first()
            else:
                clean_un = arg.lstrip("@").lower()
                target_user = await User.filter(username__iexact=clean_un).first()
        else:
            # Agar hech narsa kiritilmagan bo'lsa, o'zining geroyini ko'rsatadi
            target_uid = message.from_user.id
            target_user, _ = await User.get_or_create(
                user_id=target_uid,
                defaults={
                    "full_name": message.from_user.full_name,
                    "mention": message.from_user.mention_html(),
                    "username": message.from_user.username
                }
            )

    if not target_user:
        await message.answer("❌ Foydalanuvchi topilmadi!", parse_mode="HTML")
        return

    geroy = await Geroys.get_or_none(user=target_user)
    if not geroy:
        await message.answer(f"🥷 <b>{target_user.full_name}</b> da Geroy mavjud emas!", parse_mode="HTML")
        return

    new_level = max(1, geroy.ball // 1100 + 1)
    if new_level != geroy.level:
        geroy.level = new_level
        await geroy.save()

    min_dmg = 40 + (geroy.level - 1) * 7
    max_dmg = 40 + geroy.level * 7
    dmg_text = "maksimal uradi" if min_dmg >= 100 else f"{min_dmg}-{max_dmg} oralig'ida"
    max_himoya = int(10 * max(1, geroy.level / 1.2))

    await message.answer(
        f"🥷 <b>Geroy:</b> {geroy.name}\n"
        f"👤 <b>Egasi:</b> {target_user.mention}\n\n"
        f"⭐️ <b>Daraja:</b> {geroy.level}\n"
        f"👊 <b>Kuch:</b> {dmg_text}\n"
        f"🖤 <b>Himoya:</b> {geroy.himoya}\n"
        f"♥️ <b>Max himoya:</b> {max_himoya}\n"
        f"🩸 <b>Zaryad miqdori:</b> {geroy.patron}/10\n"
        f"☑️ <b>Jami ballari:</b> {geroy.ball} ball\n\n"
        f"⏫ <b>Keyingi daraja</b> = {geroy.level + 1} => {1100 * geroy.level} ball",
        parse_mode="HTML"
    )

async def give_geroy_from_admin(message: Message):
    """
    Admin buyrug'i: /geroy [user_id / @username] [ball (default: 1100)]
    Foydalanuvchiga geroy berish yoki ballini oshirish.
    """
    sender_id = message.from_user.id if message.from_user else None
    if sender_id not in ADMINS:
        return

    target_user = None
    ball = 1100

    if message.reply_to_message and message.reply_to_message.from_user:
        target_uid = message.reply_to_message.from_user.id
        target_user, _ = await User.get_or_create(
            user_id=target_uid,
            defaults={
                "full_name": message.reply_to_message.from_user.full_name,
                "mention": message.reply_to_message.from_user.mention_html(),
                "username": message.reply_to_message.from_user.username
            }
        )
        parts = message.text.strip().split()
        if len(parts) >= 2 and parts[1].isdigit():
            ball = int(parts[1])
    else:
        parts = message.text.strip().split()
        if len(parts) < 2:
            await message.answer(
                "ℹ️ <b>Foydalanish:</b>\n"
                "• Reply orqali: <code>/geroy [ball]</code>\n"
                "• ID orqali: <code>/geroy 123456789 [ball]</code>\n"
                "• Username orqali: <code>/geroy @username [ball]</code>",
                parse_mode="HTML"
            )
            return

        arg = parts[1].strip()
        if len(parts) >= 3 and parts[2].isdigit():
            ball = int(parts[2])

        if arg.isdigit():
            target_uid = int(arg)
            target_user = await User.filter(user_id=target_uid).first()
        else:
            clean_un = arg.lstrip("@").lower()
            target_user = await User.filter(username__iexact=clean_un).first()

    if not target_user:
        await message.answer("❌ Bunday foydalanuvchi topilmadi!", parse_mode="HTML")
        return

    geroy = await Geroys.get_or_none(user=target_user)
    if geroy:
        geroy.ball += ball
        geroy.level = max(1, geroy.ball // 1100 + 1)
        await geroy.save()
        await message.answer(
            f"✅ <b>{target_user.full_name}</b> ning geroyiga +{ball} ball qo'shildi!\n"
            f"⭐️ Yangi daraja: <b>{geroy.level}-daraja</b> (Jami: {geroy.ball} ball)",
            parse_mode="HTML"
        )
    else:
        level = max(1, ball // 1100 + 1)
        geroy = await Geroys.create(
            user=target_user,
            name="Nomsiz",
            level=level,
            himoya=int(10 * max(1, level / 1.2)),
            patron=10,
            ball=ball
        )
        await message.answer(
            f"🥷 <b>{target_user.full_name}</b> ga <b>{level}-darajali</b> Geroy ({ball} ball bilan) muvaffaqiyatli taqdim etildi!",
            parse_mode="HTML"
        )

    try:
        await message.bot.send_message(
            chat_id=target_user.user_id,
            text=f"🎉 Tabriklaymiz! Sizga admin tomonidan <b>{geroy.level}-darajali Geroy</b> taqdim etildi! 🥷",
            parse_mode="HTML"
        )
    except Exception:
        pass

async def remove_geroy_from_admin(message: Message):
    """
    Admin buyrug'i: /rgeroy [user_id / @username] yoki reply orqali
    Geroyni o'chirish.
    """
    sender_id = message.from_user.id if message.from_user else None
    if sender_id not in ADMINS:
        return

    target_user = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target_uid = message.reply_to_message.from_user.id
        target_user = await User.filter(user_id=target_uid).first()
    else:
        parts = message.text.strip().split()
        if len(parts) < 2:
            await message.answer(
                "ℹ️ <b>Foydalanish:</b>\n"
                "• Reply orqali: <code>/rgeroy</code>\n"
                "• ID orqali: <code>/rgeroy 123456789</code>\n"
                "• Username orqali: <code>/rgeroy @username</code>",
                parse_mode="HTML"
            )
            return
        arg = parts[1].strip()
        if arg.isdigit():
            target_uid = int(arg)
            target_user = await User.filter(user_id=target_uid).first()
        else:
            clean_un = arg.lstrip("@").lower()
            target_user = await User.filter(username__iexact=clean_un).first()

    if not target_user:
        await message.answer("❌ Bunday foydalanuvchi topilmadi!", parse_mode="HTML")
        return

    geroy = await Geroys.filter(user=target_user).first()
    if not geroy:
        await message.answer(f"⚠️ <b>{target_user.full_name}</b> da Geroy mavjud emas.", parse_mode="HTML")
        return

    await geroy.delete()
    await message.answer(f"✅ <b>{target_user.full_name}</b> ning geroyi muvaffaqiyatli o'chirildi!", parse_mode="HTML")

async def geroy_shop(call: CallbackQuery, state: FSMContext):
    cmd = call.data.split("_")[1]
    match cmd:
        case "levels-list":
            await geroy_levels_list(call)
            return
        case "update-ball":
            await geroy_ball_plus(call)
            return
        case "update-shield":
            await geroy_update_shield(call)
            return
        case "update-gun":
            await geroy_update_potron(call)
            return
        case "update-name":
            await geroy_update_name(call, state=state)
            return
        case _:
            await call.answer("Hozirda geroyning ushbu qismi sozlanmoqda...")

async def geroy_ball_plus(call: CallbackQuery):
    user, _ = await User.get_or_create(
        user_id=call.from_user.id,
        defaults={"full_name": call.from_user.full_name, "mention": call.from_user.mention_html()}
    )
    geroy = await Geroys.get_or_none(user=user)
    profile, _ = await Profile.get_or_create(user=user)
    if not geroy:
        await call.answer("🥷 Sizda Geroy mavjud emas!", show_alert=True)
        return
    if profile.diamond < BALL_PRICE:
        await call.answer(f"Sizda yetarli olmos yo'q! Kerak: {BALL_PRICE} 💎", show_alert=True)
        return
    profile.diamond -= BALL_PRICE
    geroy.ball += 1000
    
    new_level = max(1, geroy.ball // 1100 + 1)
    if new_level > geroy.level:
        geroy.level = new_level

    await profile.save()
    await geroy.save()
    await call.answer("✅ 1000 ball qo'shildi!", show_alert=True)
    try:
        await call.bot.send_message(
            INFO_GROUP,
            f"<b>🥷 Geroyga 1 000 ball xarid qilindi</b>\n"
            f"\t<b>👤 Foydalanuvchi:</b> {user.mention} <code>{user.user_id}</code>\n"
            f"\t<b>⭐️ Daraja:</b> {geroy.level}\n",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await my_geroy_info_handler(call)

async def geroy_levels_list(call: CallbackQuery):
    user, _ = await User.get_or_create(
        user_id=call.from_user.id,
        defaults={"full_name": call.from_user.full_name, "mention": call.from_user.mention_html()}
    )
    geroy = await Geroys.get_or_none(user=user)
    if not geroy:
        await call.answer("🥷 Sizda Geroy mavjud emas!", show_alert=True)
        return
    
    levels_info = "\n".join(
        [
            f"⭐️ <b>{i+1}-daraja</b>:\n"
            f"☑️ O'tish balli: {1100 * i} ball\n"
            f"👊 <b>Kuch:</b> {40 + (i * 7) if 40 + (i * 7) < 100 else 'maksimal uradi'}-{40 + ((i + 1) * 7) if 40 + (i * 7) < 100 else ''}\n"
            f"♥️ <b>Max Himoya:</b> {int(10 * max(1, (i+1) / 1.2))}\n\n"
            for i in range(12)
        ]
    )
    await call.message.edit_text(
        text=f"<b>Geroy darajalari:</b>\n\n{levels_info}<b>Sizning darajangiz: </b>{geroy.level}-daraja",
        parse_mode="HTML", reply_markup=get_back_geroy_menu()
    )
    await call.answer()

async def geroy_update_potron(call: CallbackQuery):
    user, _ = await User.get_or_create(
        user_id=call.from_user.id,
        defaults={"full_name": call.from_user.full_name, "mention": call.from_user.mention_html()}
    )
    geroy = await Geroys.get_or_none(user=user)
    profile, _ = await Profile.get_or_create(user=user)
    if not geroy:
        await call.answer("🥷 Sizda Geroy mavjud emas!", show_alert=True)
        return
    if geroy.patron >= 10:
        await call.answer("Sizning geroyingizda maksimal zaryad mavjud (10/10)!", show_alert=True)
        return
    price = GUN_PRICE + (geroy.level * 100)
    if profile.dollar < price:
        await call.answer(f"Sizda yetarli dollar yo'q! Kerak: {price} 💵", show_alert=True)
        return
    profile.dollar -= price
    geroy.patron = 10
    await profile.save()
    await geroy.save()
    await call.answer("✅ Qurol to'liq zaryadlandi (10/10)!", show_alert=True)
    await my_geroy_info_handler(call)

async def geroy_update_shield(call: CallbackQuery):
    user, _ = await User.get_or_create(
        user_id=call.from_user.id,
        defaults={"full_name": call.from_user.full_name, "mention": call.from_user.mention_html()}
    )
    geroy = await Geroys.get_or_none(user=user)
    profile, _ = await Profile.get_or_create(user=user)
    if not geroy:
        await call.answer("🥷 Sizda Geroy mavjud emas!", show_alert=True)
        return
    max_h = int(10 * max(1, geroy.level / 1.2))
    if geroy.himoya >= max_h:
        await call.answer(f"Sizning geroyingizda maksimal himoya mavjud ({max_h})!", show_alert=True)
        return
    price = SHIELD_PRICE + (geroy.level * 100)
    if profile.dollar < price:
        await call.answer(f"Sizda yetarli dollar yo'q! Kerak: {price} 💵", show_alert=True)
        return
    profile.dollar -= price
    geroy.himoya = max_h
    await profile.save()
    await geroy.save()
    await call.answer(f"✅ Himoya to'liq yangilandi ({max_h})!", show_alert=True)
    await my_geroy_info_handler(call)

async def geroy_update_name(call: CallbackQuery, state: FSMContext):
    user, _ = await User.get_or_create(
        user_id=call.from_user.id,
        defaults={"full_name": call.from_user.full_name, "mention": call.from_user.mention_html()}
    )
    geroy = await Geroys.get_or_none(user=user)
    profile, _ = await Profile.get_or_create(user=user)
    if not geroy:
        await call.answer("🥷 Sizda Geroy mavjud emas!", show_alert=True)
        return
    if profile.dollar < NAME_PRICE:
        await call.answer(f"Sizda yetarli dollar yo'q! Kerak: {NAME_PRICE} 💵", show_alert=True)
        return
    await call.message.answer(
        f"🖋 Geroyning yangi nomini yuboring:\n<i>Narxi: {NAME_PRICE} 💵</i>",
        parse_mode="HTML"
    )
    await call.answer()
    await state.set_state(GeroyNameState.waiting_for_name)

async def process_new_geroy_name(message: Message, state: FSMContext):
    new_name = message.text.strip()
    if len(new_name) > 30:
        await message.answer("❌ Geroy nomi 30 ta belgidan oshmasligi kerak. Qayta yuboring:")
        return

    user, _ = await User.get_or_create(
        user_id=message.from_user.id,
        defaults={"full_name": message.from_user.full_name, "mention": message.from_user.mention_html()}
    )
    geroy = await Geroys.get_or_none(user=user)
    profile, _ = await Profile.get_or_create(user=user)
    if not geroy:
        await message.answer("🥷 Sizda Geroy mavjud emas!", show_alert=True)
        await state.clear()
        return
    if profile.dollar < NAME_PRICE:
        await message.answer(f"❌ Sizda yetarli dollar yo'q! Kerak: {NAME_PRICE} 💵", parse_mode="HTML")
        await state.clear()
        return

    profile.dollar -= NAME_PRICE
    await profile.save()

    geroy.name = new_name
    await geroy.save()
    await state.clear()
    await message.answer(f"✅ Geroy nomi muvaffaqiyatli <b>{new_name}</b> ga o'zgartirildi!", parse_mode="HTML", reply_markup=get_back_geroy_menu())

async def transfer_geroy(message: Message):
    """
    /tgeroy [user_id / @username] yoki reply orqali geroyni o'tkazish.
    """
    target_tg_user = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target_tg_user = message.reply_to_message.from_user
    else:
        parts = message.text.strip().split()
        if len(parts) >= 2:
            arg = parts[1].strip()
            if arg.isdigit():
                target_obj = await User.filter(user_id=int(arg)).first()
            else:
                clean_un = arg.lstrip("@").lower()
                target_obj = await User.filter(username__iexact=clean_un).first()
            if target_obj:
                target_tg_user = target_obj
        else:
            await message.answer(
                "ℹ️ <b>Foydalanish:</b>\n"
                "• Foydalanuvchi xabariga reply qilib: <code>/tgeroy</code>\n"
                "• ID orqali: <code>/tgeroy 123456789</code>\n"
                "• Username orqali: <code>/tgeroy @username</code>",
                parse_mode="HTML"
            )
            return

    if not target_tg_user:
        await message.answer("❌ Qabul qiluvchi foydalanuvchi topilmadi!", parse_mode="HTML")
        return

    sender_tg_user = message.from_user
    target_uid = getattr(target_tg_user, "id", None) or getattr(target_tg_user, "user_id", None)

    if sender_tg_user.id == target_uid:
        await message.answer("❌ O'zingizga geroy o'tkazib bo'lmaydi!", parse_mode="HTML")
        return

    sender, _ = await User.get_or_create(
        user_id=sender_tg_user.id,
        defaults={"full_name": sender_tg_user.full_name, "mention": sender_tg_user.mention_html()}
    )
    geroy = await Geroys.get_or_none(user=sender)
    if not geroy:
        await message.answer("🥷 Sizda Geroy mavjud emas!", parse_mode="HTML")
        return

    profile, _ = await Profile.get_or_create(user=sender)

    if isinstance(target_tg_user, User):
        target = target_tg_user
    else:
        target, _ = await User.get_or_create(
            user_id=target_tg_user.id,
            defaults={"full_name": target_tg_user.full_name, "mention": target_tg_user.mention_html()}
        )

    existing_geroy = await Geroys.get_or_none(user=target)
    if existing_geroy:
        await message.answer(f"⚠️ <b>{target.full_name}</b> da allaqachon geroy mavjud!", parse_mode="HTML")
        return

    cost = max(1, geroy.level)
    dia_icon = get_diamond_display()
    if profile.diamond < cost:
        await message.answer(f"❌ Sizda yetarli {dia_icon} yo'q! O'tkazish komissiyasi: {cost} {dia_icon}", parse_mode="HTML")
        return

    profile.diamond -= cost
    await profile.save()

    geroy.user = target
    await geroy.save()

    await message.answer(
        f"✅ {sender.mention} ➔ {target.mention} ga <b>{geroy.level}-darajali</b> 🥷 geroy muvaffaqiyatli o'tkazildi!",
        parse_mode="HTML"
    )

    try:
        chat_info = f"{message.chat.title} ({message.chat.id})" if getattr(message.chat, "title", None) else f"{message.chat.id}"
        await message.bot.send_message(
            INFO_GROUP,
            f"<b>🥷 Geroy o'tkazildi</b>\n"
            f"\t<b>💸 O'tkazuvchi:</b> {sender.mention}\n"
            f"\t<b>🎯 Qabul qiluvchi:</b> {target.mention}\n"
            f"\t<b>{dia_icon} Komissiya:</b> {cost}\n"
            f"\t<b>🏠 Guruh:</b> {chat_info}",
            parse_mode="HTML"
        )
    except Exception:
        pass