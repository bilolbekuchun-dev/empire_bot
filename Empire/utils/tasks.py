from datetime import datetime, timedelta, timezone
from aiogram import Bot
from models.game_data import Chat, Game, GamePlayer, GamePhase, Giveaway, Tournament
from models.game_set import GroupBalance
from aiogram.exceptions import TelegramRetryAfter
from models.user import User, Profile, VipUser
from config import ADMINS
from keyboards.game_keyboard import go_group_button
from asyncio import sleep
from utils.statistika import calculate_and_cache_global_stats

def _get_admin_chat_id():
    return ADMINS[0] if ADMINS else None

TASHKENT_TZ = timezone(timedelta(hours=5))


async def check_personal_birthday_gifts(bot: Bot):
    """Har kuni bir marta: 'birthday_date' (DD.MM) belgilangan shaxsiy tabriklarni tekshiradi
    va bugun sanaga to'g'ri kelganlarga sovg'ani (olmos/dollar) avtomatik beradi hamda
    tabrik xabarini shaxsiy botga yuboradi. Har bir yozuvga faqat 1 yilda 1 marta beriladi."""
    while True:
        try:
            today = datetime.now(TASHKENT_TZ)
            today_str = today.strftime("%d.%m")
            entries = await Tournament.filter(target_user_id__not_isnull=True, birthday_date=today_str).all()
            for entry in entries:
                if entry.gift_last_year == today.year:
                    continue
                target = await User.filter(user_id=entry.target_user_id).first()
                if not target:
                    continue
                if entry.gift_diamond or entry.gift_dollar:
                    profile, _ = await Profile.get_or_create(user=target)
                    profile.diamond += entry.gift_diamond
                    profile.dollar += entry.gift_dollar
                    await profile.save(update_fields=["diamond", "dollar"])
                entry.gift_last_year = today.year
                await entry.save(update_fields=["gift_last_year"])
                try:
                    gift_line = ""
                    if entry.gift_diamond:
                        gift_line += f"\n💎 Sovg'a: {entry.gift_diamond} olmos"
                    if entry.gift_dollar:
                        gift_line += f"\n💵 Sovg'a: {entry.gift_dollar} dollar"
                    text = f"🎉 <b>{entry.title}</b>\n\n{entry.banner_text}{gift_line}"
                    await bot.send_message(entry.target_user_id, text, parse_mode="HTML")
                except Exception:
                    pass
        except Exception as e:
            print(f"⚠️ check_personal_birthday_gifts xato: {e}")
        await sleep(86400)


def to_utc(dt: datetime) -> datetime:
    """
    Har qanday datetime obyektini UTC timezone-aware holatga keltiradi.
    - Agar None bo'lsa → None qaytaradi
    - Agar timezone-naive bo'lsa → UTC deb qabul qilib, aware qiladi
    - Agar boshqa timezone bo'lsa → UTC ga konvertatsiya qiladi
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def long_giveaways_cleanup(bot: Bot):
    """2 haftadan eski bo'lgan giveawaylarni tozalash"""
    while True:
        deleted_count = 0
        try:
            giveaways = await Giveaway.all()
            now = datetime.now(timezone.utc)

            for giveaway in giveaways:
                try:
                    created_at = to_utc(giveaway.created_at)
                    if created_at is None:
                        continue

                    giveaway_duration = now - created_at

                    if giveaway_duration > timedelta(weeks=2):
                        await giveaway.delete()
                        deleted_count += 1

                except Exception as e:
                    try:
                        admin_id = _get_admin_chat_id()
                        if admin_id:
                            await bot.send_message(
                                chat_id=admin_id,
                                text=f"Giveawayni o'chirishda xatolik: {str(e)}\nGiveaway ID: {giveaway.id}"
                            )
                    except Exception:
                        pass

        except Exception as e:
            try:
                admin_id = _get_admin_chat_id()
                if admin_id:
                    await bot.send_message(
                        chat_id=admin_id,
                        text=f"long_giveaways_cleanup xatolik: {str(e)}"
                    )
            except Exception:
                pass

        try:
            admin_id = _get_admin_chat_id()
            if admin_id:
                await bot.send_message(
                    chat_id=admin_id,
                    text=f"Giveaway tozalash tugadi.\n\nO'chirilgan giveawaylar soni: {deleted_count}"
                )
        except Exception:
            pass

        await sleep(86400)  # Har kun tekshirish


async def long_games_attack(bot: Bot):
    """2 soatdan uzun davom etgan yoki 30 daqiqadan ko'p kutishda qolib ketgan o'yinlarni tozalash"""
    while True:
        try:
            games = await Game.filter(is_active=True).prefetch_related('chat')
            now = datetime.now(timezone.utc)

            for game in games:
                try:
                    created_at = to_utc(game.created_at)
                    if created_at is None:
                        continue

                    game_duration = now - created_at

                    # 1. 30 daqiqadan ko'p waiting holatida qolgan o'yinlarni to'xtatish
                    if game.phase == "waiting" and game_duration > timedelta(minutes=30):
                        chat = await game.chat
                        game.is_active = False
                        game.phase = "end"
                        await game.save()
                        continue

                    # 2. 2 soatdan uzun davom etgan o'yinlarni to'xtatish
                    if game_duration > timedelta(hours=2):
                        chat = await game.chat
                        try:
                            admin_id = _get_admin_chat_id()
                            if admin_id:
                                await bot.send_message(
                                    chat_id=admin_id,
                                    text=(
                                        f"Uzluksiz o'yin topildi va o'chirilmoqda!\n\n"
                                        f"Guruh: {chat.title}\n"
                                        f"O'yin davomiyligi: {game_duration}\n"
                                        f"Yaratilgan: {game.created_at}"
                                    ),
                                    reply_markup=go_group_button(chat.invite_link)
                                )
                        except TelegramRetryAfter as e:
                            await sleep(e.retry_after)
                        except Exception:
                            pass

                        game.is_active = False
                        game.phase = "end"
                        await game.save()

                        try:
                            await bot.send_message(
                                chat_id=chat.chat_id,
                                text="⚠️ O'yin 2 soatdan ortiq davom etgani uchun avtomatik ravishda to'xtatildi!"
                            )
                        except Exception:
                            pass

                except Exception as e:
                    print(f"long_games_attack: game {getattr(game, 'id', '?')} xato: {e}")

        except Exception as e:
            print(f"long_games_attack xatolik: {e}")

        await sleep(300)  # Har 5 daqiqada tekshirish


async def daily_balance_task(bot: Bot):
    """Har 15 kunda guruh balansini tozalash"""
    while True:
        try:
            # Faqat balansi bor guruhlarni tekshiramiz
            groups = await GroupBalance.filter(balance__gt=0).all()
            now = datetime.now(timezone.utc)

            for group in groups:
                try:
                    last_reset = to_utc(group.last_reset_at)

                    if last_reset is None:
                        # Hech qachon reset qilinmagan — hozirgi vaqtni belgilash (tozalamay)
                        group.last_reset_at = now
                        await group.save(update_fields=['last_reset_at'])
                        continue

                    days_since_reset = (now - last_reset).days

                    if days_since_reset >= 15:
                        old_balance = group.balance
                        group.balance = 0
                        group.last_reset_at = now
                        await group.save(update_fields=['balance', 'last_reset_at'])

                        if old_balance > 0:
                            try:
                                await bot.send_message(
                                    chat_id=group.chat_id,
                                    text=(
                                        f"💎 Guruh balansida olmoslar muddati (15 kun) tugadi!\n\n"
                                        f"/gsend buyrug'i orqali guruh hisobini to'ldirishingiz mumkin."
                                    ),
                                    parse_mode="HTML"
                                )
                            except Exception:
                                pass

                except Exception as e:
                    pass

        except Exception as e:
            pass

        await sleep(3600)  # Har soatda tekshirish


async def check_vip_users(bot: Bot):
    """30 kundan eski VIP foydalanuvchilarni o'chirish"""
    while True:
        try:
            vip_users = await VipUser.all().prefetch_related('user')
            now = datetime.now(timezone.utc)

            for vip in vip_users:
                try:
                    created_at = to_utc(vip.created_at)
                    if created_at is None:
                        continue

                    if (now - created_at).days > 30:
                        await vip.delete()
                        try:
                            await bot.send_message(
                                chat_id=vip.user.user_id,
                                text="<b>⭐️ Sizning VIP statusingiz muddati tugadi.</b>",
                                parse_mode="HTML"
                            )
                        except Exception:
                            pass

                except Exception as e:
                    try:
                        admin_id = _get_admin_chat_id()
                        if admin_id:
                            await bot.send_message(
                                chat_id=admin_id,
                                text=f"VIP tekshirishda xatolik:\nXatolik: {str(e)}"
                            )
                    except Exception:
                        pass

        except Exception as e:
            try:
                admin_id = _get_admin_chat_id()
                if admin_id:
                    await bot.send_message(
                        chat_id=admin_id,
                        text=f"check_vip_users xatolik: {str(e)}"
                    )
            except Exception:
                pass

        await sleep(86400)  # Har kuni bir marta tekshirish


async def stats_update_task(bot: Bot):
    """Har 15 minutda statistikani yangilash"""
    while True:
        try:
            for period in ["today", "week", "month"]:
                await calculate_and_cache_global_stats(period)
        except Exception as e:
            try:
                admin_id = _get_admin_chat_id()
                if admin_id:
                    await bot.send_message(
                        chat_id=admin_id,
                        text=f"Statistika yangilashda xatolik: {str(e)}"
                    )
            except Exception:
                pass

        await sleep(900)  # 15 daqiqa kutiladi