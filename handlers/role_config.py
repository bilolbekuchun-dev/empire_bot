"""
Admin handlers for role configuration management.
Allows querying role order via bot commands.
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from utils.role_configuration import RoleConfiguration
from utils.redis_game.role_assignment import get_role_config_text
import config

router = Router()


@router.message(Command("roleconfig"))
async def roles_command_handler(message: Message):
    """
    Show role configuration for all modes or specific mode.
    Handles Telegram's 4096 character limit by splitting into multiple messages.
    
    Usage: 
        /roles - show all modes
        /roles classic - show classic mode config
    """
    args = message.text.split(maxsplit=1)
    
    if len(args) == 1:
        # Show all modes
        messages = await get_role_config_text()
        for text in messages:
            await message.answer(text, parse_mode="HTML")
    else:
        # Show specific mode
        mode = args[1].strip()
        messages = await get_role_config_text(mode)
        for text in messages:
            await message.answer(text, parse_mode="HTML")


@router.message(Command("rolemodes"))
async def role_modes_handler(message: Message):
    """
    Show all available game modes with buttons.
    """
    modes = RoleConfiguration.get_all_modes()
    
    # Create keyboard with mode buttons
    keyboard = []
    for mode in modes:
        keyboard.append([
            InlineKeyboardButton(
                text=f"🎭 {mode}",
                callback_data=f"roleconfig_{mode}"
            )
        ])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await message.answer(
        "<b>📋 O'YIN MODE'LARINI TANLANG:</b>\n\n"
        "Rol tartibini ko'rish uchun mode'ni bosing:",
        reply_markup=markup,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "roleconfig_back")
async def role_config_back_handler(call: CallbackQuery):
    """
    Go back to mode selection.
    """
    modes = RoleConfiguration.get_all_modes()
    
    keyboard = []
    for mode in modes:
        keyboard.append([
            InlineKeyboardButton(
                text=f"🎭 {mode}",
                callback_data=f"roleconfig_{mode}"
            )
        ])
    
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await call.message.edit_text(
        "<b>📋 O'YIN MODE'LARINI TANLANG:</b>\n\n"
        "Rol tartibini ko'rish uchun mode'ni bosing:",
        reply_markup=markup,
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data.startswith("roleconfig_"))
async def role_config_callback_handler(call: CallbackQuery):
    """
    Handle role config button clicks.
    Handles Telegram's 4096 character limit.
    """
    mode = call.data.replace("roleconfig_", "")
    messages = await get_role_config_text(mode)
    
    # Add back button
    keyboard = [[
        InlineKeyboardButton(
            text="⬅️ Ortga",
            callback_data="roleconfig_back"
        )
    ]]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    # If multiple messages, delete original and send as new messages
    if len(messages) > 1:
        await call.message.delete()
        for i, text in enumerate(messages):
            # Only add back button to last message
            if i == len(messages) - 1:
                await call.message.answer(text, reply_markup=markup, parse_mode="HTML")
            else:
                await call.message.answer(text, parse_mode="HTML")
    else:
        # Single message - just edit
        await call.message.edit_text(
            messages[0],
            reply_markup=markup,
            parse_mode="HTML"
        )
    
    await call.answer()


@router.message(Command("roleinfo"))
async def role_info_handler(message: Message):
    """
    Show general info about role system.
    """
    text = """
<b>🎭 ROL TIZIMI HAQIDA</b>

<b>📊 Rol Taqsimlash Tartibi:</b>
1. Sotib olingan faol rollar birinchi navbatda beriladi
2. Qolgan rollar tasodifiy taqsimlanadi
3. Majburiy rollar: DON, KOMISSAR, MAFIA, FUQARO
4. Taqiqlangan rollar FUQARO/BORI bilan almashtiriladi

<b>💡 Komandalar:</b>
/roles - Barcha mode'larni ko'rish
/roles [mode] - Ma'lum bir mode uchun rol tartibi
/rolemodes - Mode'larni button bilan tanlash

<b>🎮 Game Mode'lar:</b>
• Classic - Oddiy klassik o'yin
• Super - Ko'proq maxsus rollar
• Mega - Eng ko'p rollar
• Real - Real mode
• VS - Jamoaviy o'yin
• Zombie - Zombie mode
• Para - Juftlik o'yini

<b>📝 Misol:</b>
/roles classic - Classic mode rol tartibini ko'rish
    """
    
    await message.answer(text, parse_mode="HTML")
