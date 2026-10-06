import asyncio
from aiogram import Bot
from models.user import User
from models.game_data import GamePlayer, Game

# Kechiktirilgan (o'yinda bo'lgan) foydalanuvchilar uchun bildirishnomalar navbati
# format: { user_id: [message_text1, message_text2] }
_DEFERRED_NOTIFICATIONS = {}

async def is_user_in_active_game(user_id: int) -> bool:
    """Foydalanuvchi hozir faol o'yin ichidami yoki yo'qligini tekshiradi"""
    try:
        active_player = await GamePlayer.filter(
            user_id=user_id,
            game__is_active=True
        ).first()
        return active_player is not None
    except Exception:
        return False

async def notify_airdrop_event(bot: Bot, user_id: int, notification_text: str):
    """
    AQLLI BILDIRISHNOMA:
    Agar foydalanuvchi o'yinda bo'lsa -> o'yin tugaguncha saqlab turiladi.
    Agar bo'sh bo'lsa -> darhol yuboriladi.
    """
    in_game = await is_user_in_active_game(user_id)
    if in_game:
        if user_id not in _DEFERRED_NOTIFICATIONS:
            _DEFERRED_NOTIFICATIONS[user_id] = []
        _DEFERRED_NOTIFICATIONS[user_id].append(notification_text)
    else:
        try:
            await bot.send_message(user_id, notification_text, parse_mode="HTML")
        except Exception:
            pass

async def flush_deferred_notifications_for_user(bot: Bot, user_id: int):
    """Foydalanuvchining o'yini tugaganda barcha kechiktirilgan xabarlarni yuboradi"""
    if user_id in _DEFERRED_NOTIFICATIONS and _DEFERRED_NOTIFICATIONS[user_id]:
        messages = _DEFERRED_NOTIFICATIONS.pop(user_id, [])
        for msg in messages:
            try:
                await bot.send_message(user_id, msg, parse_mode="HTML")
                await asyncio.sleep(0.5)
            except Exception:
                pass
