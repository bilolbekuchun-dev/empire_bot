from aiogram.types import Message, CallbackQuery
from keyboards.main_keyboard import get_start_markup, gender_keyboard
from config import DIAMOND_SHOP_USERNAME
from models.user import User

CHOOSE_GENDER_TEXT = "Davom etishdan oldin jinsingizni tanlang:"

START_TEXT = (
    "<b>Salom</b>\n"
    "Men mafiya botiman. Doʻstlar bilan mafiya oʻynash uchun meni guruhingizga qoʻshing va "
    "45 kishilik oʻyindan zavqlaning batafsil maʼlumot uchun {shop_user}\n\n"
    " Meni admin qilib qoʻyganingizdan soʻng, oʻyinni boshlashingiz mumkin.."
)


def _start_text() -> str:
    return START_TEXT.format(shop_user=DIAMOND_SHOP_USERNAME)


async def _get_user_safe(from_user):
    try:
        user, _ = await User.get_or_create(
            user_id=from_user.id,
            defaults={
                "full_name": from_user.full_name[:100] if from_user.full_name else "Foydalanuvchi",
                "mention": from_user.mention_html() if hasattr(from_user, 'mention_html') else from_user.full_name
            }
        )
        return user
    except Exception:
        users = await User.filter(user_id=from_user.id).all()
        if users:
            return users[0]
        return await User.create(
            user_id=from_user.id,
            full_name=from_user.full_name[:100] if from_user.full_name else "Foydalanuvchi",
            mention=from_user.mention_html() if hasattr(from_user, 'mention_html') else from_user.full_name
        )


async def _ensure_onboarded(from_user, send_fn) -> bool:
    """
    Yangi foydalanuvchilar uchun bir martalik onboarding:
    gender yo'q bo'lsa -> jins tanlashni ko'rsatadi.
    True qaytarsa -> onboarding boshlandi, asosiy menyu ko'rsatilmaydi.
    """
    user = await _get_user_safe(from_user)
    if user.gender:
        return False
    await send_fn(
        CHOOSE_GENDER_TEXT,
        reply_markup=gender_keyboard(),
        parse_mode="HTML"
    )
    return True


async def ensure_onboarded_or_defer(message: Message, state, args: str = None) -> bool:
    """
    /start ni har qanday argument (masalan game_12345 deep-link) bilan bosishdan oldin
    ishlaydi. Gender yo'q bo'lsa -> jins tanlashni ko'rsatadi va argumentni state ga
    saqlab qo'yadi.
    """
    user = await _get_user_safe(message.from_user)
    if user.gender:
        return False
    if args:
        await state.update_data(pending_start_args=args)
    await message.answer(
        CHOOSE_GENDER_TEXT,
        reply_markup=gender_keyboard(),
        parse_mode="HTML"
    )
    return True


async def start_msg_handler(message: Message):
    if await _ensure_onboarded(message.from_user, message.answer):
        return
    await message.answer(_start_text(), reply_markup=get_start_markup(), parse_mode="HTML")


async def start_call_handler(call: CallbackQuery):
    await call.message.edit_text(_start_text(), reply_markup=get_start_markup(), parse_mode="HTML")
    await call.answer()
