from aiogram.types import Message, CallbackQuery
from keyboards.main_keyboard import get_start_markup, gender_keyboard
from config import DIAMOND_SHOP_USERNAME
from models.user import User
from utils.i18n import clean_lang, START_TEXTS, GENDER_PROMPT

def _start_text(lang: str = "uz") -> str:
    code = clean_lang(lang)
    tmpl = START_TEXTS.get(code, START_TEXTS["uz"])
    return tmpl.format(shop_user=DIAMOND_SHOP_USERNAME)


async def _ensure_onboarded(user_id: int, full_name: str, mention: str, send_fn, lang: str = "uz") -> bool:
    """
    Yangi foydalanuvchilar uchun bir martalik onboarding:
    gender yo'q bo'lsa -> jins tanlashni ko'rsatadi.
    """
    user, _created = await User.get_or_create(
        user_id=user_id,
        defaults={"full_name": full_name, "mention": mention}
    )
    code = clean_lang(user.lang or lang)
    if user.gender:
        return False
    prompt = GENDER_PROMPT.get(code, GENDER_PROMPT["uz"])
    await send_fn(
        prompt,
        reply_markup=gender_keyboard(code),
        parse_mode="HTML"
    )
    return True


async def ensure_onboarded_or_defer(message: Message, state, args: str = None) -> bool:
    user, _created = await User.get_or_create(
        user_id=message.from_user.id,
        defaults={"full_name": message.from_user.full_name, "mention": message.from_user.mention_html()}
    )
    code = clean_lang(user.lang)
    if user.gender:
        return False
    if args:
        await state.update_data(pending_start_args=args)
    prompt = GENDER_PROMPT.get(code, GENDER_PROMPT["uz"])
    await message.answer(
        prompt,
        reply_markup=gender_keyboard(code),
        parse_mode="HTML"
    )
    return True


async def start_msg_handler(message: Message):
    user = await User.get_or_none(user_id=message.from_user.id)
    lang = clean_lang(user.lang if user else "uz")
    if await _ensure_onboarded(
        message.from_user.id,
        message.from_user.full_name,
        message.from_user.mention_html(),
        message.answer,
        lang=lang
    ):
        return
    await message.answer(_start_text(lang), reply_markup=get_start_markup(lang), parse_mode="HTML")


async def start_call_handler(call: CallbackQuery):
    user = await User.get_or_none(user_id=call.from_user.id)
    lang = clean_lang(user.lang if user else "uz")
    st_text = _start_text(lang)
    kb = get_start_markup(lang)
    try:
        await call.message.edit_text(st_text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        try:
            await call.message.answer(st_text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass
    try:
        await call.answer()
    except Exception:
        pass
