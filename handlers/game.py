from aiogram import Router, Bot, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery
from utils import start, night_actions, day_actions, game_logic, others
from filters.more import DelCommands, NightSheriklarMessages, SayLastWordFilter
from utils.role_names import RoleNames
from aiogram.fsm.context import FSMContext
from utils.redis_game.handler_wrappers import (
    create_game_handler_wrapper,
    create_vs_game_handler_wrapper,
    join_game_handler_wrapper,
    kick_player_wrapper,
    leave_game_wrapper,
    stop_game_handler_wrapper,
    start_game_handler_wrapper
)

from utils.subscription import ensure_subscribed_or_prompt, get_unsubscribed_channels, build_sub_keyboard
from utils.i18n import clean_lang, SUB_REQUIRED_TEXT, GENDER_PROMPT
from keyboards.main_keyboard import gender_keyboard
from models.user import User

router = Router()

@router.message(Command("stop"))
async def f(message: Message, bot: Bot):
    await stop_game_handler_wrapper(message=message, bot=bot)

@router.message(Command("tep"))
async def f(message: Message, bot: Bot):
    await kick_player_wrapper(message, bot)

@router.message(Command("game"))
async def f(message: Message, bot: Bot):
    await create_game_handler_wrapper(message, bot)

@router.message(F.text.startswith("/vsgame"))
async def f(message: Message, bot: Bot):
    await create_vs_game_handler_wrapper(message, bot)

@router.message(Command("leave"))
async def f(message: Message, bot: Bot):
    await leave_game_wrapper(message, bot)

@router.message(Command("extend"))
async def f(message: Message, bot: Bot):
    await game_logic.extend_game_timer(message, bot)


@router.message(Command("start"), F.chat.type == "private")
async def f(message: Message, bot: Bot, state: FSMContext, command: CommandObject):
    args = command.args
    if args:
        await state.update_data(pending_start_args=args)

    user, _created = await User.get_or_create(
        user_id=message.from_user.id,
        defaults={"full_name": message.from_user.full_name, "mention": message.from_user.mention_html()}
    )

    data = await state.get_data()

    # 1-bosqich: Til tanlash (yangi foydalanuvchi yoki onboarding hali tugamagan bo'lsa)
    if not user.gender and not data.get("onboard_lang_selected"):
        from keyboards.main_keyboard import get_onboard_lang_keyboard
        text = "🌐 <b>Bot tilini tanlang / Choose bot language / Выберите язык бота / Bot dilini seçin:</b>"
        await message.answer(text, reply_markup=get_onboard_lang_keyboard(), parse_mode="HTML")
        return

    # 2-bosqich: Majburiy obuna
    if await ensure_subscribed_or_prompt(message, bot):
        return

    # 3-bosqich: Jins tanlash
    if not user.gender:
        lang = clean_lang(user.lang)
        prompt = GENDER_PROMPT.get(lang, GENDER_PROMPT["uz"])
        await message.answer(prompt, reply_markup=gender_keyboard(lang), parse_mode="HTML")
        return

    # 4-bosqich: Bosh menyu / Buyruqlar
    if args and "buy_star_" in args:
        await others.process_buy_star_main_bot(message=message, args=args)
    elif args and len(args.split("_")) > 1:
        await join_game_handler_wrapper(message, bot, state=state)
    else:
        await start.start_msg_handler(message)


@router.callback_query(F.data == "check_sub")
async def check_sub_handler(call: CallbackQuery, bot: Bot, state: FSMContext):
    user = await User.get_or_none(user_id=call.from_user.id)
    lang = clean_lang(user.lang if user else "uz")
    unsubscribed = await get_unsubscribed_channels(bot, call.from_user.id)

    if unsubscribed:
        prompt = SUB_REQUIRED_TEXT.get(lang, SUB_REQUIRED_TEXT["uz"])
        await call.answer(prompt, show_alert=True)
        try:
            await call.message.edit_text(
                prompt,
                reply_markup=build_sub_keyboard(unsubscribed, lang=lang),
                parse_mode="HTML"
            )
        except Exception:
            pass
    else:
        confirm_map = {
            "uz": "✅ Rahmat! Barcha kanallarga obuna bo'ldingiz.",
            "ru": "✅ Спасибо! Вы подписались на все каналы.",
            "en": "✅ Thank you! You subscribed to all channels.",
            "tr": "✅ Teşekkürler! Tüm kanallara abone oldunuz."
        }
        await call.answer(confirm_map.get(lang, confirm_map["uz"]), show_alert=True)
        if not user or not user.gender:
            prompt = GENDER_PROMPT.get(lang, GENDER_PROMPT["uz"])
            kb = gender_keyboard(lang)
            try:
                await call.message.edit_text(prompt, reply_markup=kb, parse_mode="HTML")
            except Exception:
                await call.message.answer(prompt, reply_markup=kb, parse_mode="HTML")
        else:
            await start.start_call_handler(call)


@router.message(Command("start"))
async def f(message: Message, bot: Bot, state: FSMContext):
    await start_game_handler_wrapper(message, bot, state)

@router.message(SayLastWordFilter())
async def f(message: Message, state: FSMContext):
    await day_actions.say_last_word_handler(message, state)

@router.callback_query(F.data.startswith(RoleNames.QAROQCHI))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await night_actions.qaroqchi_handler(call, bot, state)

@router.callback_query(F.data.startswith(RoleNames.KOMISSAR))
async def f(call: CallbackQuery, bot:Bot, state: FSMContext):
    await night_actions.komissar_action_handler(call, bot, state)

@router.callback_query(F.data.startswith("kom_upgrade_"))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await night_actions.komissar_upgrade_handler(call, bot, state)

@router.callback_query(F.data.startswith("learnbosh_"))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await night_actions.kom_learn_bosh_handler(call, bot, state)

@router.callback_query(F.data.startswith(RoleNames.DOKTOR))
async def f(call: CallbackQuery, bot:Bot, state: FSMContext):
    await night_actions.dok_action_handler(call, bot, state)

@router.callback_query(F.data.startswith(RoleNames.ZOMBI))
async def f(call: CallbackQuery, bot:Bot, state: FSMContext):
    await night_actions.zombi_action_handler(call, bot, state)

@router.callback_query(F.data.startswith(RoleNames.DON))
async def f(call: CallbackQuery, bot:Bot, state: FSMContext):
    await night_actions.don_action_handler(call, bot, state)

@router.callback_query(F.data.startswith(RoleNames.MAFIA))
async def f(call: CallbackQuery, bot:Bot, state: FSMContext):
    await night_actions.maf_action_handler(call, bot, state)

@router.callback_query(F.data.startswith(RoleNames.QORIQCHI))
async def f(call: CallbackQuery, bot:Bot, state: FSMContext):
    await night_actions.qoriqchi_action_handler(call, bot, state)

@router.callback_query(F.data.startswith(RoleNames.XOYIN))
async def f(call: CallbackQuery, bot:Bot, state: FSMContext):
    await night_actions.xoyin_action_handler(call, bot, state)

@router.callback_query(F.data.startswith(RoleNames.ZANJIR))
async def f(call: CallbackQuery, bot:Bot, state: FSMContext):
    await night_actions.zanjir_action_handler(call, bot, state)

@router.callback_query(F.data.startswith("vote"))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await day_actions.vote_target_handler(call=call, bot=bot, state=state)

@router.callback_query(F.data.startswith("like"))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await game_logic.handle_vote_like(call=call, bot=bot, state=state)

@router.callback_query(F.data.startswith("dislike"))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await game_logic.handle_vote_like(call=call, bot=bot, state=state)

@router.callback_query(F.data.startswith(RoleNames.DAYDI))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await night_actions.daydi_action_handler(call, bot, state)

@router.callback_query(F.data.startswith(RoleNames.KEZUVCHI))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await night_actions.kezuv_action_handler(call, bot, state)

@router.callback_query(F.data.startswith(RoleNames.ADVOKAT))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await night_actions.advokat_action_handler(call, bot, state)

@router.callback_query(F.data.startswith(RoleNames.QOTIL))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await night_actions.qotil_action_handler(call, bot, state)

@router.message(NightSheriklarMessages())
async def f(message: Message, bot: Bot, state: FSMContext):
    await night_actions.night_sheriklar_msg(message, bot, state)

@router.callback_query(F.data.startswith(RoleNames.OVCHI))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await night_actions.ovchi_action_handler(call, bot, state)

@router.callback_query(F.data.startswith(RoleNames.GAZABDOR))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await night_actions.gazabdor_action_handler(call, bot, state)

@router.callback_query(F.data.startswith(RoleNames.AFERIST))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await night_actions.aferist_action_handler(call, bot, state)

@router.callback_query(F.data.startswith("sehrgar_"))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await night_actions.sehr_action_handler(call, bot, state)

@router.callback_query(F.data.startswith(RoleNames.SEHRGAR))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await night_actions.sehrgar_night_action_handler(call, bot, state)

@router.callback_query(F.data.startswith(RoleNames.JURNALIST))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await night_actions.jurnalist_action_handler(call, bot, state)

@router.callback_query(F.data.startswith(RoleNames.SOTQIN))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await night_actions.sotqin_action_handler(call, bot, state)

@router.callback_query(F.data.startswith("karta_"))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await day_actions.select_card_handler(call=call, bot=bot, state=state)

@router.callback_query(F.data.startswith(RoleNames.AYGOQCHI))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await night_actions.aygoqchi_action_handler(call=call, state=state, bot=bot)

@router.callback_query(F.data.startswith(RoleNames.KONCHI))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await night_actions.konchi_action_handler(call, bot, state)

@router.callback_query(F.data.startswith(RoleNames.REVERSER))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await night_actions.reverser_action_handler(call, bot, state)

@router.callback_query(F.data.startswith(RoleNames.TAQLIDCHI))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await night_actions.taqlidchi_action_handler(call, bot, state)
