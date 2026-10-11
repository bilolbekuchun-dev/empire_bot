"""
Rol almashtirish funksiyasi
Agar muhim rollar (DON, KOMISSAR, DOKTOR) yo'q bo'lsa, 
ularning o'rnini tegishli vorislar egallaydi.
"""

from aiogram import Bot
from models.game_data import GamePlayer, Chat
from utils.role_names import RoleNames


async def check_and_replace_missing_roles(players_list, bot: Bot, chat: Chat, game):
    """
    O'yin boshida rollarni tekshirib, kerakli rol almashtirishlarini amalga oshiradi
    
    Args:
        players_list: O'yinchilar ro'yxati
        bot: Telegram bot
        chat: Chat obyekti
        game: O'yin obyekti
    """
    
    # Asosiy rollarni tekshirish
    don_bor = any(p.role == RoleNames.DON and p.is_alive for p in players_list)
    komissar_bor = any(p.role == RoleNames.KOMISSAR and p.is_alive for p in players_list)
    doktor_bor = any(p.role == RoleNames.DOKTOR and p.is_alive for p in players_list)
    
    # Vorislarni tekshirish
    mafia_bor = any(p.role == RoleNames.MAFIA and p.is_alive for p in players_list)
    serjant_bor = any(p.role == RoleNames.SERJANT and p.is_alive for p in players_list)
    
    # DON yo'q lekin MAFIA bor bo'lsa
    if not don_bor and mafia_bor:
        mafia_player = next(p for p in players_list if p.role == RoleNames.MAFIA and p.is_alive)
        mafia_player.role = RoleNames.DON
        await mafia_player.save()
        await mafia_player.fetch_related("user")
        
        await bot.send_message(
            mafia_player.user.user_id,
            f"🤵🏼 <b>Siz endi {RoleNames.DON} bo'ldingiz!</b>\n\n",
            parse_mode="HTML"
        )

    
    # KOMISSAR yo'q lekin SERJANT bor bo'lsa
    if not komissar_bor and serjant_bor:
        serjant_player = next(p for p in players_list if p.role == RoleNames.SERJANT and p.is_alive)
        serjant_player.role = RoleNames.KOMISSAR
        await serjant_player.save()
        await serjant_player.fetch_related("user")
        
        await bot.send_message(
            serjant_player.user.user_id,
            f"👮‍♂️ <b>Siz endi {RoleNames.KOMISSAR} bo'ldingiz!</b>\n",
            parse_mode="HTML"
        )
        
    return True