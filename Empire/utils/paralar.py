from aiogram.types import Message
from models.user import Profile, User, ActiveRole, ChangeDiamondGiveAway, VipUser, Blocked_user, Paralar
from models.game_data import Chat, Geroys
from models.game_data import GamePlayer, Game  # importni yuqoriga olib chiqishingiz mumkin
from models.game_data import Giveaway
from keyboards.user_keyboards import blocking_users, profile_keyboards, shop_keyboard, profile_keyboards_on_private, active_role_keyboard, para_gift_menu, para_no_para_keyboard, anon_chat_keyboard
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from models.game_set import GroupBalance, GroupGiveSet
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.game_logic import safe_send_message
from aiogram import Bot
from .roles_text import Roles
import asyncio
from config import ADMINS, CHANNEL_USERNAME, CHANNEL_ID, DIAMOND_SHOP_USERNAME
from utils.role_names import RoleNames
from aiogram.enums import ChatMemberStatus
from config import INFO_GROUP, ADMINS
from random import choice
from datetime import datetime, timedelta
from tortoise.functions import Count
from utils.database import redis_client

# ── ANONIM SUHBAT ──
active_chats: dict[int, int] = {}  # user_id -> partner_user_id

DPARA_FINE = 200
GENDER_CHANGE_MAX = 3


async def _has_active_para(user_id_1: int, user_id_2: int) -> bool:
    """Ikki foydalanuvchi hozir ham para bo'lib turganini tekshiradi."""
    try:
        u1 = await User.get_or_none(user_id=user_id_1)
        u2 = await User.get_or_none(user_id=user_id_2)
        if not u1 or not u2:
            return False
        return bool(
            await Paralar.filter(user1=u1, user2=u2).exists()
            or await Paralar.filter(user1=u2, user2=u1).exists()
        )
    except Exception:
        return False


# Anonim suhbat boshlanganda FSM omborini eslab qolamiz — keyin istalgan
# foydalanuvchining holatini (o'zi yozmasa ham) tozalash uchun kerak bo'ladi.
_fsm_storage = None


async def force_close_anon_chat(*user_ids: int, bot: Bot = None) -> None:
    """Berilgan foydalanuvchilarning anonim suhbat holatini tozalaydi.

    Xotiradagi ro'yxat, Redis kaliti va FSM holati — uchalasi ham tozalanadi,
    shunda ularning keyingi xabarlari oddiy xabar sifatida ishlanadi.
    """
    from aiogram.fsm.storage.base import StorageKey
    from aiogram.fsm.context import FSMContext as _FSM

    for uid in user_ids:
        if not uid:
            continue
        active_chats.pop(uid, None)
        try:
            await redis_client.delete(f"anon_chat:{uid}")
        except Exception:
            pass
        if bot is not None and _fsm_storage is not None:
            try:
                key = StorageKey(bot_id=bot.id, chat_id=uid, user_id=uid)
                await _FSM(storage=_fsm_storage, key=key).clear()
            except Exception:
                pass

async def del_my_para(message: Message):
    user = await User.get_or_none(user_id=message.from_user.id)
    if not user:
        return
    paras1 = await Paralar.filter(user1=user).prefetch_related("user2", "user1").first()
    paras2 = await Paralar.filter(user2=user).prefetch_related("user2", "user1").first()
    para = paras1 or paras2
    if not para:
        await message.answer("Sizda para yo'q. <tg-emoji emoji-id='5913364548554854682'>🖤</tg-emoji>", parse_mode="HTML")
        return

    other_user = para.user2 if para.user1.id == user.id else para.user1

    profile, _ = await Profile.get_or_create(user=user, defaults={"dollar": 0})
    if profile.dollar < DPARA_FINE:
        await message.answer(
            f"❗ Parangizdan ajralish uchun {DPARA_FINE} 💵 jarima to'lashingiz kerak.\n"
            f"Sizda yetarli mablag' yo'q.",
            parse_mode="HTML"
        )
        return

    other_profile, _ = await Profile.get_or_create(user=other_user, defaults={"dollar": 0})
    profile.dollar -= DPARA_FINE
    other_profile.dollar += DPARA_FINE
    await profile.save()
    await other_profile.save()

    await para.delete()

    # Para bekor qilindi — ochiq anonim suhbat ham yopilsin. Aks holda ikkala
    # tomon ham "suhbat" holatida qolib, yozgan har bir xabari eski parasiga
    # ketaverardi (yoki umuman yo'qolardi).
    await force_close_anon_chat(user.user_id, other_user.user_id, bot=message.bot)

    await message.answer(
        f"Sizning parangiz bekor qilindi. {DPARA_FINE} 💵 jarima {other_user.mention}ga o'tkazildi.",
        parse_mode="HTML"
    )
    try:
        await message.bot.send_message(
            chat_id=other_user.user_id,
            text=f"💔 {user.mention} siz bilan parani bekor qildi va {DPARA_FINE} 💵 jarima to'ladi.",
            parse_mode="HTML"
        )
    except:
        pass

async def check_my_para(message: Message):
    user = await User.get_or_none(user_id=message.from_user.id)
    if not user:
        return
    paras = await Paralar.filter(user1=user).prefetch_related("user2", "user1").first()
    if not paras:
        paras = await Paralar.filter(user2=user).prefetch_related("user1", "user2").first()
    if not paras:
        markup = InlineKeyboardBuilder()
        markup.button(text="🎲 Random para topish", callback_data="find_random_para")
        markup.adjust(1)
        await message.answer(
            "Sizda para yo'q. <tg-emoji emoji-id='5913364548554854682'>🖤</tg-emoji>",
            reply_markup=markup.as_markup(),
            parse_mode="HTML"
        )
        return
    other_user = paras.user2 if paras.user1.id == user.id else paras.user1
    await message.answer(f"Sizning parangiz: {other_user.mention} <tg-emoji emoji-id='5402100905883488232'>💍</tg-emoji>", parse_mode="HTML")

async def add_para_request(message: Message):
    user_id = message.reply_to_message.from_user.id if message.reply_to_message else None
    if not user_id:
        return
    if user_id == message.from_user.id:
        return
    user = await User.get_or_none(user_id=message.from_user.id)
    if not user:
        return
    targ_user = await User.get_or_none(user_id=user_id)
    if not targ_user:
        return

    exists = await Paralar.filter(user1=user, user2=targ_user).first()
    if not exists:
        exists = await Paralar.filter(user1=targ_user, user2=user).first()
    if exists:
        await message.answer("Siz allaqachon ushbu foydalanuvchi bilan para bo'lgansiz.")
        return
    
    markup = InlineKeyboardBuilder()
    markup.button(text="Qabul qilish", callback_data=f"para_accept_{user.user_id}_{targ_user.user_id}")
    markup.button(text="Rad etish", callback_data=f"para_decline_{user.user_id}_{targ_user.user_id}")
    markup.adjust(1)
    await message.bot.send_message(
        chat_id=targ_user.user_id,
        text=f"Sizga {user.mention}dan para so'rov yuborildi.",
        reply_markup=markup.as_markup(),
        parse_mode="HTML"
    )
    await message.bot.send_message(
        chat_id=user.user_id,
        text=f"Siz {targ_user.mention}ga para so'rov yubordingiz.",
        parse_mode="HTML"
    )

async def accept_para(callback: CallbackQuery):
    args = callback.data.split("_")
    if len(args) != 4:
        await callback.answer("Noto'g'ri ma'lumot!", show_alert=True)
        return
    user1_id = int(args[2])
    user2_id = int(args[3])
    user1 = await User.get_or_none(user_id=user1_id)
    user2 = await User.get_or_none(user_id=user2_id)
    match args[1]:
        case "accept":
            para = None
            para1 = await Paralar.filter(user1=user1).first()
            para2 = await Paralar.filter(user1=user2).first()
            if para1 and para2:
                await para2.delete()
                para = para1
            if not para:
                para = await Paralar.filter(user1=user2, user2=user1).first()
            if para:
                await callback.answer("Siz allaqachon ushbu foydalanuvchi bilan para bo'lgansiz.", show_alert=True)
                return
            para = await Paralar.filter(user1=user2).first()
            if not para:
                para = await Paralar.filter(user2=user2).first()
                if not para:
                    await Paralar.create(user1=user1, user2=user2)
                else:
                    para.user1 = user1
                    await para.save()
            else:
                para.user2 = user1
                await para.save()
            await callback.answer("Para so'rovi qabul qilindi.")
            await callback.message.edit_text(
                f"Siz {user1.mention} bilan para bo'ldingiz!",
                parse_mode="HTML"
            )
            await safe_send_message(
                callback.bot,
                user1.user_id,
                f"Siz {user2.mention} bilan para bo'ldingiz!",
                parse_mode="HTML"
            )
        case "decline":
            await callback.answer("Para so'rovi rad etildi.")
            await callback.message.edit_text(
                f"Siz {user1.mention}ning para so'rovini rad etdiniz.",
                parse_mode="HTML"
            )
            await callback.bot.send_message(
                chat_id=user1.user_id,
                text=f"Sizning {user2.mention}ga yuborgan para so'rovingiz rad etildi.",
                parse_mode="HTML"
            )

async def show_para_gift_menu(call: CallbackQuery):
    user = await User.get_or_none(user_id=call.from_user.id)
    if not user:
        return
    
    para = await Paralar.filter(user1=user).first()
    if not para:
        para = await Paralar.filter(user2=user).first()
        
    if not para:
        changes_left = max(0, GENDER_CHANGE_MAX - (getattr(user, "gender_changes", 0) or 0))
        await call.message.edit_text(
            "Sizda para yo'q. <tg-emoji emoji-id='5913364548554854682'>🖤</tg-emoji>",
            reply_markup=para_no_para_keyboard(gender_changes_left=changes_left),
            parse_mode="HTML"
        )
        return await call.answer()

    changes_left = max(0, GENDER_CHANGE_MAX - (getattr(user, "gender_changes", 0) or 0))
    await call.message.edit_text(
        "🎁 <b>Parangiz uchun sovg'a yuborish menyusi</b>\n\n"
        "Quyidagilardan birini tanlang:",
        reply_markup=para_gift_menu(gender_changes_left=changes_left),
        parse_mode="HTML"
    )

async def start_para_gift(call: CallbackQuery, state):
    data = call.data.split("_")
    # para_send_dollar, para_send_diamond, para_send_item_{key}
    gift_type = data[2]
    item_key = data[3] if len(data) > 3 else gift_type
    
    await state.update_data(gift_type=gift_type, item_key=item_key)
    
    names = {
        "dollar": "💵",
        "diamond": "💎",
        "himoya": "<tg-emoji emoji-id='5334560212986632624'>🔰</tg-emoji>",
        "hujjat": "<tg-emoji emoji-id='5357315181649076022'>📁</tg-emoji>",
        "qotildan_himoya": "⛑️",
        "osishdan_himoya": "<tg-emoji emoji-id='5283063413373684641'>⚖️</tg-emoji>",
        "miltiq": "<tg-emoji emoji-id='5471993127734632155'>🔫</tg-emoji>",
        "doridan_himoya": "<tg-emoji emoji-id='5420163708674384414'>➕</tg-emoji>",
        "maska": "<tg-emoji emoji-id='5350658016700013471'>🎭</tg-emoji>",
        "slip_himoya": "🪤",
        "geroy_himoya": "🛡️"
    }
    
    name = names.get(item_key, item_key)
    await call.message.edit_text(
        f"📤 <b>{name} yuborish</b>\n\n"
        f"Nechta yubormoqchisiz? (Faqat raqam yuboring)",
        reply_markup=InlineKeyboardBuilder().button(text="⬅️ Orqaga", callback_data="my_para_menu").as_markup(),
        parse_mode="HTML"
    )
    from handlers.paralar import ParaGiftState
    await state.set_state(ParaGiftState.waiting_for_amount)

async def process_para_gift(message: Message, state):
    try:
        amount = int(message.text)
        if amount <= 0:
            raise ValueError
    except:
        return await message.answer("❌ Iltimos, musbat butun son yuboring.")
    
    data = await state.get_data()
    item_key = data.get("item_key")
    
    user = await User.get_or_none(user_id=message.from_user.id)
    profile = await Profile.get_or_none(user=user)
    
    para = await Paralar.filter(user1=user).prefetch_related("user1", "user2").first()
    if not para:
        para = await Paralar.filter(user2=user).prefetch_related("user1", "user2").first()
        
    if not para:
        await state.clear()
        return await message.answer("Sizda para yo'q!")
    
    other_user = para.user2 if para.user1.id == user.id else para.user1
    other_profile = await Profile.get_or_none(user=other_user)
    
    # Check balance
    user_val = getattr(profile, item_key, 0)
    if user_val < amount:
        return await message.answer(f"❌ Sizda yetarli miqdor yo'q! (Sizda: {user_val})")
    
    # Transfer
    setattr(profile, item_key, user_val - amount)
    setattr(other_profile, item_key, getattr(other_profile, item_key, 0) + amount)
    
    await profile.save()
    await other_profile.save()
    
    names = {
        "dollar": "💵",
        "diamond": "💎",
        "himoya": "<tg-emoji emoji-id='5334560212986632624'>🔰</tg-emoji>",
        "hujjat": "<tg-emoji emoji-id='5357315181649076022'>📁</tg-emoji>",
        "qotildan_himoya": "⛑️",
        "osishdan_himoya": "<tg-emoji emoji-id='5283063413373684641'>⚖️</tg-emoji>",
        "miltiq": "<tg-emoji emoji-id='5471993127734632155'>🔫</tg-emoji>",
        "doridan_himoya": "<tg-emoji emoji-id='5420163708674384414'>➕</tg-emoji>",
        "maska": "<tg-emoji emoji-id='5350658016700013471'>🎭</tg-emoji>",
        "slip_himoya": "🪤",
        "geroy_himoya": "🛡️"
    }
    name = names.get(item_key, item_key)
    
    await message.answer(
        f"✅ <b>Muvaffaqiyatli!</b>\n\n"
        f"Parangiz {other_user.mention}ga {amount} ta {name} yuborildi.",
        parse_mode="HTML"
    )
    
    try:
        await message.bot.send_message(
            chat_id=other_user.user_id,
            text=f"🎁 <b>Parangiz <a href='tg://user?id={user.user_id}'>{user.full_name}</a> sizga {amount} ta {name} yubordi!</b>",
            parse_mode="HTML"
        )
    except:
        pass

    await state.clear()

# ── GENDER SELECTION ──

async def open_gender_menu(call: CallbackQuery):
    """'Jinsni o'zgartirish' tugmasi bosilganda — Yigit/Qiz tanlovini ko'rsatadi."""
    from keyboards.main_keyboard import gender_keyboard
    await call.message.edit_text(
        "Jinsingizni tanlang:",
        reply_markup=gender_keyboard()
    )
    await call.answer()

async def select_gender(call: CallbackQuery, gender: str, state=None):
    """gender_select_m / gender_select_f callback handler — Sherif 2 bilan bir xil:
    har bosilganda hisoblanadi, cheklov faqat tugmani yashirish orqali (keyboard
    darajasida) amalga oshiriladi."""
    user = await User.get_or_none(user_id=call.from_user.id)
    if not user:
        return
    user.gender = gender  # "m" yoki "f"
    user.gender_changes = (getattr(user, "gender_changes", 0) or 0) + 1
    await user.save()
    await call.answer("✅ Saqlandi!", show_alert=True)

    pending_args = None
    if state:
        data = await state.get_data()
        pending_args = data.get("pending_start_args")
        if pending_args:
            await state.update_data(pending_start_args=None)

    if pending_args:
        from config import BOT_URL
        markup = InlineKeyboardBuilder()
        markup.button(text="▶️ Davom etish", url=f"{BOT_URL}?start={pending_args}")
        markup.adjust(1)
        await call.message.edit_text(
            "✅ Rahmat! Endi davom etish uchun tugmani bosing:",
            reply_markup=markup.as_markup()
        )
        return

    from utils.start import start_call_handler
    await start_call_handler(call)

# ── RANDOM PARA TOPISH ──

FIND_LIMIT = 3
FIND_LIMIT_VIP = 7
_find_requests: dict[int, tuple[str, int]] = {}  # user_id -> (YYYY-MM-DD, count)

async def _get_find_limit(user) -> int:
    is_vip = await VipUser.get_or_none(user=user)
    return FIND_LIMIT_VIP if is_vip else FIND_LIMIT

async def find_random_para(call: CallbackQuery, bot: Bot):
    """Para yo'q foydalanuvchi uchun teskari jinsli random para topish"""
    user = await User.get_or_none(user_id=call.from_user.id)
    if not user:
        return

    if not user.gender:
        await call.answer("❗ Avval jinsingizni tanlashingiz kerak. /start bosing.", show_alert=True)
        return

    limit = await _get_find_limit(user)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    date_str, count = _find_requests.get(user.user_id, (today, 0))
    if date_str != today:
        count = 0
    if count >= limit:
        await call.answer(f"❗ Kuniga faqat {limit} marta random para so'rovi yuborishingiz mumkin.", show_alert=True)
        return

    existing = await Paralar.filter(user1=user).first()
    if not existing:
        existing = await Paralar.filter(user2=user).first()
    if existing:
        await call.answer("❗ Sizda allaqachon para bor!", show_alert=True)
        return

    opposite = "f" if user.gender == "m" else "m"

    paired_ids = set()
    async for p in Paralar.all():
        paired_ids.add(p.user1_id)
        paired_ids.add(p.user2_id)

    exclude_ids = list(paired_ids | {user.id})
    candidates = await User.filter(gender=opposite).exclude(id__in=exclude_ids).all()

    if not candidates:
        await call.answer("❗ Hozircha mos para topilmadi. Keyinroq urinib ko'ring.", show_alert=True)
        return

    target = choice(candidates)
    _find_requests[user.user_id] = (today, count + 1)

    markup = InlineKeyboardBuilder()
    markup.button(text="Qabul qilish", callback_data=f"para_accept_{user.user_id}_{target.user_id}")
    markup.button(text="Rad etish", callback_data=f"para_decline_{user.user_id}_{target.user_id}")
    markup.adjust(1)

    try:
        await bot.send_message(
            chat_id=target.user_id,
            text=f"💘 Sizga random para so'rovi keldi! Kimdir siz bilan para bo'lishni xohlayapti.",
            reply_markup=markup.as_markup(),
            parse_mode="HTML"
        )
    except Exception:
        await call.answer("❗ Hozircha mos para topilmadi. Keyinroq urinib ko'ring.", show_alert=True)
        return

    await call.answer("✅ Random para so'rovi yuborildi! Javobini kuting.", show_alert=True)

async def find_random_para_command(message: Message, bot: Bot):
    """/rpara komandasi uchun — find_random_para bilan bir xil mantiq, faqat message orqali javob beradi"""
    user = await User.get_or_none(user_id=message.from_user.id)
    if not user:
        return

    if not user.gender:
        await message.answer("❗ Avval jinsingizni tanlashingiz kerak. /start bosing.")
        return

    limit = await _get_find_limit(user)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    date_str, count = _find_requests.get(user.user_id, (today, 0))
    if date_str != today:
        count = 0
    if count >= limit:
        await message.answer(f"❗ Kuniga faqat {limit} marta random para so'rovi yuborishingiz mumkin.")
        return

    existing = await Paralar.filter(user1=user).first()
    if not existing:
        existing = await Paralar.filter(user2=user).first()
    if existing:
        await message.answer("❗ Sizda allaqachon para bor!")
        return

    opposite = "f" if user.gender == "m" else "m"

    paired_ids = set()
    async for p in Paralar.all():
        paired_ids.add(p.user1_id)
        paired_ids.add(p.user2_id)

    exclude_ids = list(paired_ids | {user.id})
    candidates = await User.filter(gender=opposite).exclude(id__in=exclude_ids).all()

    if not candidates:
        await message.answer("❗ Hozircha mos para topilmadi. Keyinroq urinib ko'ring.")
        return

    target = choice(candidates)
    _find_requests[user.user_id] = (today, count + 1)

    markup = InlineKeyboardBuilder()
    markup.button(text="Qabul qilish", callback_data=f"para_accept_{user.user_id}_{target.user_id}")
    markup.button(text="Rad etish", callback_data=f"para_decline_{user.user_id}_{target.user_id}")
    markup.adjust(1)

    try:
        await bot.send_message(
            chat_id=target.user_id,
            text=f"💘 Sizga random para so'rovi keldi! Kimdir siz bilan para bo'lishni xohlayapti.",
            reply_markup=markup.as_markup(),
            parse_mode="HTML"
        )
    except Exception:
        await message.answer("❗ Hozircha mos para topilmadi. Keyinroq urinib ko'ring.")
        return

    await message.answer("✅ Random para so'rovi yuborildi! Javobini kuting.")

# ── ANONIM SUHBAT ──

async def para_chat_request(call: CallbackQuery, bot: Bot, state):
    """Parasiga anonim suhbat so'rovi yuborish"""
    user = await User.get_or_none(user_id=call.from_user.id)
    if not user:
        return

    if call.from_user.id in active_chats:
        await call.answer("❗ Siz allaqachon suhbatdasiz!", show_alert=True)
        return

    para = await Paralar.filter(user1=user).prefetch_related("user2").first()
    if not para:
        para = await Paralar.filter(user2=user).prefetch_related("user1").first()
    if not para:
        await call.answer("❗ Sizda para yo'q!", show_alert=True)
        return

    partner = para.user2 if para.user1_id == user.id else para.user1

    markup = InlineKeyboardBuilder()
    markup.button(text="✅ Qabul qilish", callback_data=f"para_chat_accept_{user.user_id}")
    markup.button(text="❌ Rad etish", callback_data=f"para_chat_decline_{user.user_id}")
    markup.adjust(1)

    try:
        await bot.send_message(
            chat_id=partner.user_id,
            text="💬 Parangiz sizga anonim suhbat taklif qilyapti!",
            reply_markup=markup.as_markup(),
            parse_mode="HTML"
        )
    except Exception:
        await call.answer("❗ Parangizga xabar yuborib bo'lmadi.", show_alert=True)
        return

    await call.answer("✅ Suhbat so'rovi yuborildi! Javobini kuting.", show_alert=True)

async def para_chat_close_action(user_id: int, bot: Bot, state=None, send_notification: bool = True):
    """Anonim suhbatni ishonchli yopish va Reply klaviaturani o'chirish"""
    from aiogram.types import ReplyKeyboardRemove
    from aiogram.fsm.storage.base import StorageKey
    from aiogram.fsm.context import FSMContext as _FSM

    partner_user_id = None
    if state:
        try:
            data = await state.get_data()
            partner_user_id = data.get("partner_user_id")
        except Exception:
            pass

    if not partner_user_id:
        partner_user_id = active_chats.get(user_id)

    if not partner_user_id:
        try:
            r_partner = await redis_client.get(f"anon_chat:{user_id}")
            if r_partner:
                partner_user_id = int(r_partner)
        except Exception:
            pass

    if not partner_user_id:
        try:
            user = await User.get_or_none(user_id=user_id)
            if user:
                para = await Paralar.filter(user1=user).prefetch_related("user2").first()
                if not para:
                    para = await Paralar.filter(user2=user).prefetch_related("user1").first()
                if para:
                    p_user = para.user2 if para.user1_id == user.id else para.user1
                    if active_chats.get(p_user.user_id) == user_id:
                        partner_user_id = p_user.user_id
        except Exception:
            pass

    # Asosiy foydalanuvchini tozalash
    active_chats.pop(user_id, None)
    try:
        await redis_client.delete(f"anon_chat:{user_id}")
    except Exception:
        pass

    if state:
        try:
            await state.clear()
        except Exception:
            pass
    else:
        try:
            from bot import dp
            u_key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)
            u_state = _FSM(storage=dp.storage, key=u_key)
            await u_state.clear()
        except Exception:
            pass

    if send_notification:
        try:
            await bot.send_message(
                chat_id=user_id,
                text="✅ Suhbat yopildi.",
                reply_markup=ReplyKeyboardRemove()
            )
        except Exception:
            pass

    # Sherikni tozalash
    if partner_user_id:
        active_chats.pop(partner_user_id, None)
        try:
            await redis_client.delete(f"anon_chat:{partner_user_id}")
        except Exception:
            pass

        try:
            storage = state.storage if state else None
            if not storage:
                from bot import dp
                storage = dp.storage
            p_key = StorageKey(bot_id=bot.id, chat_id=partner_user_id, user_id=partner_user_id)
            p_state = _FSM(storage=storage, key=p_key)
            await p_state.clear()
        except Exception:
            pass

        try:
            await bot.send_message(
                chat_id=partner_user_id,
                text="💬 Parangiz suhbatni yopdi.",
                reply_markup=ReplyKeyboardRemove()
            )
        except Exception:
            pass

async def para_chat_respond(call: CallbackQuery, bot: Bot, state, action: str, requester_id: int):
    """Anonim suhbat so'roviga javob: accept yoki decline"""
    user = await User.get_or_none(user_id=call.from_user.id)
    if not user:
        return
    requester = await User.get_or_none(user_id=requester_id)
    if not requester:
        await call.answer("❗ Foydalanuvchi topilmadi.", show_alert=True)
        return

    if action == "decline":
        await call.message.edit_text("❌ Siz suhbat so'rovini rad etdingiz.", parse_mode="HTML")
        try:
            await bot.send_message(
                chat_id=requester.user_id,
                text="❌ Parangiz anonim suhbat so'rovingizni rad etdi.",
                parse_mode="HTML"
            )
        except Exception:
            pass
        return

    from aiogram.fsm.storage.base import StorageKey
    from aiogram.fsm.context import FSMContext as _FSM
    from handlers.paralar import AnonymousChatState

    await state.set_state(AnonymousChatState.chatting)
    await state.update_data(partner_user_id=requester.user_id)

    storage = state.storage
    global _fsm_storage
    _fsm_storage = storage
    req_key = StorageKey(bot_id=bot.id, chat_id=requester.user_id, user_id=requester.user_id)
    req_state = _FSM(storage=storage, key=req_key)
    await req_state.set_state(AnonymousChatState.chatting)
    await req_state.update_data(partner_user_id=user.user_id)

    active_chats[user.user_id] = requester.user_id
    active_chats[requester.user_id] = user.user_id

    try:
        await redis_client.set(f"anon_chat:{user.user_id}", str(requester.user_id), ex=86400)
        await redis_client.set(f"anon_chat:{requester.user_id}", str(user.user_id), ex=86400)
    except Exception:
        pass

    await call.message.edit_reply_markup(reply_markup=None)
    await bot.send_message(
        chat_id=user.user_id,
        text="💬 Anonim suhbat boshlandi! Xabarlaringiz parangizga anonim yetkaziladi.\nYopish uchun pastdagi tugmani bosing.",
        reply_markup=anon_chat_keyboard(),
        parse_mode="HTML"
    )
    try:
        await bot.send_message(
            chat_id=requester.user_id,
            text="💬 Parangiz suhbatni qabul qildi! Xabarlaringiz anonim yetkaziladi.\nYopish uchun pastdagi tugmani bosing.",
            reply_markup=anon_chat_keyboard(),
            parse_mode="HTML"
        )
    except Exception:
        pass

async def para_chat_relay(message: Message, state, bot: Bot):
    """Suhbat jarayonida xabarlarni relay qilish"""
    user_id = message.from_user.id
    text = (message.text or "").strip()

    if text in ["❌ Suhbatni yopish", "/stopchat", "/stop_chat", "/endchat", "/stop", "/cancel", "/close", "/exit"]:
        await para_chat_close_action(user_id=user_id, bot=bot, state=state, send_notification=True)
        return

    # Buyruqlar hech qachon parangizga yuborilmaydi. Ilgari /profile, /start va
    # hatto /dpara ham suhbatga tushib ketardi va odam botdan chiqa olmay qolardi.
    if text.startswith("/"):
        await para_chat_close_action(user_id=user_id, bot=bot, state=state, send_notification=True)
        await message.answer(
            "💬 Anonim suhbat yopildi (buyruq yuborildi).\n"
            f"Endi <b>{text.split()[0]}</b> buyrug'ini qayta yuboring.",
            parse_mode="HTML",
        )
        return

    if state is not None:
        global _fsm_storage
        _fsm_storage = state.storage

    data = await state.get_data() if state else {}
    partner_user_id = data.get("partner_user_id") or active_chats.get(user_id)
    if not partner_user_id:
        try:
            r_partner = await redis_client.get(f"anon_chat:{user_id}")
            if r_partner:
                partner_user_id = int(r_partner)
        except Exception:
            pass

    if not partner_user_id:
        await para_chat_close_action(user_id=user_id, bot=bot, state=state, send_notification=True)
        return

    # Para bekor qilingan bo'lsa, xabar eski juftga ketmasligi kerak.
    if not await _has_active_para(user_id, partner_user_id):
        await force_close_anon_chat(user_id, partner_user_id, bot=bot)
        try:
            from aiogram.types import ReplyKeyboardRemove
            await message.answer(
                "💔 Sizda para yo'q — anonim suhbat yopildi. Xabaringiz hech kimga yuborilmadi.",
                reply_markup=ReplyKeyboardRemove(),
            )
        except Exception:
            pass
        if state:
            try:
                await state.clear()
            except Exception:
                pass
        return

    try:
        await message.copy_to(chat_id=partner_user_id)
    except Exception:
        await message.answer("⚠️ Parangizga xabar yetkazilmadi. Suhbat yopilmoqda...")
        await para_chat_close_action(user_id=user_id, bot=bot, state=state, send_notification=True)