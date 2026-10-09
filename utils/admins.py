import asyncio
from aiogram import Bot
from aiogram.types import Message, CallbackQuery
from models.user import GeroyMarket, User, Blocked_user, Profile, VipUser
from models.game_set import GroupBalance
from keyboards.admin_keyboard import groups_list_button, group_button, back_groups_list_btn
from models.game_data import Chat, Game, GamePlayer, GamePhase, Action, Vote, VoteLike, GazabdorPick
from models.game_data import Geroys
from models.game_set import BlockGrousp
from tortoise.expressions import Q
from config import MAX_PLAYERS, ADMINS, PRIMARY_ADMIN_IDS, MINI_ADMINS_GROUP_IDS, CHANNEL_ID
from tortoise.expressions import Q
from datetime import datetime, timedelta, timezone

GROUPS_PER_PAGE = 15

# VIP giveaway holati: {giveaway_id: {"remaining": N, "total": N, "claimed": set()}}
_vip_giveaways: dict = {}

async def is_bot_admin(user_id: int) -> bool:
    """Config primary adminlar yoki BotAdmin DB adminlari."""
    if not user_id:
        return False
    if user_id in PRIMARY_ADMIN_IDS:
        return True
    try:
        from models.user import BotAdmin
        return await BotAdmin.filter(user_id=user_id).exists()
    except Exception:
        return False

def _vip_giveaway_text(remaining: int, total: int) -> str:
    return (
        f"🎁 <b>VIP Giveaway!</b>\n\n"
        f"Admin <b>{total} ta VIP</b> tarqatyapti!\n"
        f"Birinchi bo'lib bosganlarga VIP beriladi.\n\n"
        f"✅ Qolgan: <b>{remaining}/{total}</b>"
    )

async def distribute_vip_handler(message: Message, bot: Bot):
    """
    /vip <son> - inline tugma bilan foydalanuvchilar bosib VIP oladi
    Faqat bot adminlari ishlatishi mumkin.
    """
    is_channel = message.chat.type == "channel"
    if is_channel and (not CHANNEL_ID or message.chat.id != CHANNEL_ID):
        return
    sender_id = list(PRIMARY_ADMIN_IDS)[0] if is_channel else (message.from_user.id if message.from_user else None)
    if sender_id not in PRIMARY_ADMIN_IDS:
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Format: /vip <son>\nMisol: /vip 10")
        return
    count = int(parts[1])
    if count <= 0 or count > 500:
        await message.answer("❌ Son 1 dan 500 gacha bo'lishi kerak.")
        return

    import time
    giveaway_id = str(int(time.time()))
    _vip_giveaways[giveaway_id] = {"remaining": count, "total": count, "claimed": set()}

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    kb = InlineKeyboardBuilder()
    kb.button(text="🎁 VIP olish", callback_data=f"claim_vip_{giveaway_id}")

    await message.answer(
        _vip_giveaway_text(count, count),
        parse_mode="HTML",
        reply_markup=kb.as_markup()
    )

async def claim_vip_callback(call: CallbackQuery, bot: Bot):
    """Foydalanuvchi 'VIP olish' tugmasini bosganida"""
    giveaway_id = call.data.replace("claim_vip_", "")
    giveaway = _vip_giveaways.get(giveaway_id)

    if not giveaway or giveaway["remaining"] <= 0:
        await call.answer("❌ VIP tugadi!", show_alert=True)
        return

    user_id = call.from_user.id
    if user_id in giveaway["claimed"]:
        await call.answer("⚠️ Siz allaqachon oldingiz!", show_alert=True)
        return

    user, _ = await User.get_or_create(
        user_id=user_id,
        defaults={"full_name": call.from_user.full_name, "mention": call.from_user.mention_html()}
    )
    exists = await VipUser.get_or_none(user=user)
    if exists:
        giveaway["claimed"].add(user_id)
        await call.answer("⚠️ Sizda allaqachon VIP bor!", show_alert=True)
        return

    await VipUser.create(user=user)
    giveaway["claimed"].add(user_id)
    giveaway["remaining"] -= 1

    await call.answer("✅ Tabriklaymiz! Sizga VIP berildi 🎉", show_alert=True)

    total = giveaway["total"]
    remaining = giveaway["remaining"]

    if remaining <= 0:
        _vip_giveaways.pop(giveaway_id, None)
        try:
            await call.message.edit_text(
                f"🎁 <b>VIP Giveaway tugadi!</b>\n\n✅ <b>{total}/{total}</b> ta VIP tarqatildi.",
                parse_mode="HTML"
            )
        except Exception:
            pass
    else:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        kb = InlineKeyboardBuilder()
        kb.button(text="🎁 VIP olish", callback_data=f"claim_vip_{giveaway_id}")
        try:
            await call.message.edit_text(
                _vip_giveaway_text(remaining, total),
                parse_mode="HTML",
                reply_markup=kb.as_markup()
            )
        except Exception:
            pass

async def get_user_chats(user, filter_type: str = "all"):
    """
    Foydalanuvchining qatnashgan barcha guruhlarini (Chat) qaytaradi.
    """
    _tashkent = timezone(timedelta(hours=5))
    now = datetime.now(timezone.utc).astimezone(_tashkent)
    start = None
    end = None

    if filter_type == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

    elif filter_type == "yesterday":
        end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start = end - timedelta(days=1)

    elif filter_type == "this_week":
        start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        end = now + timedelta(days=1)

    elif filter_type == "until_today":
        start = None
        end = now.replace(hour=0, minute=0, second=0, microsecond=0)

    query = Game.filter(players__user=user)

    if start and end:
        query = query.filter(created_at__gte=start, created_at__lt=end)
    elif end:
        query = query.filter(created_at__lt=end)

    games = await query.all()

    if not games:
        return []

    chats = await Chat.filter(games__in=games).distinct()

    return chats
def format_chats(chats):
    if not chats:
        return "— Hech biri yo‘q"
    return "\n".join([f"• {chat.title or chat.id}" for chat in chats])

async def remove_geroy_market_item(message: Message):
    if message.from_user.id not in ADMINS:
        return
    points = message.text.split()
    if len(points) != 2:
        return
    geroy_user_id = int(points[1])
    user = await User.filter(user_id=geroy_user_id).first()
    if not user:
        await message.answer("❌ Bunday foydalanuvchi topilmadi!")
        return
    
    geroy_market_item = await GeroyMarket.filter(user=user).first()
    if not geroy_market_item:
        await message.answer("❌ Bunday geroy market elementi topilmadi!")
        return
    await geroy_market_item.delete()
    await message.answer(f"✅ Geroy market elementi muvaffaqiyatli o'chirildi!")
                         
async def change_profile_answer(message: Message):
    if message.from_user.id not in ADMINS:
        return
    points = message.text.split()
    if len(points) != 3:
        return
    user_id = int(points[1])
    targ_user_id = int(points[2])
    user = await User.get_or_none(user_id=user_id)
    targ_user = await User.get_or_none(user_id=targ_user_id)
    user.user_id = targ_user_id
    targ_user.user_id = user_id
    await user.save()
    await targ_user.save()
    await message.answer(f"{user.full_name} va {targ_user.full_name} profillari almashdirildi!")

async def bust_user_answer(message: Message):
    if not await is_bot_admin(message.from_user.id):
        return
    points = message.text.split()
    if len(points) == 2:
        user_id = int(points[1])
    else:
        if message.reply_to_message:
            user_id = message.reply_to_message.from_user.id
        else:
            return
    user = await User.get_or_none(user_id=user_id)
    profile = await Profile.get_or_none(user=user)
    match points[0][-1]:
        case "1":
            profile.dollar = 0
            await profile.save()
            await message.answer(f"{user.full_name} 💵 hisobi bankrot qilindi!", parse_mode="HTML")
        case "2":
            profile.diamond = 0
            await profile.save()
            await message.answer(f"{user.full_name} <tg-emoji emoji-id='5210941235912552228'>💎</tg-emoji> hisobi bankrot qilindi!", parse_mode="HTML")

async def block_users_lst_answer(message: Message):
    if message.from_user.id not in ADMINS:
        return
    
    blocked_users = await Blocked_user.all().prefetch_related("user")
    if not blocked_users:
        await message.answer("<b>❗️ Hozircha bloklangan foydalanuvchilar yo'q!</b>", parse_mode="HTML")
        return
    
    text = "<b>🚫 Bloklangan foydalanuvchilar ro'yxati:</b>\n\n"
    s = 1
    for blocked_user in blocked_users:
        user = blocked_user.user
        text += f"{s}. {user.full_name if hasattr(user, 'full_name') else user.id} (ID: {user.user_id})\n"
        s += 1
        if len(text) > 4000 and s < len(blocked_users):
            await message.answer(text, parse_mode="HTML")
            text = "<b>🚫 Bloklangan foydalanuvchilar ro'yxati davom etmoqda:</b>\n\n"

    await message.answer(text, parse_mode="HTML")

async def zapravka_olmosh_handler(message: Message):
    if not await is_bot_admin(message.from_user.id):
        return
    import html
    from utils.premium_emojis import get_diamond_display
    
    target_user = message.from_user
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user

    user, _ = await User.get_or_create(
        user_id=target_user.id,
        defaults={"full_name": target_user.full_name, "username": target_user.username}
    )
    profile, _ = await Profile.get_or_create(user=user)
    profile.diamond += 100
    await profile.save()

    d_disp = get_diamond_display()
    if target_user.id == message.from_user.id:
        await message.answer(f"✅ Sizga 100 {d_disp} berildi!", parse_mode="HTML")
    else:
        name = html.escape(target_user.full_name or target_user.username or str(target_user.id))
        await message.answer(f"✅ <b>{name}</b> ga 100 {d_disp} berildi!", parse_mode="HTML")

async def zapravka_dollar_handler(message: Message):
    if not await is_bot_admin(message.from_user.id):
        return
    import html
    from utils.premium_emojis import get_dollar_display

    target_user = message.from_user
    if message.reply_to_message and message.reply_to_message.from_user:
        target_user = message.reply_to_message.from_user

    user, _ = await User.get_or_create(
        user_id=target_user.id,
        defaults={"full_name": target_user.full_name, "username": target_user.username}
    )
    profile, _ = await Profile.get_or_create(user=user)
    profile.dollar += 10000
    await profile.save()

    m_disp = get_dollar_display()
    if target_user.id == message.from_user.id:
        await message.answer(f"✅ Sizga 10 000 {m_disp} berildi!", parse_mode="HTML")
    else:
        name = html.escape(target_user.full_name or target_user.username or str(target_user.id))
        await message.answer(f"✅ <b>{name}</b> ga 10 000 {m_disp} berildi!", parse_mode="HTML")

async def get_vip_users(message: Message):
    if message.from_user.id not in ADMINS:
        return
    vip_users = await VipUser.all().prefetch_related("user")
    if not vip_users:
        await message.answer("❌ VIP foydalanuvchilar topilmadi!")
        return
    text = "<b>🌟 VIP foydalanuvchilar ro'yxati:</b>\n\n"
    i = 0
    for vip in vip_users:
        i += 1
        text += f"{i}. {vip.user.full_name if hasattr(vip.user, 'full_name') else vip.user.user_id} (ID: {vip.user.user_id})\n"
        if len(text) > 4000 and i < len(vip_users):
            await message.answer(text, parse_mode="HTML")
            text = "<b>🌟 VIP foydalanuvchilar ro'yxati davom etmoqda:</b>\n\n"
    await message.answer(text, parse_mode="HTML")

async def block_this_group(message: Message, bot: Bot):
    if message.from_user.id not in ADMINS:
        return
    chat = await Chat.get_or_none(chat_id=message.chat.id)
    if not chat:
        if len(message.text.split()) == 2:
            chat = await Chat.get_or_none(chat_id=message.text.split()[1])
            if not chat:
                await message.answer("❌ Guruh topilmadi!")
                return
        else:
            await message.answer("❌ Guruh topilmadi!")
            return
    await BlockGrousp.create(chat_id=chat.chat_id)
    await message.answer("✅ Guruh muvaffaqiyatli bloklandi!")

async def unblock_this_group(message: Message, bot: Bot):   
    if message.from_user.id not in ADMINS:
        return
    chat = await Chat.get_or_none(chat_id=message.chat.id)
    if not chat:
        if len(message.text.split()) == 2:
            chat = await Chat.get_or_none(chat_id=message.text.split()[1])
            if not chat:
                await message.answer("❌ Guruh topilmadi!")
                return
        else:
            await message.answer("❌ Guruh topilmadi!")
            return
    group_block = await BlockGrousp.get_or_none(chat_id=chat.chat_id)
    if not group_block:
        await message.answer("❌ Guruh bloklanmagan!")
        return
    await group_block.delete()
    await message.answer("✅ Guruh muvaffaqiyatli blokdan chiqarildi!")

async def check_gaming_groups_user(message: Message):
    await message.answer("aniqlanmoqda")
    try:
        args = message.text.strip().split()
        if len(args) < 2 or not args[1].isdigit():
            await message.answer("⚠️ Foydalanish: <code>/yougame &lt;user_id&gt;</code>")
            return

        user_id = int(args[1])
        user = await User.get_or_none(user_id=user_id)
        if not user:
            await message.answer("❌ Bunday foydalanuvchi topilmadi.")
            return

        chats_today = await get_user_chats(user, filter_type="today")
        chats_yesterday = await get_user_chats(user, filter_type="yesterday")
        chats_this_week = await get_user_chats(user, filter_type="this_week")
        chats_until_today = await get_user_chats(user, filter_type="until_today")
        chats_all = await get_user_chats(user)


        today_str = datetime.now(timezone(timedelta(hours=5))).strftime("%d.%m.%Y")

        text = (
            f"👤 <b>Foydalanuvchi:</b> {user.full_name if hasattr(user, 'full_name') else user_id}\n"
            f"📅 <b>Sana:</b> {today_str}\n\n"
            f"🎯 <b>Bugun:</b>\n{format_chats(chats_today)}\n\n"
            f"🌙 <b>Kecha:</b>\n{format_chats(chats_yesterday)}\n\n"
            f"📆 <b>Shu hafta:</b>\n{format_chats(chats_this_week)}\n\n"
            f"⏳ <b>Bugungacha:</b>\n{format_chats(chats_until_today)}\n\n"
            f"🌍 <b>Umuman olganda (barcha guruhlar):</b>\n{format_chats(chats_all)}"
        )

        await message.answer(text, parse_mode="HTML")

    except Exception as e:
        await message.answer(f"⚠️ Xatolik yuz berdi:\n<code>{e}</code>")

async def check_user_full_info(message: Message):
    if message.from_user.id not in ADMINS:
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Foydalanish: /check <ID yoki ism>")
        return

    target = args[1].replace("@", "").strip()

    if target.isdigit():
        user = await User.get_or_none(user_id=int(target))
    else:
        user = await User.filter(Q(full_name__icontains=target) | Q(mention__icontains=target)).first()

    if not user:
        await message.answer("Foydalanuvchi topilmadi.")
        return

    profile = await Profile.get_or_none(user=user)
    vip = await VipUser.get_or_none(user=user)
    blocked = await Blocked_user.get_or_none(user=user)
    geroy = await Geroys.get_or_none(user=user)

    total_games = await GamePlayer.filter(user=user).count()
    wins = await GamePlayer.filter(user=user, win=True).count()

    _tashkent = timezone(timedelta(hours=5))
    now = datetime.now(timezone.utc).astimezone(_tashkent)

    if vip:
        delta = now - vip.created_at.astimezone(_tashkent)
        days_left = 30 - delta.days
        vip_str = f"[VIP {days_left} kun ⭐]" if days_left > 0 else "[VIP tugagan]"
    else:
        vip_str = ""

    ban_str = "Ha 🚫" if blocked else "Yo'q"

    info_text = f"✅ <b>{user.full_name}</b> {vip_str}\n"
    info_text += f"ID: <code>{user.user_id}</code> | Ban: {ban_str}\n\n"

    if profile:
        info_text += f"💵 Dollar: <code>{profile.dollar:,}</code>\n"
        info_text += f"💎 Olmos: <code>{profile.diamond:,}</code>\n\n"

        info_text += f"🛡 Himoya: {profile.himoya}\n"
        info_text += f"📁 Hujjat: {profile.hujjat}\n"
        info_text += f"⚖️ Osishdan himoya: {profile.osishdan_himoya}\n"
        info_text += f"⛑️ Qotildan himoya: {profile.qotildan_himoya}\n"
        info_text += f"🔫 Miltiq: {profile.miltiq}\n"
        info_text += f"💊 Doridan himoya: {profile.doridan_himoya}\n"
        info_text += f"🎭 Maska: {profile.maska}\n"
        info_text += f"🪤 Sirpanishdan himoya: {profile.slip_himoya}\n"
        info_text += f"🔰 Qahramon himoyasi: {profile.geroy_himoya}\n"

    if geroy:
        info_text += f"\n🥷 Geroy: {geroy.name} ({geroy.level}-daraja)\n"

    info_text += "\n📊 Statistika:\n"
    info_text += f"🎯 G'alabalar: {wins}\n"
    info_text += f"🎲 Jami o'yinlar: {total_games}\n"

    from models.user import ActiveRole, Paralar, Transfers
    if profile:
        active_roles = await ActiveRole.filter(profile=profile, is_active=True)
        if active_roles:
            roles_str = ", ".join([ar.role for ar in active_roles])
            info_text += f"\n🃏 Faol rollar: {roles_str}\n"
        else:
            info_text += "\n🃏 Faol rollar: Yo'q\n"
    else:
        info_text += "\n🃏 Faol rollar: Yo'q\n"

    para = await Paralar.filter(Q(user1=user) | Q(user2=user)).first()
    if para:
        partner_id = para.user1_id if para.user2_id == user.id else para.user2_id
        partner = await User.get_or_none(id=partner_id)
        if partner:
            info_text += f"💖 Jufti: {partner.full_name}\n"
        else:
            info_text += "💔 Jufti: Noma'lum\n"
    else:
        info_text += "💔 Jufti yo'q\n"

    await message.answer(info_text, parse_mode="HTML")

    _tashkent = timezone(timedelta(hours=5))

    def to_tashkent(dt_val):
        if dt_val is None:
            return "?"
        if dt_val.tzinfo is None:
            dt_val = dt_val.replace(tzinfo=timezone.utc)
        return dt_val.astimezone(_tashkent).strftime("%d.%m.%y %H:%M")

    transfers_from = await Transfers.filter(from_user=user).prefetch_related('to_user').order_by('-created_at').all()
    transfers_to = await Transfers.filter(to_user=user).prefetch_related('from_user').order_by('-created_at').all()

    if not transfers_from and not transfers_to:
        await message.answer("📜 <b>O'tkazmalar tarixi yo'q</b>", parse_mode="HTML")
        return

    CHUNK = 3500

    async def send_section(header: str, rows: list[str]):
        body = "\n".join(rows)
        text = header + f"<blockquote expandable>{body}</blockquote>"
        for i in range(0, len(text), CHUNK):
            await message.answer(text[i:i+CHUNK], parse_mode="HTML")

    if transfers_from:
        total_dollar = sum(t.amount for t in transfers_from if t.type == "dollar")
        total_diamond = sum(t.amount for t in transfers_from if t.type != "dollar")
        header = (
            f"📤 <b>Yuborgan</b>  —  <b>{len(transfers_from)} ta</b>\n"
            f"<i>Jami: <b>{total_dollar:,} 💵</b>  ·  <b>{total_diamond:,} 💎</b></i>\n\n"
        )
        rows = []
        for i, t in enumerate(transfers_from, 1):
            to_name = (t.to_user.full_name or "?") if t.to_user else "?"
            to_id = t.to_user.user_id if t.to_user else "?"
            icon = "💵" if t.type == "dollar" else "💎"
            dt = to_tashkent(t.created_at)
            rows.append(f"{i}. ➖ {t.amount:,} {icon}  →  {to_name}  [{to_id}]  {dt}")
        await send_section(header, rows)

    if transfers_to:
        total_dollar = sum(t.amount for t in transfers_to if t.type == "dollar")
        total_diamond = sum(t.amount for t in transfers_to if t.type != "dollar")
        header = (
            f"📥 <b>Qabul qilgan</b>  —  <b>{len(transfers_to)} ta</b>\n"
            f"<i>Jami: <b>{total_dollar:,} 💵</b>  ·  <b>{total_diamond:,} 💎</b></i>\n\n"
        )
        rows = []
        for i, t in enumerate(transfers_to, 1):
            from_name = (t.from_user.full_name or "?") if t.from_user else "?"
            from_id = t.from_user.user_id if t.from_user else "?"
            icon = "💵" if t.type == "dollar" else "💎"
            dt = to_tashkent(t.created_at)
            rows.append(f"{i}. ➕ {t.amount:,} {icon}  ←  {from_name}  [{from_id}]  {dt}")
        await send_section(header, rows)

async def check_user_exists(message: Message):
    user_id = message.text.split()[1] if len(message.text.split()) > 1 else message.from_user.id
    if message.from_user.id not in ADMINS:
        if message.chat.id != MINI_ADMINS_GROUP_IDS:
            return
    users = await User.filter(user_id=user_id)
    if not users:
        await message.answer("❌ Foydalanuvchi topilmadi!")
        return
    if len(users) > 1:
        for user in users[1:]:
            await user.delete()
        await message.answer(f"🗑️ {len(users)-1} ta duplicate foydalanuvchi o'chirildi!")
    else:
        await message.answer("✅ Duplicate foydalanuvchi topilmadi.")
    
    profiles = await Profile.filter(user=users[0])
    if not profiles:
        await message.answer("❌ Foydalanuvchi profili topilmadi!")
    elif len(profiles) > 1:
        for profile in profiles[1:]:
            await profile.delete()
        await message.answer(f"🗑️ {len(profiles)-1} ta duplicate profil o'chirildi!")
    else:
        await message.answer("✅ Duplicate profil topilmadi.")
    
    players = await GamePlayer.filter(user=users[0], is_alive=True)
    if not players:
        await message.answer("🎮 Foydalanuvchi o'yinlarda ishtirok etmayapti!")
    elif len(players) > 0:
        for player in players[:]:
            await player.delete()
        await message.answer(f"🗑️ {len(players)} ta o'yin ishtirokchisi o'chirildi!")
    else:
        await message.answer("✅ O'yin ishtirokchisi topilmadi.")

async def stop_all_games_handler(message: Message, bot: Bot):
    if message.from_user.id not in ADMINS: return
    active_games = await Game.filter(is_active=True).prefetch_related("chat").all()
    if not active_games:
        await message.answer("🚫 Faol o'yinlar topilmadi!")
        return
    failed_games = 0
    stoped_games = 0
    msg = await message.answer("🛑 Faol o'yinlar to'xtatilyapti...")
    caption = message.text.split("/stopgames")[1] if message.text.split("/stopgames") else ""
    for game in active_games:
        try:
            game.is_active = False
            game.phase = "end"
            await game.save()

            await GamePlayer.filter(game=game).delete()
            await GamePhase.filter(game=game).delete()

            await bot.send_message(game.chat.chat_id, f"🛑 O'yin admin tomonidan to'xtatildi!\n\n{caption}")
            stoped_games += 1
            await msg.edit_text(f"🛑 {stoped_games} ta o'yin to'xtatildi.\n❌ {failed_games} ta o'yin to'xtatilmadi.")
            await asyncio.sleep(0.3)
        except Exception as e:
            failed_games += 1
            await msg.edit_text(f"🛑 {stoped_games} ta o'yin to'xtatildi.\n❌ {failed_games} ta o'yin to'xtatilmadi.\n\nXato: {e}")
            await asyncio.sleep(0.3)
    await message.answer(f"✅ {len(active_games) - failed_games} ta faol o'yin muvaffaqiyatli to'xtatildi!\n\n{failed_games} ta o'yin to'xtatilmadi.")

async def get_chat_id(message: Message):
    if message.from_user.id in ADMINS:
        await message.answer(f"Chat ID: {message.chat.id}")

async def block_user_answer(message: Message):
    if not await is_bot_admin(message.from_user.id):
        return
    user_id = None
    parts = (message.text or "").strip().split()
    if len(parts) >= 2 and parts[1].lstrip("-").isdigit():
        user_id = int(parts[1])
    elif message.reply_to_message and message.reply_to_message.from_user:
        user_id = message.reply_to_message.from_user.id
    
    if not user_id:
        await message.answer("ℹ️ <b>Foydalanish:</b> <code>/ban 123456789</code> yoki foydalanuvchi xabariga reply qilib <code>/ban</code>", parse_mode="HTML")
        return
    
    user = await User.get_or_none(user_id=user_id)
    if not user:
        clean_name = f"User_{user_id}"
        mention = f"<code>{user_id}</code>"
        user = await User.create(user_id=user_id, full_name=clean_name, mention=mention)
        await Blocked_user.create(user=user)
        await message.answer("<b>⚠️ Foydalanuvchi bazada topilmadi! Oldindan ban qilindi!</b>", parse_mode="HTML")
        return

    user_is_blocked = await Blocked_user.filter(user=user).first()
    if user_is_blocked:
        await message.answer("<b>❗️ Foydalanuvchi allaqachon bloklangan!</b>", parse_mode="HTML")
        return
    
    await Blocked_user.create(user=user)
    await message.answer(f"<b>✅ {user_id} foydalanuvchisi botda bloklandi (ban qilindi)!</b>", parse_mode="HTML")

async def unblock_user_answer(message: Message):
    if not await is_bot_admin(message.from_user.id):
        return
    user_id = None
    parts = (message.text or "").strip().split()
    if len(parts) >= 2 and parts[1].lstrip("-").isdigit():
        user_id = int(parts[1])
    elif message.reply_to_message and message.reply_to_message.from_user:
        user_id = message.reply_to_message.from_user.id
    
    if not user_id:
        await message.answer("ℹ️ <b>Foydalanish:</b> <code>/unban 123456789</code> yoki foydalanuvchi xabariga reply qilib <code>/unban</code>", parse_mode="HTML")
        return
    
    user = await User.get_or_none(user_id=user_id)
    if not user:
        await message.answer("⚠️ Foydalanuvchi bazada topilmadi!", parse_mode="HTML")
        return

    user_is_blocked = await Blocked_user.filter(user=user).first()
    if not user_is_blocked:
        await message.answer("<b>❗️ Foydalanuvchi bloklanmagan!</b>", parse_mode="HTML")
        return
    
    await user_is_blocked.delete()
    await message.answer(f"<b>✅ {user_id} foydalanuvchisidan blok (ban) olib tashlandi!</b>", parse_mode="HTML")

async def get_all_bot_admins():
    """Barcha config va DB dynamic adminlar ro'yxatini User ob'yektlari shaklida qaytaradi."""
    from models.user import User, BotAdmin
    from config import PRIMARY_ADMIN_IDS

    admin_ids = set(PRIMARY_ADMIN_IDS)
    try:
        db_admins = await BotAdmin.all().values_list("user_id", flat=True)
        for aid in db_admins:
            if aid:
                admin_ids.add(int(aid))
    except Exception:
        pass

    users = []
    for uid in admin_ids:
        user = await User.get_or_none(user_id=uid)
        if not user:
            user = User(user_id=uid, full_name=f"Admin_{uid}", username=None)
        users.append(user)
    return users

async def add_admin_answer(message: Message):
    """/addadmin <user_id> - yangi tayinlangan admin qo'shish (faqat PRIMARY_ADMIN_IDS)"""
    if message.from_user.id not in PRIMARY_ADMIN_IDS:
        return

    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("<b>Format:</b> <code>/addadmin <user_id></code>", parse_mode="HTML")
        return

    target_id = int(parts[1])
    from models.user import BotAdmin, User
    user, _ = await User.get_or_create(
        user_id=target_id,
        defaults={"full_name": f"Admin_{target_id}", "mention": f"<code>{target_id}</code>"}
    )
    already = await BotAdmin.filter(user_id=target_id).exists()
    if already or target_id in PRIMARY_ADMIN_IDS:
        await message.answer(f"⚠️ <code>{target_id}</code> allaqachon adminlar ro'yxatida mavjud!", parse_mode="HTML")
        return

    await BotAdmin.create(user_id=target_id)
    await message.answer(
        f"✅ <code>{target_id}</code> foydalanuvchisi yangi tayinlangan adminlar ro'yxatiga qo'shildi!\n"
        f"<i>(Eslatma: Ushbu adminga /admin va /panel buyruqlari ishlamaydi, boshqa admin buyruqlari ishlaydi)</i>",
        parse_mode="HTML"
    )

async def show_admins_list(event, page: int = 0):
    """/admins buyrug'i va tugmasi uchun adminlar ro'yxati"""
    user_id = event.from_user.id if event.from_user else None
    if not await is_bot_admin(user_id):
        if isinstance(event, CallbackQuery):
            await event.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    admins_list = await get_all_bot_admins()
    if not admins_list:
        text = "<b>👑 BOT ADMINLARI RO'YXATI</b>\n━━━━━━━━━━━━━━━━━━━━━━\n<i>Hozircha adminlar yo'q.</i>"
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text, parse_mode="HTML")
            await event.answer()
        else:
            await event.answer(text, parse_mode="HTML")
        return

    ITEMS_PER_PAGE = 8
    total_pages = (len(admins_list) - 1) // ITEMS_PER_PAGE + 1
    page = max(0, min(page, total_pages - 1))
    current_page = admins_list[page * ITEMS_PER_PAGE : (page + 1) * ITEMS_PER_PAGE]

    lines = []
    for i, u in enumerate(current_page, start=page * ITEMS_PER_PAGE + 1):
        uname = f"@{u.username}" if u.username else "username yo'q"
        name = u.full_name or f"Admin_{u.user_id}"
        lines.append(f"{i}. <b>{name}</b> ({uname}) — <code>{u.user_id}</code>")

    text = (
        f"<b>👑 BOT ADMINLARI RO'YXATI</b> ({page + 1}/{total_pages})\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Jami: {len(admins_list)} ta admin</i>\n\n"
        + "\n".join(lines) + "\n\n"
        f"<i>Tafsilotlarini ko'rish yoki boshqarish uchun admin ustiga bosing:</i>"
    )

    from keyboards.admin_keyboard import admin_list_keyboard
    kb = admin_list_keyboard(current_page, page, total_pages)

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML", reply_markup=kb)

async def show_admin_detail(call: CallbackQuery, target_id: int):
    """Admin haqida ma'lumot va boshqaruv tugmalari"""
    if not await is_bot_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    user = await User.get_or_none(user_id=target_id)
    name = user.full_name if user else f"Admin_{target_id}"
    uname = f"@{user.username}" if (user and user.username) else "username yo'q"

    from models.user import BotAdmin
    is_dynamic = bool(await BotAdmin.filter(user_id=target_id).exists())
    from config import ADMINS, PRIMARY_ADMIN_IDS, PRIMARY_ADMIN_ID
    is_static = target_id in set(ADMINS) or target_id in set(PRIMARY_ADMIN_IDS) or target_id == PRIMARY_ADMIN_ID

    admin_type = "Asosiy (config.py)" if is_static else ("Tayinlangan (BotAdmin DB)" if is_dynamic else "Boshqa")

    text = (
        f"👑 <b>ADMIN MA'LUMOTLARI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"• <b>Ismi:</b> {name}\n"
        f"• <b>Username:</b> {uname}\n"
        f"• <b>User ID:</b> <code>{target_id}</code>\n"
        f"• <b>Maqomi:</b> {admin_type}\n\n"
        f"<i>Amalni tanlang:</i>"
    )

    from keyboards.admin_keyboard import admin_single_manage_kb
    kb = admin_single_manage_kb(target_id)
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()

async def remove_bot_admin_handler(call: CallbackQuery, target_id: int):
    if not await is_bot_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    from config import PRIMARY_ADMIN_ID, PRIMARY_ADMIN_IDS
    if target_id == PRIMARY_ADMIN_ID or target_id in PRIMARY_ADMIN_IDS:
        await call.answer("⚠️ Asosiy bosh adminni olib tashlab bo'lmaydi!", show_alert=True)
        return

    from models.user import BotAdmin
    bot_adm = await BotAdmin.filter(user_id=target_id).first()
    if bot_adm:
        await bot_adm.delete()
        await call.answer("✅ Adminlikdan olindi!", show_alert=True)
    else:
        from config import ADMINS
        if target_id in ADMINS:
            await call.answer("⚠️ Bu admin config.py faylida ko'rsatilgan asosiy admin, uni DB orqali o'chirib bo'lmaydi!", show_alert=True)
            return
        await call.answer("⚠️ Ushbu admin topilmadi!", show_alert=True)

    await show_admins_list(call, page=0)

async def ban_bot_admin_handler(call: CallbackQuery, target_id: int):
    if not await is_bot_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    from config import PRIMARY_ADMIN_ID, PRIMARY_ADMIN_IDS
    if target_id == PRIMARY_ADMIN_ID or target_id in PRIMARY_ADMIN_IDS:
        await call.answer("❌ Asosiy bosh adminni ban qilib bo'lmaydi!", show_alert=True)
        return

    from models.user import BotAdmin, Blocked_user
    await BotAdmin.filter(user_id=target_id).delete()

    user, _ = await User.get_or_create(
        user_id=target_id,
        defaults={"full_name": f"User_{target_id}", "mention": f"<code>{target_id}</code>"}
    )
    user_blocked = await Blocked_user.filter(user=user).first()
    if not user_blocked:
        await Blocked_user.create(user=user)

    await call.answer("🚫 Admin ban qilindi va adminlikdan olindi!", show_alert=True)
    await show_admins_list(call, page=0)

async def show_blocked_list(event, page: int = 0):
    """Banlanganlar ro'yxati (paginatsiya bilan)"""
    user_id = event.from_user.id if event.from_user else None
    if not await is_bot_admin(user_id):
        if isinstance(event, CallbackQuery):
            await event.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    blocked_users = await Blocked_user.all().prefetch_related("user").order_by("-id")

    from keyboards.admin_keyboard import blocked_list_keyboard

    if not blocked_users:
        text = (
            "<b>🚫 BAN QILINGAN FOYDALANUVCHILAR</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Hozirda ban qilingan foydalanuvchilar yo'q.</i>"
        )
        kb = blocked_list_keyboard(0, 1)
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
            await event.answer()
        else:
            await event.answer(text, parse_mode="HTML", reply_markup=kb)
        return

    ITEMS_PER_PAGE = 10
    total_pages = (len(blocked_users) - 1) // ITEMS_PER_PAGE + 1
    page = max(0, min(page, total_pages - 1))
    current_page = blocked_users[page * ITEMS_PER_PAGE : (page + 1) * ITEMS_PER_PAGE]

    lines = []
    for i, record in enumerate(current_page, start=page * ITEMS_PER_PAGE + 1):
        u = record.user
        name = u.full_name or "Foydalanuvchi"
        uname = f"@{u.username}" if (u and u.username) else "username yo'q"
        lines.append(f"{i}. {name} {uname} <code>{u.user_id}</code>")

    text = (
        f"<b>🚫 BAN QILINGAN FOYDALANUVCHILAR</b> ({page + 1}/{total_pages})\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Jami: {len(blocked_users)} ta foydalanuvchi</i>\n\n"
        + "\n".join(lines)
    )

    kb = blocked_list_keyboard(page, total_pages)

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML", reply_markup=kb)

async def bust_group_balance(message: Message):
    if message.from_user.id not in ADMINS: return
    if len(message.text.split()) == 2: chat_id = int(message.text.split()[1])
    else: chat_id = message.chat.id

    group_balance = await GroupBalance.get_or_none(chat_id=chat_id)
    if group_balance:
        group_balance.balance = 0
        # Faqat balance maydonini yangilash (updated_at timezone muammosini oldini olish)
        await group_balance.save(update_fields=['balance'])
        await message.answer(f"💰 Guruh bankrot qilindi!")
    else: 
        await message.answer("💰 Guruh topilmadi!")

async def set_group_real_money(message: Message):
    if message.from_user.id not in PRIMARY_ADMIN_IDS:
        return
    
    parts = message.text.strip().split()
    if len(parts) == 2:
        # /setmoney <amount> in group
        if not parts[1].lstrip('-').isdigit():
            await message.answer("❗ Foydalanish: <code>/setmoney &lt;miqdor&gt;</code> yoki <code>/setmoney &lt;chat_id&gt; &lt;miqdor&gt;</code>", parse_mode="HTML")
            return
        chat_id = message.chat.id
        amount = int(parts[1])
    elif len(parts) == 3:
        # /setmoney <chat_id> <amount>
        try:
            chat_id = int(parts[1])
            amount = int(parts[2])
        except ValueError:
            await message.answer("❗ Foydalanish: <code>/setmoney &lt;chat_id&gt; &lt;miqdor&gt;</code>", parse_mode="HTML")
            return
    else:
        await message.answer("❗ Foydalanish: <code>/setmoney &lt;miqdor&gt;</code> (guruhda) yoki <code>/setmoney &lt;chat_id&gt; &lt;miqdor&gt;</code>", parse_mode="HTML")
        return

    group_balance, _ = await GroupBalance.get_or_create(chat_id=chat_id)
    group_balance.real_money = amount
    await group_balance.save(update_fields=['real_money'])
    try:
        await message.answer(f"Guruh hisobiga {amount}$ kiritildi. Premium guruhlar qatoriga kirib ko'rishingiz mumkin", parse_mode="HTML")
    except Exception:
        try:
            await message.bot.send_message(chat_id=message.chat.id, text=f"Guruh hisobiga {amount}$ kiritildi. Premium guruhlar qatoriga kirib ko'rishingiz mumkin", parse_mode="HTML")
        except Exception:
            pass

async def get_geroys_list(message: Message):
    if message.from_user.id not in ADMINS: return
    geroys = await Geroys.all().prefetch_related("user").order_by("level")
    if not geroys:
        await message.answer("🥷 Geroylar topilmadi!")
        return
    text = "<b>🥷 Geroylar ro'yxati:</b>\n\n"
    i = 0
    for geroy in geroys:
        i += 1
        text += f"{i}. 🥷 Geroy: {geroy.name}\n⭐️ Daraja: {geroy.level}\n👤 Egas: {geroy.user.mention}\n\n"
        if len(text) > 4000 and i < len(geroys):
            await message.answer(text, parse_mode="HTML")
            text = "<b>🥷 Geroylar ro'yxati davom etmoqda:</b>\n\n"
    await message.answer(text, parse_mode="HTML")

async def get_groups_list(message: Message, page: int = 0):
    if message.chat.type != "private" or message.from_user.id not in ADMINS:
        return

    chats = await Chat.exclude(Q(invite_link="") | Q(invite_link=None))
    chats = list(chats)
    total_pages = (len(chats) - 1) // GROUPS_PER_PAGE + 1

    start = page * GROUPS_PER_PAGE
    end = start + GROUPS_PER_PAGE
    current_page_chats = chats[start:end]

    markup = await groups_list_button(current_page_chats, page, total_pages)
    await message.answer(f"<b>Guruhlar ro'yxati ({page+1}/{total_pages})\nJami: {len(chats)} ta guruh</b>", reply_markup=markup, parse_mode="HTML")
    await message.delete()

async def block_the_group(call: CallbackQuery, bot: Bot):
    if call.from_user.id not in ADMINS:
        return
    try:
        chat_id = int(call.data.split("_")[2])
    except (IndexError, ValueError):
        return

    chat = await Chat.get_or_none(chat_id=int(chat_id))
    if not chat:
        return

    await chat.delete()
    try:
        await bot.leave_chat(chat=int(chat_id))
    except Exception as e:
        pass
    await call.message.edit_text(f"Guruh muvaffaqiyatli o'chirildi: {chat.title}", reply_markup=back_groups_list_btn())
    await call.answer()

async def get_group_info(call: CallbackQuery, bot: Bot):
    if call.from_user.id not in ADMINS:
        return

    try:
        chat_id = int(call.data.split("_")[2])
    except (IndexError, ValueError):
        return

    chat = await Chat.get_or_none(chat_id=chat_id)
    if not chat:
        return

    try:
        members_count = await bot.get_chat_member_count(chat.chat_id)
    except:
        members_count = "Noma'lum"

    games_count = await Game.filter(chat=chat).count()

    last_game = await Game.filter(chat=chat).order_by("-id").first()
    if last_game:
        game_status = last_game.phase
        status_text = {
            "waiting": "⏳ Boshlanmoqda",
            "night": "🌙 Tunda",
            "day": "🌞 Kunduzi",
            "end": "🛑 Tugagan"
        }.get(game_status, "❓ Noma'lum")
    else:
        status_text = "🚫 O‘yinlar hali bo‘lmagan"

    text = (
        f"<b>📋 Guruh haqida:</b>\n"
        f"• Nomi: <b>{chat.title}</b>\n"
        f"• A'zolar soni: <b>{members_count}</b>\n"
        f"• O‘yinlar soni: <b>{games_count}</b>\n"
        f"• Oxirgi o‘yinning holati: <b>{status_text}</b>"
    )

    markup = await group_button(chat.invite_link, chat.chat_id)

    await call.message.delete()
    await call.message.answer(text, reply_markup=markup, parse_mode="HTML")

async def paginate_groups_list(call: CallbackQuery, bot: Bot):
    if call.from_user.id not in ADMINS:
        return

    try:
        page = int(call.data.split("_")[-1])
    except ValueError:
        page = 0

    await get_groups_list_from_callback(call, page=page)

async def get_groups_list_from_callback(call: CallbackQuery, page: int = 0):
    chats = await Chat.exclude(Q(invite_link="") | Q(invite_link=None))
    chats = list(chats)
    total_pages = (len(chats) - 1) // GROUPS_PER_PAGE + 1

    start = page * GROUPS_PER_PAGE
    end = start + GROUPS_PER_PAGE
    current_page_chats = chats[start:end]

    markup = await groups_list_button(current_page_chats, page, total_pages)
    await call.message.edit_text(f"Guruhlar ro'yxati ({page+1}/{total_pages})", reply_markup=markup)

async def back_groups_list(call: CallbackQuery, bot: Bot, page: int = 0):
    chats = await Chat.exclude(Q(invite_link="") | Q(invite_link=None))
    chats = list(chats)
    total_pages = (len(chats) - 1) // GROUPS_PER_PAGE + 1

    start = page * GROUPS_PER_PAGE
    end = start + GROUPS_PER_PAGE
    current_page_chats = chats[start:end]

    markup = await groups_list_button(current_page_chats, page, total_pages)
    await call.message.answer(f"Guruhlar ro'yxati ({page+1}/{total_pages})", reply_markup=markup)
    await call.message.delete()

async def find_active_game(message: Message):
    if message.chat.type != "private": return
    if message.from_user.id not in ADMINS: return
    game = await Game.filter(is_active=True, phase__not="waiting").first()
    if not game:
        await message.answer("Hozirda faol o'yin mavjud emas.")
        return
    await game.fetch_related("chat")
    players = await GamePlayer.filter(game=game, is_alive=True).all()
    await message.answer(f"Faol o'yin topildi: {game.chat.title} - {len(players)} ta ishtirokchi",)

async def find_group_by_name(message: Message):
    if message.chat.type != "private": return
    if message.from_user.id not in ADMINS: return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Iltimos, guruh nomini kiriting.")
        return
    group_name = " ".join(args[1:]).strip().lower()
    chats = await Chat.exclude(Q(invite_link="") | Q(invite_link=None))
    matched_chats = [chat for chat in chats if chat.title and group_name in chat.title.lower()]
    if not matched_chats:
        await message.answer("Hech qanday guruh topilmadi.")
        return
    text = "<b>Topilgan guruhlar:</b>\n\n"
    for chat in matched_chats:
        text += f"• {chat.title} (ID: {chat.chat_id})\n{chat.invite_link}\n\n"
    await message.answer(text, parse_mode="HTML")

async def take_vip_handler(message: Message, bot: Bot):
    """
    /takevip [user_id / @username] yoki xabarga reply qilib:
    Foydalanuvchidan VIP maqomini bekor qilish.
    """
    sender_id = message.from_user.id if message.from_user else None
    if sender_id not in ADMINS and sender_id not in PRIMARY_ADMIN_IDS:
        return

    target_user = None
    
    # 1. Reply qilingan bo'lsa
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
        if len(parts) < 2:
            await message.answer(
                "ℹ️ <b>Foydalanish:</b>\n"
                "• Foydalanuvchi xabariga javoban: <code>/takevip</code>\n"
                "• ID orqali: <code>/takevip 123456789</code>\n"
                "• Username orqali: <code>/takevip @username</code>",
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
                target_user = await User.filter(username=clean_un).first()

    if not target_user:
        await message.answer("❌ Bunday foydalanuvchi topilmadi!", parse_mode="HTML")
        return

    vip = await VipUser.filter(user=target_user).first()
    if not vip:
        await message.answer(
            f"⚠️ <b>{target_user.full_name}</b> (<code>{target_user.user_id}</code>) da VIP maqomi mavjud emas.",
            parse_mode="HTML"
        )
        return

    await vip.delete()
    await message.answer(
        f"✅ <b>{target_user.full_name}</b> (<code>{target_user.user_id}</code>) dan VIP maqomi muvaffaqiyatli olib tashlandi!",
        parse_mode="HTML"
    )
    try:
        await bot.send_message(
            chat_id=target_user.user_id,
            text="ℹ️ Sizning VIP maqomingiz admin tomonidan bekor qilindi."
        )
    except Exception:
        pass

async def give_vip_handler(message: Message, bot: Bot):
    """
    /givevip [user_id / @username] [kunlar (default: 30)] yoki xabarga reply qilib:
    Foydalanuvchiga VIP maqomini berish.
    """
    sender_id = message.from_user.id if message.from_user else None
    if sender_id not in ADMINS and sender_id not in PRIMARY_ADMIN_IDS:
        return

    target_user = None
    days = 30

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
        parts = message.text.strip().split()
        if len(parts) >= 2 and parts[1].isdigit():
            days = int(parts[1])
    else:
        parts = message.text.strip().split()
        if len(parts) < 2:
            await message.answer(
                "ℹ️ <b>Foydalanish:</b>\n"
                "• Foydalanuvchi xabariga javoban: <code>/givevip [kun]</code>\n"
                "• ID orqali: <code>/givevip 123456789 30</code>\n"
                "• Username orqali: <code>/givevip @username 30</code>",
                parse_mode="HTML"
            )
            return

        arg = parts[1].strip()
        if len(parts) >= 3 and parts[2].isdigit():
            days = int(parts[2])

        if arg.isdigit():
            target_uid = int(arg)
            target_user = await User.filter(user_id=target_uid).first()
        else:
            clean_un = arg.lstrip("@").lower()
            target_user = await User.filter(username__iexact=clean_un).first()

    if not target_user:
        await message.answer("❌ Bunday foydalanuvchi topilmadi!", parse_mode="HTML")
        return

    existing_vip = await VipUser.filter(user=target_user).first()
    if existing_vip:
        existing_vip.duration_days = (existing_vip.duration_days or 30) + days
        await existing_vip.save()
        await message.answer(
            f"✅ <b>{target_user.full_name}</b> (<code>{target_user.user_id}</code>) ning VIP muddati +{days} kunga uzaytirildi!",
            parse_mode="HTML"
        )
    else:
        await VipUser.create(user=target_user, duration_days=days)
        await message.answer(
            f"✅ <b>{target_user.full_name}</b> (<code>{target_user.user_id}</code>) ga <b>{days} kunlik</b> VIP maqomi berildi! ⭐",
            parse_mode="HTML"
        )

    try:
        await bot.send_message(
            chat_id=target_user.user_id,
            text=f"🎉 Tabriklaymiz! Sizga admin tomonidan <b>{days} kunlik VIP</b> maqomi taqdim etildi! ⭐",
            parse_mode="HTML"
        )
    except Exception:
        pass


async def add_bot_admin_handler(message: Message):
    """Adminlar faqat variables orqali boshqarilishi haqida xabar berish."""
    await message.answer("⚠️ Adminlar faqat konfiguratsiya (variables) orqali boshqariladi.", parse_mode="HTML")


async def del_bot_admin_handler(message: Message):
    """Adminlar faqat variables orqali boshqarilishi haqida xabar berish."""
    await message.answer("⚠️ Adminlar faqat konfiguratsiya (variables) orqali boshqariladi.", parse_mode="HTML")


async def list_bot_admins_handler(message: Message):
    """Barcha bot adminlari ro'yxatini ko'rsatish (faqat variables static adminlar)."""
    lines = ["👑 <b>BOT ADMINLARI RO'YXATI:</b>\n"]
    lines.append("<b>📌 Asosiy adminlar (variables):</b>")
    for a_id in set(ADMINS + list(PRIMARY_ADMIN_IDS)):
        lines.append(f"• <code>{a_id}</code>")

    await message.answer("\n".join(lines), parse_mode="HTML")


async def del_vip_handler(message: Message):
    """Foydalanuvchining VIP statusini olib tashlash."""
    target_uid = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target_uid = message.reply_to_message.from_user.id
    else:
        parts = message.text.strip().split()
        if len(parts) >= 2 and parts[1].lstrip("-").isdigit():
            target_uid = int(parts[1])

    if not target_uid:
        await message.answer("ℹ️ Foydalanish: <code>/delvip 123456789</code> yoki reply qilgan holda <code>/delvip</code>", parse_mode="HTML")
        return

    user = await User.filter(user_id=target_uid).first()
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi!", parse_mode="HTML")
        return

    deleted = await VipUser.filter(user=user).delete()
    if deleted:
        await message.answer(f"❌ <b>{user.full_name}</b> (<code>{target_uid}</code>) dan VIP status olib tashlandi.", parse_mode="HTML")
    else:
        await message.answer("⚠️ Foydalanuvchida VIP status mavjud emas.", parse_mode="HTML")