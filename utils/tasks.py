import logging
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
    """Har kuni bir marta: 'birthday_date' (DD.MM) belgilangan shaxsiy tabriklarni tekshiridi
    va bugun sanaga to'g'ri kelganlarga sovg'ani (olmos/dollar) avtomatik beradi hamda
    tabrik xabarini shaxsiy botga yuboradi. Har bir yozuvga faqat 1 yilda 1 marta beriladi."""
    while True:
        try:
            today = datetime.now(TASHKENT_TZ)
            today_str = today.strftime("%d.%m")
            # Optimized: Use only() to fetch only needed fields
            entries = await Tournament.filter(
                target_user_id__not_isnull=True, 
                birthday_date=today_str
            ).only("id", "target_user_id", "gift_diamond", "gift_dollar", "title", "banner_text", "gift_last_year").all()
            
            processed_count = 0
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
                    processed_count += 1
                except Exception as e:
                    logging.warning(f"Failed to send birthday gift to {entry.target_user_id}: {e}")
            
            if processed_count > 0:
                logging.info(f"Sent birthday gifts to {processed_count} users")
        except Exception as e:
            logging.error(f"check_personal_birthday_gifts error: {e}", exc_info=True)
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
    """2 haftadan eski bo'lgan giveawaylarni tozalash (SQL filtri bilan)"""
    while True:
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=14)
            deleted_count = await Giveaway.filter(created_at__lt=cutoff).delete()

            if deleted_count > 0:
                admin_id = _get_admin_chat_id()
                if admin_id:
                    try:
                        await bot.send_message(
                            chat_id=admin_id,
                            text=f"Giveaway tozalash tugadi.\n\nO'chirilgan giveawaylar soni: {deleted_count}"
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

        await sleep(86400)  # Har kun tekshirish


async def long_games_attack(bot: Bot):
    """2 soatdan uzun davom etgan yoki 30 daqiqadan ko'p kutishda qolib ketgan o'yinlarni tozalash (SQL filtri bilan)"""
    while True:
        try:
            now = datetime.now(timezone.utc)
            waiting_cutoff = now - timedelta(minutes=30)
            long_game_cutoff = now - timedelta(hours=2)

            # 1. 30 daqiqadan ko'p waiting holatida qolgan o'yinlarni to'xtatish
            stale_waiting_games = await Game.filter(
                is_active=True, 
                phase="waiting", 
                created_at__lt=waiting_cutoff
            ).only("id", "is_active", "phase").all()
            
            waiting_stopped = 0
            for game in stale_waiting_games:
                try:
                    game.is_active = False
                    game.phase = "end"
                    await game.save(update_fields=['is_active', 'phase'])
                    waiting_stopped += 1
                except Exception as e:
                    logging.warning(f"long_games_attack waiting game {game.id} error: {e}")

            # 2. 2 soatdan uzun davom etgan o'yinlarni to'xtatish
            stale_long_games = await Game.filter(
                is_active=True, 
                created_at__lt=long_game_cutoff
            ).select_related('chat').all()
            
            long_stopped = 0
            for game in stale_long_games:
                try:
                    chat = game.chat
                    game_duration = now - to_utc(game.created_at)
                    if chat:
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
                        except Exception as e:
                            logging.warning(f"Failed to notify admin about long game: {e}")

                    game.is_active = False
                    game.phase = "end"
                    await game.save(update_fields=['is_active', 'phase'])
                    long_stopped += 1

                    if chat:
                        try:
                            await bot.send_message(
                                chat_id=chat.chat_id,
                                text="⚠️ O'yin 2 soatdan ortiq davom etgani uchun avtomatik ravishda to'xtatildi!"
                            )
                        except Exception as e:
                            logging.warning(f"Failed to notify chat about long game stop: {e}")
                except Exception as e:
                    logging.error(f"long_games_attack long game {game.id} error: {e}", exc_info=True)
            
            if waiting_stopped > 0 or long_stopped > 0:
                logging.info(f"long_games_attack: stopped {waiting_stopped} waiting games, {long_stopped} long games")

        except Exception as e:
            logging.error(f"long_games_attack error: {e}", exc_info=True)

        await sleep(300)  # Har 5 daqiqada tekshirish


async def daily_balance_task(bot: Bot):
    """Har 15 kunda guruh balansini tozalash (SQL filtri bilan)"""
    while True:
        try:
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(days=15)

            # 15 kundan ortiq reset qilinmagan va balansi bor guruhlar
            expired_groups = await GroupBalance.filter(
                balance__gt=0, 
                last_reset_at__lt=cutoff
            ).only("id", "chat_id", "balance", "last_reset_at").all()
            
            reset_count = 0
            for group in expired_groups:
                try:
                    old_balance = group.balance
                    group.balance = 0
                    group.last_reset_at = now
                    await group.save(update_fields=['balance', 'last_reset_at'])
                    reset_count += 1

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
                        except Exception as e:
                            logging.warning(f"Failed to notify group {group.chat_id} about balance reset: {e}")
                except Exception as e:
                    logging.error(f"Error resetting balance for group {group.chat_id}: {e}", exc_info=True)

            # last_reset_at belgilanmagan balansi bor guruhlarga joriy vaqtni yozib qo'yish
            unset_groups = await GroupBalance.filter(
                balance__gt=0, 
                last_reset_at__isnull=True
            ).only("id", "chat_id", "last_reset_at").all()
            
            initialized_count = 0
            for group in unset_groups:
                try:
                    group.last_reset_at = now
                    await group.save(update_fields=['last_reset_at'])
                    initialized_count += 1
                except Exception as e:
                    logging.error(f"Error initializing last_reset_at for group {group.chat_id}: {e}", exc_info=True)
            
            if reset_count > 0 or initialized_count > 0:
                logging.info(f"daily_balance_task: reset {reset_count} groups, initialized {initialized_count} groups")

        except Exception as e:
            logging.error(f"daily_balance_task error: {e}", exc_info=True)

        await sleep(3600)  # Har soatda tekshirish


async def check_vip_users(bot: Bot):
    """Muddati tugagan VIP foydalanuvchilarni o'chirish (duration_days bo'yicha)"""
    while True:
        try:
            now = datetime.now(timezone.utc)
            all_vips = await VipUser.all().prefetch_related('user')
            expired_count = 0
            for vip in all_vips:
                try:
                    duration = getattr(vip, 'duration_days', 30) or 30
                    vip_created = to_utc(vip.created_at)
                    if vip_created and (vip_created + timedelta(days=duration) < now):
                        user_id = vip.user.user_id if vip.user else None
                        await vip.delete()
                        expired_count += 1
                        if user_id:
                            try:
                                await bot.send_message(
                                    chat_id=user_id,
                                    text="<b>⭐️ Sizning VIP statusingiz muddati tugadi.</b>",
                                    parse_mode="HTML"
                                )
                            except Exception as e:
                                logging.warning(f"Failed to notify VIP user {user_id}: {e}")
                except Exception as e:
                    logging.error(f"Error checking individual VIP user: {e}", exc_info=True)
            
            if expired_count > 0:
                logging.info(f"check_vip_users: expired {expired_count} VIP users")

        except Exception as e:
            logging.error(f"check_vip_users error: {e}", exc_info=True)

        await sleep(3600)  # Har soatda tekshirish


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