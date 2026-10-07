import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from models.user import RequiredChannel, User
from utils.i18n import clean_lang, SUB_REQUIRED_TEXT, SUB_CHECK_BTN

logger = logging.getLogger(__name__)

SUB_PROMPT_TEXT = (
    "Iltimos, quyidagi kanal(lar) ga obuna boling va pastdagi \"tekshirish\" tugmasini bosing"
)

async def get_unsubscribed_channels(bot: Bot, user_id: int):
    """
    Foydalanuvchi obuna bo'lmagan majburiy kanallar ro'yxatini qaytaradi.
    """
    try:
        active_channels = await RequiredChannel.filter(is_active=True).all()
    except Exception as e:
        logger.warning(f"RequiredChannel db error: {e}")
        return []

    if not active_channels:
        return []

    unsubscribed = []
    for ch in active_channels:
        target_chat = ch.channel_id or ch.username or ch.invite_link
        if not target_chat:
            continue
            
        try:
            member = await bot.get_chat_member(chat_id=target_chat, user_id=user_id)
            if member.status not in ["creator", "administrator", "member"]:
                unsubscribed.append(ch)
        except Exception as e:
            logger.warning(f"Obunani tekshirishda xatolik (channel: {target_chat}, user: {user_id}): {e}")
            unsubscribed.append(ch)

    return unsubscribed

def build_sub_keyboard(unsubscribed_channels, lang: str = "uz"):
    """
    Obuna bo'lish tugmalari va 'Tekshirish' tugmasini yaratadi.
    """
    code = clean_lang(lang)
    check_btn_text = SUB_CHECK_BTN.get(code, SUB_CHECK_BTN["uz"])

    kb = []
    for idx, ch in enumerate(unsubscribed_channels, 1):
        url = ch.invite_link
        if not url and ch.username:
            username = ch.username.lstrip("@")
            url = f"https://t.me/{username}"
        elif not url:
            url = "https://t.me"
            
        kb.append([InlineKeyboardButton(text=f"📢 {ch.title}", url=url)])

    kb.append([InlineKeyboardButton(text=check_btn_text, callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

async def ensure_subscribed_or_prompt(event, bot: Bot) -> bool:
    """
    Agar foydalanuvchi shaxsiy yozishmada majburiy kanallarga obuna bo'lmagan bo'lsa,
    ogohlantirish xabarini chiqaradi va True (to'xtatish) qaytaradi.
    """
    chat_type = getattr(getattr(event, "chat", None), "type", None)
    if isinstance(event, CallbackQuery) and event.message:
        chat_type = event.message.chat.type

    # Obunani faqat shaxsiy (private) yozishmalarda majburiy qilamiz
    if chat_type and chat_type != "private":
        return False

    user_id = event.from_user.id
    user = await User.get_or_none(user_id=user_id)
    lang = clean_lang(user.lang if user else "uz")

    unsubscribed = await get_unsubscribed_channels(bot, user_id)
    if not unsubscribed:
        return False

    prompt_text = SUB_REQUIRED_TEXT.get(lang, SUB_REQUIRED_TEXT["uz"])
    kb = build_sub_keyboard(unsubscribed, lang=lang)

    if isinstance(event, Message):
        await event.answer(prompt_text, reply_markup=kb)
    elif isinstance(event, CallbackQuery):
        await event.answer(prompt_text, show_alert=True)
        try:
            await event.message.edit_text(prompt_text, reply_markup=kb)
        except Exception:
            await event.message.answer(prompt_text, reply_markup=kb)
    return True
