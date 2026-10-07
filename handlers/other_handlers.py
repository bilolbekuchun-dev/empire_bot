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
@router.callback_query(F.data == "vip_emoji_self_change")
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await sandiqlar.start_vip_emoji_change_call(call, state)

@router.callback_query(F.data == "clear_vip_self_emoji")
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await sandiqlar.clear_vip_self_emoji(call, state)

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
async def setlang_cb_handler(call: CallbackQuery, bot: Bot):
    await others.set_lang_callback(call, bot)

@router.callback_query(F.data.startswith("onboard_lang_"))
async def onboard_lang_cb(call: CallbackQuery, bot: Bot, state: FSMContext):
    from models.user import User
    from utils.i18n import clean_lang, SUB_REQUIRED_TEXT, GENDER_PROMPT
    from utils.subscription import get_unsubscribed_channels, build_sub_keyboard
    from keyboards.main_keyboard import gender_keyboard

    lang = clean_lang(call.data.split("_")[-1])
    user, _ = await User.get_or_create(
        user_id=call.from_user.id,
        defaults={"full_name": call.from_user.full_name or f"User_{call.from_user.id}", "mention": call.from_user.mention_html()}
    )
    user.lang = lang
    await user.save()
    await state.update_data(onboard_lang_selected=True)

    try:
        await call.answer()
    except Exception:
        pass

    # 2-bosqich: Majburiy obuna
    unsubscribed = await get_unsubscribed_channels(bot, call.from_user.id)
    if unsubscribed:
        prompt = SUB_REQUIRED_TEXT.get(lang, SUB_REQUIRED_TEXT["uz"])
        kb = build_sub_keyboard(unsubscribed, lang=lang)
        try:
            await call.message.edit_text(prompt, reply_markup=kb, parse_mode="HTML")
        except Exception:
            await call.message.answer(prompt, reply_markup=kb, parse_mode="HTML")
        return

    # 3-bosqich: Jins tanlash
    if not user.gender:
        prompt = GENDER_PROMPT.get(lang, GENDER_PROMPT["uz"])
        kb = gender_keyboard(lang)
        try:
            await call.message.edit_text(prompt, reply_markup=kb, parse_mode="HTML")
        except Exception:
            await call.message.answer(prompt, reply_markup=kb, parse_mode="HTML")
        return

    # 4-bosqich: Bosh menyu
    await start.start_call_handler(call)

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

@router.callback_query(F.data == "open_protections")
async def open_protections_cb(call: CallbackQuery):
    await others.open_protections_menu(call)

@router.callback_query(F.data.in_(["get_diamond_hamyonlar", "get_diamond", "get_dollar", "get_dollar_hamyonlar"]))
async def balance_cb(call: CallbackQuery):
    await others.get_diamond_hamyonlar(call)

@router.callback_query(F.data == "shop")
async def shop_cb(call: CallbackQuery):
    await others.show_shop(call)

@router.callback_query(F.data == "prem_groups")
async def prem_groups_cb(call: CallbackQuery, bot: Bot):
    await others.get_premium_groups_on_profile(call, bot)