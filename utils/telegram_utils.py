"""
Telegram message utilities - xabar uzunligi va formatlashni boshqarish.
"""
from typing import List
from aiogram import Bot
from aiogram.types import Message


# Telegram limitleri
TELEGRAM_MAX_MESSAGE_LENGTH = 4096
TELEGRAM_SAFE_MESSAGE_LENGTH = 4000  # Buffer uchun


def split_long_message(text: str, max_length: int = TELEGRAM_SAFE_MESSAGE_LENGTH) -> List[str]:
    """
    Uzun xabarni bir nechta qismlarga bo'ladi.
    Qatorlar o'rtasida bo'lishga harakat qiladi.
    
    Args:
        text: Bo'linadigan xabar
        max_length: Maksimal uzunlik (default: 4000)
        
    Returns:
        Xabarlar ro'yxati
    """
    if len(text) <= max_length:
        return [text]
    
    messages = []
    current_message = ""
    
    # Split by lines to preserve formatting
    lines = text.split('\n')
    
    for line in lines:
        # If single line is too long, split it by words
        if len(line) > max_length:
            words = line.split(' ')
            for word in words:
                # If single word is too long, force split it
                if len(word) > max_length:
                    # Split word into chunks
                    while len(word) > 0:
                        chunk_size = max_length - len(current_message) - 1 if current_message else max_length
                        if chunk_size <= 0:
                            messages.append(current_message)
                            current_message = ""
                            chunk_size = max_length
                        
                        chunk = word[:chunk_size]
                        word = word[chunk_size:]
                        
                        if current_message:
                            current_message += ' ' + chunk
                        else:
                            current_message = chunk
                        
                        if len(word) > 0 and len(current_message) + len(word) > max_length:
                            messages.append(current_message)
                            current_message = ""
                else:
                    # Normal word processing
                    if len(current_message) + len(word) + 1 > max_length:
                        if current_message:
                            messages.append(current_message)
                        current_message = word
                    else:
                        current_message += (' ' if current_message else '') + word
        else:
            # Check if adding this line exceeds limit
            if len(current_message) + len(line) + 1 > max_length:
                # Save current message and start new one
                if current_message:
                    messages.append(current_message)
                current_message = line
            else:
                current_message += ('\n' if current_message else '') + line
    
    # Add last message
    if current_message:
        messages.append(current_message)
    
    return messages


async def send_long_message(
    bot: Bot,
    chat_id: int,
    text: str,
    parse_mode: str = "HTML",
    reply_markup = None,
    **kwargs
) -> List[Message]:
    """
    Uzun xabarni yuboradi, kerak bo'lsa bir nechta qismga bo'lib.
    
    Args:
        bot: Bot instance
        chat_id: Chat ID
        text: Yuborilayotgan xabar
        parse_mode: HTML yoki Markdown
        reply_markup: Keyboard (faqat oxirgi xabarga qo'shiladi)
        **kwargs: Qo'shimcha parametrlar
        
    Returns:
        Yuborilgan xabarlar ro'yxati
    """
    messages = split_long_message(text)
    sent_messages = []
    
    for i, msg_text in enumerate(messages):
        # Only add reply_markup to last message
        current_markup = reply_markup if i == len(messages) - 1 else None
        
        sent_msg = await bot.send_message(
            chat_id=chat_id,
            text=msg_text,
            parse_mode=parse_mode,
            reply_markup=current_markup,
            **kwargs
        )
        sent_messages.append(sent_msg)
    
    return sent_messages


async def edit_long_message(
    message: Message,
    text: str,
    parse_mode: str = "HTML",
    reply_markup = None,
    **kwargs
) -> List[Message]:
    """
    Xabarni edit qiladi. Agar yangi xabar uzunroq bo'lsa, 
    eski xabarni o'chiradi va yangi xabar(lar) yuboradi.
    
    Args:
        message: Edit qilinadigan xabar
        text: Yangi xabar matni
        parse_mode: HTML yoki Markdown
        reply_markup: Keyboard
        **kwargs: Qo'shimcha parametrlar
        
    Returns:
        Oxirgi xabar yoki xabarlar ro'yxati
    """
    if len(text) <= TELEGRAM_SAFE_MESSAGE_LENGTH:
        # Single message - just edit
        try:
            edited = await message.edit_text(
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                **kwargs
            )
            return [edited]
        except Exception:
            # If edit fails, delete and send new
            await message.delete()
            return await send_long_message(
                message.bot,
                message.chat.id,
                text,
                parse_mode,
                reply_markup,
                **kwargs
            )
    else:
        # Multiple messages needed - delete original and send new ones
        await message.delete()
        return await send_long_message(
            message.bot,
            message.chat.id,
            text,
            parse_mode,
            reply_markup,
            **kwargs
        )


def truncate_text(text: str, max_length: int = TELEGRAM_SAFE_MESSAGE_LENGTH, suffix: str = "...") -> str:
    """
    Xabarni qisqartiradi va suffix qo'shadi.
    
    Args:
        text: Qisqartirilayotgan xabar
        max_length: Maksimal uzunlik
        suffix: Qo'shiladigan suffix (default: "...")
        
    Returns:
        Qisqartirilgan xabar
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def format_large_list(
    items: List[str],
    title: str = "",
    max_length: int = TELEGRAM_SAFE_MESSAGE_LENGTH,
    items_per_page: int = None
) -> List[str]:
    """
    Katta ro'yxatni bir nechta xabarga bo'ladi.
    
    Args:
        items: Element ro'yxati
        title: Har bir sahifaning sarlavhasi
        max_length: Maksimal uzunlik
        items_per_page: Har bir sahifadagi elementlar soni (None = avtomatik)
        
    Returns:
        Xabarlar ro'yxati
    """
    if not items:
        return [title if title else "Bo'sh ro'yxat"]
    
    messages = []
    current_text = f"{title}\n\n" if title else ""
    page = 1
    
    for item in items:
        item_text = f"{item}\n"
        
        if len(current_text) + len(item_text) > max_length:
            # Save current page
            messages.append(current_text)
            page += 1
            # Start new page
            page_title = f"{title} (Sahifa {page})" if title else f"Sahifa {page}"
            current_text = f"{page_title}\n\n{item_text}"
        else:
            current_text += item_text
    
    # Add last page
    if current_text:
        messages.append(current_text)
    
    return messages


async def get_chat_join_link(bot: Bot, chat_id: int) -> str:
    """
    Guruh/kanal uchun taklif havolasini olish yoki yaratish:
    1. Agar guruhda public username bo'lsa -> https://t.me/<username>
    2. Agar bot.get_chat() da invite_link bo'lsa -> shu havola
    3. Bot huquqlari orqali yangi havola yaratish -> bot.create_chat_invite_link(chat_id, name="Empire Mafia")
    4. Birlamchi havolani olish -> bot.export_chat_invite_link(chat_id)
    """
    try:
        chat = await bot.get_chat(chat_id)
        if chat.username:
            return f"https://t.me/{chat.username}"
        if chat.invite_link:
            return chat.invite_link
    except Exception:
        pass

    try:
        invite = await bot.create_chat_invite_link(chat_id=chat_id, name="Empire Mafia")
        if invite and invite.invite_link:
            return invite.invite_link
    except Exception:
        pass

    try:
        link = await bot.export_chat_invite_link(chat_id=chat_id)
        if link:
            return link
    except Exception:
        pass

    return ""


import logging
logger = logging.getLogger(__name__)

async def safe_send_message(bot: Bot, chat_id: int, text: str, parse_mode: str = "HTML", reply_markup=None, **kwargs):
    """
    Xabarni xavfsiz yuboradi. Uzun xabarlar bo'lsa bo'lib yuboradi.
    Xatolik yuz berganda exception tashlamaydi (catch qiladi).
    """
    try:
        return await send_long_message(bot, chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup, **kwargs)
    except Exception as e:
        logger.warning(f"safe_send_message error ({chat_id}): {e}")
        return None
