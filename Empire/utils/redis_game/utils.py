"""
Utils - Umumiy yordamchi funksiyalar.
"""
from aiogram import Bot
from aiogram.types import Message
from aiogram.enums import ChatMemberStatus

from models.game_set import CommandPermissionsChat


async def check_user_permission(
    bot: Bot,
    chat_id: int,
    user_id: int,
    permission_type: str = "game_cmd"
) -> bool:
    """
    User ning buyruqni bajarish huquqini tekshirish.
    
    Args:
        bot: Bot instance
        chat_id: Chat ID
        user_id: User ID
        permission_type: Permission turi (game_cmd, start_cmd, etc.)
    
    Returns:
        bool: Ruxsat bor bo'lsa True
    """
    cmd_perm, _ = await CommandPermissionsChat.get_or_create(
        chat_id=chat_id,
        defaults={
            "game_cmd": "admin",
            "start_cmd": "admin",
            "stop_cmd": "admin",
            "top1_cmd": "admin",
            "top7_cmd": "admin",
            "top30_cmd": "admin",
            "gtop1_cmd": "admin",
            "gtop7_cmd": "admin",
            "gtop30_cmd": "admin"
        }
    )
    
    perm_level = getattr(cmd_perm, permission_type, "admin")
    member = await bot.get_chat_member(chat_id, user_id)
    
    if perm_level == "admin":
        return member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    elif perm_level == "member":
        return member.status in [
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR,
            ChatMemberStatus.MEMBER
        ]
    elif perm_level == "ega":
        return member.status == ChatMemberStatus.CREATOR
    
    return False
