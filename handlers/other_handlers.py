from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery
from aiogram.filters import Command, and_f
from filters.more import DelCommands
from utils import start, sandiqlar, profile_actions, others
from utils.subscription import ensure_subscribed_or_prompt
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()

class VipEmojiState(StatesGroup):
    waiting_for_emoji = State()

@router.message(Command("profile", "me", "myprofile", "prof", "profil"))
@router.message(F.text.in_(["/profile", "/me", "/myprofile", "/prof", "/profil", "Profil", "👤 Profil", "My profile", "🌐 Shaxsiy kabinet", "Shaxsiy kabinet"]))
async def profile_command_handler(message: Message, bot: Bot):
    if await ensure_subscribed_or_prompt(message, bot):
        return
    await others.get_profile(bot, message)


@router.message(Command("give", "money", "send", "otkazma", "pul"))
@router.message(F.text.startswith("/give"))
@router.message(F.text.startswith("/money"))
@router.message(F.text.startswith("/send"))
@router.message(F.text.startswith("/otkazma"))
@router.message(F.text.startswith("/pul"))
async def transfer_money_cmd(message: Message, bot: Bot):
    await others.transfer_funds_handler(message, bot)

@router.message(DelCommands())
async def f(message: Message):
    pass

@router.message(profile_actions.TransferProfileState.waiting_for_transfer_profile)
async def f(message: Message, state: FSMContext):
    await profile_actions.process_transfer_profile(message=message, state=state)

@router.message(Command("vipemoji"))
@router.message(F.text.startswith("/vipemoji"))
async def f(message: Message, state: FSMContext):
    await sandiqlar.start_vip_emoji_change(message=message, state=state)

@router.message(VipEmojiState.waiting_for_emoji)
async def f(message: Message, state: FSMContext):
    await sandiqlar.process_vip_emoji_message(message=message, state=state)

@router.callback_query(F.data.startswith("open-sandiq"))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await sandiqlar.open_sandiqlar(call, state)

@router.callback_query(F.data == "vip_emoji_change")
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await sandiqlar.start_vip_emoji_change_call(call, state)

@router.callback_query(F.data.startswith("super_sandiq"))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await sandiqlar.open_super_sandiq(call, state)

@router.callback_query(F.data.startswith("mega_sandiq"))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await sandiqlar.open_mega_sandiq(call, state)

@router.callback_query(F.data.startswith("back_to_start"))
async def f(call: CallbackQuery):
    await start.start_call_handler(call=call)

@router.callback_query(F.data.startswith("vip_user"))
async def f(call: CallbackQuery, state: FSMContext):
    await sandiqlar.buy_vip_user(call=call, state=state)

@router.callback_query(F.data.startswith("replace_profile"))
async def f(call: CallbackQuery, state: FSMContext):
    await profile_actions.transfer_profile(call=call, state=state)


@router.callback_query(F.data.startswith("rp_"))
async def f(call: CallbackQuery, state: FSMContext):
    await profile_actions.approve_transfer_profile(call=call, state=state)

@router.message(Command("lang", "language", "til", "yazyk", "dil"))
@router.message(F.text.in_(["/lang", "/language", "/til", "/yazyk", "/dil", "🌐 Til", "Tilni o'zgartirish", "Change language"]))
async def lang_cmd_handler(message: Message):
    await others.lang_command_handler(message)

@router.callback_query(F.data.startswith("setlang_"))
async def setlang_cb_handler(call: CallbackQuery):
    await others.set_lang_callback(call)

@router.callback_query(F.data.in_(["back_profile", "open_profile", "my_profile"]))
async def profile_callback_handler(call: CallbackQuery, bot: Bot):
    from keyboards.user_keyboards import profile_keyboards_on_private
    from models.user import User
    from utils.i18n import clean_lang
    await call.answer()

    user = await User.get_or_none(user_id=call.from_user.id)
    lang = clean_lang(user.lang if user else "uz")

    profile_text, profile = await others._build_profile_text(
        call.from_user.id,
        call.from_user.full_name
    )
    kb = profile_keyboards_on_private(profile, lang=lang)
    try:
        await call.message.edit_text(profile_text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await call.message.answer(profile_text, reply_markup=kb, parse_mode="HTML")