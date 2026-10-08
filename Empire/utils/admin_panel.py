import asyncio
from datetime import datetime, timezone, timedelta
from aiogram import Bot
from aiogram.types import Message, CallbackQuery
from tortoise.functions import Sum, Count
from models.user import User, Profile, VipUser, Blocked_user, AdminGiveLog
from models.game_data import Chat, Game, GamePlayer, GamePhase
from models.game_set import GroupBalance, BlockGrousp
from keyboards.admin_keyboard import (
    admin_main_menu, admin_users_menu_kb, admin_user_manage_kb,
    admin_games_menu_kb, admin_broadcast_menu_kb, admin_vip_menu_kb,
    admin_logs_menu_kb, admin_back_btn
)
from config import ADMINS, PRIMARY_ADMIN_IDS

def is_admin(user_id: int) -> bool:
    return user_id in PRIMARY_ADMIN_IDS

async def get_admin_dashboard_text() -> str:
    """Admin panel asosiy statistikasi va holati"""
    tashkent = timezone(timedelta(hours=5))
    now = datetime.now(timezone.utc).astimezone(tashkent)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_users = await User.all().count()
    total_chats = await Chat.all().count()
    active_games = await Game.filter(is_active=True).count()
    today_games = await Game.filter(created_at__gte=today_start).count()
    
    total_vip = await VipUser.all().count()
    total_blocked = await Blocked_user.all().count()

    # Balanslar statistikasi
    money_sum = await Profile.all().annotate(total=Sum("dollar")).values("total")
    diamond_sum = await Profile.all().annotate(total=Sum("diamond")).values("total")
    group_diamond_sum = await GroupBalance.all().annotate(total=Sum("balance")).values("total")

    user_money = money_sum[0]["total"] if money_sum and money_sum[0]["total"] else 0
    user_diamond = diamond_sum[0]["total"] if diamond_sum and diamond_sum[0]["total"] else 0
    grp_diamond = group_diamond_sum[0]["total"] if group_diamond_sum and group_diamond_sum[0]["total"] else 0

    text = (
        "👑 <b>ADMINSTRATOR BOSHQARUV PANELI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📊 <b>Umumiy ko'rsatkichlar:</b>\n"
        f"• 👤 <b>Jami foydalanuvchilar:</b> <code>{total_users:,}</code> ta\n"
        f"• 💬 <b>Jami guruhlar:</b> <code>{total_chats:,}</code> ta\n"
        f"• 🎮 <b>Hozir faol o'yinlar:</b> <code>{active_games}</code> ta\n"
        f"• 📅 <b>Bugungi o'yinlar:</b> <code>{today_games}</code> ta\n"
        f"• 👑 <b>VIP a'zolar:</b> <code>{total_vip}</code> ta\n"
        f"• 🚫 <b>Bloklanganlar:</b> <code>{total_blocked}</code> ta\n\n"
        "💰 <b>Moliyaviy ko'rsatkichlar:</b>\n"
        f"• 💵 <b>Foydalanuvchilar pullari:</b> <code>${user_money:,.0f}</code>\n"
        f"• 💎 <b>Foydalanuvchilar olmoslari:</b> <code>{user_diamond:,}</code> 💎\n"
        f"• 💍 <b>Guruhlar olmoslari:</b> <code>{grp_diamond:,}</code> 💎\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Kerakli bo'limni tanlang:</i>"
    )
    return text

async def show_admin_dashboard(event: Message | CallbackQuery):
    """Admin panelni ochish yoki yangilash"""
    user_id = event.from_user.id
    if not is_admin(user_id):
        if isinstance(event, CallbackQuery):
            await event.answer("❌ Siz bot admini emassiz!", show_alert=True)
        else:
            await event.answer("❌ Siz bot admini emassiz!")
        return

    text = await get_admin_dashboard_text()
    reply_markup = admin_main_menu()

    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
        except Exception:
            await event.message.answer(text, parse_mode="HTML", reply_markup=reply_markup)
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML", reply_markup=reply_markup)

async def get_user_manage_info(user_id: int):
    """Foydalanuvchi haqida to'liq kartochka matni va tugmalarini qaytaradi"""
    user = await User.get_or_none(user_id=user_id)
    if not user:
        return None, None

    profile, _ = await Profile.get_or_create(user=user)
    is_vip = await VipUser.exists(user=user)
    is_blocked = await Blocked_user.exists(user=user)

    total_games = await GamePlayer.filter(user=user).count()
    wins = await GamePlayer.filter(user=user, win=True).count()

    vip_str = "✅ Bor (Aktiv)" if is_vip else "❌ Yo'q"
    block_str = "🚫 Bloklangan" if is_blocked else "✅ Toza (Faol)"

    text = (
        f"👤 <b>Foydalanuvchi ma'lumotlari:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"• <b>Ism:</b> {user.full_name}\n"
        f"• <b>ID:</b> <code>{user.user_id}</code>\n"
        f"• <b>Username:</b> @{user.username if user.username else 'yoq'}\n"
        f"• <b>Holat:</b> {block_str}\n"
        f"• <b>VIP status:</b> {vip_str}\n\n"
        f"💰 <b>Balans:</b>\n"
        f"• 💵 Pul: <code>${profile.money:,.0f}</code>\n"
        f"• 💎 Olmos: <code>{profile.diamond:,}</code> ta\n"
        f"• 🪙 Ball: <code>{profile.score:,}</code>\n\n"
        f"🛡 <b>Inventar va Qurollar:</b>\n"
        f"• 🔫 Miltiq: <code>{profile.miltiq}</code> ta\n"
        f"• 🛡 Himoya: <code>{profile.himoya}</code> ta\n"
        f"• 💊 Doridan himoya: <code>{profile.doridan_himoya}</code> ta\n"
        f"• 🎭 Niqob: <code>{profile.mask}</code> ta\n"
        f"• 📜 Hujjat: <code>{profile.hujjat}</code> ta\n"
        f"• 🔒 Osishdan himoya: <code>{profile.osishdan_himoya}</code> ta\n\n"
        f"🎮 <b>O'yin statistikasi:</b>\n"
        f"• 🕹 O'yinlar: <code>{total_games}</code> ta\n"
        f"• 🏆 G'alabalar: <code>{wins}</code> ta\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    kb = admin_user_manage_kb(user_id=user_id, is_blocked=is_blocked, is_vip=is_vip)
    return text, kb

async def get_active_games_overview() -> str:
    """Hozirgi barcha faol o'yinlar ro'yxati"""
    active_games = await Game.filter(is_active=True).prefetch_related("chat", "creator").all()
    if not active_games:
        return "🎮 <b>Hozirda hech qanday faol o'yin mavjud emas.</b>"

    text = f"🎮 <b>Hozirgi faol o'yinlar soni: {len(active_games)} ta</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for idx, game in enumerate(active_games, start=1):
        players_count = await GamePlayer.filter(game=game, is_alive=True).count()
        chat_title = game.chat.title if game.chat and game.chat.title else f"Chat ID: {game.chat.chat_id}"
        phase_name = game.phase
        text += (
            f"{idx}. <b>{chat_title}</b>\n"
            f"   • O'yin ID: <code>{game.id}</code> | Rejim: <code>{game.mode}</code>\n"
            f"   • Faza: <b>{phase_name}</b> | Tiriklar: <b>{players_count}</b> ta\n\n"
        )
    return text

async def execute_broadcast_task(bot: Bot, target: str, message: Message, admin_id: int):
    """Foydalanuvchilarga yoki guruhlarga xabar yuborish (Rassilka)"""
    status_msg = await bot.send_message(
        admin_id,
        f"⏳ <b>Xabar tarqatish boshlandi...</b> ({'Foydalanuvchilar' if target == 'users' else 'Guruhlar'})",
        parse_mode="HTML"
    )

    success_count = 0
    blocked_count = 0
    error_count = 0

    if target == "users":
        recipients = await User.all().values_list("user_id", flat=True)
    else:
        recipients = await Chat.all().values_list("chat_id", flat=True)

    total = len(recipients)

    for i, chat_id in enumerate(recipients, start=1):
        try:
            await message.copy_to(chat_id=chat_id)
            success_count += 1
        except Exception as e:
            err_str = str(e).lower()
            if "blocked" in err_str or "deactivated" in err_str or "chat not found" in err_str:
                blocked_count += 1
            else:
                error_count += 1
        
        # Har 50 ta xabarda progressni yangilash
        if i % 50 == 0 or i == total:
            try:
                await status_msg.edit_text(
                    f"⏳ <b>Xabar tarqatilmoqda...</b>\n\n"
                    f"• Jami: <b>{total}</b>\n"
                    f"• Yuborildi: <b>{i}/{total}</b> ({(i/total*100):.1f}%)\n"
                    f"• ✅ Muvaffaqiyatli: <b>{success_count}</b>\n"
                    f"• 🚫 Bloklangan / O'chirilgan: <b>{blocked_count}</b>\n"
                    f"• ⚠️ Xatolik: <b>{error_count}</b>",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        await asyncio.sleep(0.04)  # Telegram limitlariga muvofiq xavfsiz kechikish

    report_text = (
        f"✅ <b>Xabar tarqatish muvaffaqiyatli yakunlandi!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"• Nishon: <b>{'Foydalanuvchilar' if target == 'users' else 'Guruhlar'}</b>\n"
        f"• 📊 Jami ob'yektlar: <b>{total}</b>\n"
        f"• ✅ Yetkazildi: <b>{success_count}</b> ta\n"
        f"• 🚫 Bloklagan/O'chgan: <b>{blocked_count}</b> ta\n"
        f"• ⚠️ Xatolik yuz berdi: <b>{error_count}</b> ta\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    await bot.send_message(admin_id, report_text, parse_mode="HTML", reply_markup=admin_back_btn())
