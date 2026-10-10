import logging
from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

logger = logging.getLogger(__name__)

# Empire Bot uchun majburiy 3 ta ruxsatlar
REQUIRED_PERMISSIONS = {
    "can_delete_messages": "🗑 Xabarlarni o'chirish huquqi",
    "can_pin_messages": "📌 Xabarlarni pin qilish (qadash)",
    "can_invite_users": "🔗 Guruhga qo'shish / Havola orqali taklif qilish",
}

async def check_bot_group_permissions(bot: Bot, chat_id: int) -> tuple[bool, list[str]]:
    """
    Guruhdagi bot adminlik va majburiy 3 ta ruxsatlarini tekshiradi:
    1. can_delete_messages (Xabar o'chirish)
    2. can_pin_messages (Habarni pin qilish)
    3. can_invite_users (Guruhga qo'shish / Havola orqali taklif qilish)

    Returns: (is_valid: bool, missing_labels: list[str])
    """
    try:
        me = await bot.get_chat_member(chat_id, bot.id)
        if me.status == ChatMemberStatus.CREATOR:
            return True, []
        if me.status != ChatMemberStatus.ADMINISTRATOR:
            return False, ["❗️ Bot guruhda Admin emas"]

        missing = []
        for perm_attr, label in REQUIRED_PERMISSIONS.items():
            if not getattr(me, perm_attr, False):
                missing.append(label)

        if missing:
            return False, missing
        return True, []
    except (TelegramForbiddenError, TelegramBadRequest):
        return False, ["❗️ Bot guruhda Admin emas (yoki guruhdan chiqarilgan)"]
    except Exception as e:
        logger.warning(f"Error checking bot permissions for chat {chat_id}: {e}")
        return False, ["⚠️ Xatolik yuz berdi. Iltimos botni guruhga qaytadan admin qiling!"]

def get_permission_warning_text(missing_labels: list[str]) -> str:
    missing_str = "\n".join([f"• ❌ {lbl}" for lbl in missing_labels])
    return (
        "<b>⚠️ BOTNING GURUHDAGI HUQUQLARI YETARLI EMAS!</b>\n\n"
        "Bot guruhda to'liq va muammosiz ishlashi uchun botga adminlik bering va quyidagi <b>3 ta majburiy ruxsatni</b> yoqing:\n\n"
        "1. 🗑 <b>Xabarlarni o'chirish huquqi</b>\n"
        "2. 📌 <b>Xabarlarni pin qilish (qadash)</b>\n"
        "3. 🔗 <b>Guruhga qo'shish / Havola orqali taklif qilish</b>\n\n"
        f"<i>⚠️ Hozirda yetishmayotgan ruxsatlar:</i>\n{missing_str}\n\n"
        "👉 <i>Iltimos, guruh sozlamalaridan (Group Settings ➔ Administrators) botga ko'rsatilgan ruxsatlarni berib, qaytadan urinib ko'ring.</i>"
    )
