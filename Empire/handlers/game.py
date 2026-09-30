from aiogram import Router, Bot, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, CallbackQuery
from utils import game_logic, night_actions, day_actions, start
from utils import qora_materiya as qm
from filters.more import DelCommands, NightSheriklarMessages, SayLastWordFilter
from utils.role_names import RoleNames
from aiogram.fsm.context import FSMContext
from utils import others
from utils.redis_game.handler_wrappers import (
    create_game_handler_wrapper,
    create_vs_game_handler_wrapper,
    join_game_handler_wrapper,
    kick_player_wrapper,
    leave_game_wrapper,
    stop_game_handler_wrapper,
    start_game_handler_wrapper
)

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


@router.message(Command("start"), F.chat.type == "private")
async def f(message: Message, bot: Bot, state: FSMContext, command: CommandObject):
    args = command.args  # "buy_star_10" yoki None

    if await start.ensure_onboarded_or_defer(message, state, args):
        return

    if args and "buy_star_" in args:
        await others.process_buy_star_main_bot(message=message, args=args)
    elif args and len(args.split("_")) > 1:
        await join_game_handler_wrapper(message, bot, state=state)
    else:
        await start.start_msg_handler(message)

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

@router.callback_query(F.data.startswith(qm.QM_VS_SELECT))
async def f(call: CallbackQuery, bot: Bot):
    await qm.qm_voidswap_select(call, bot)

@router.callback_query(F.data.startswith(qm.QM_VS_PICK))
async def f(call: CallbackQuery, bot: Bot):
    await qm.qm_voidswap_pick(call, bot)

@router.callback_query(F.data.startswith(qm.QM_PORTLAT))
async def f(call: CallbackQuery, bot: Bot):
    await qm.qm_portlatish(call, bot)

@router.callback_query(F.data.startswith(qm.QM_TIR_SELECT))
async def f(call: CallbackQuery, bot: Bot):
    await qm.qm_tiriltir_select(call, bot)

@router.callback_query(F.data.startswith(qm.QM_TIR_PICK))
async def f(call: CallbackQuery, bot: Bot):
    await qm.qm_tiriltir_pick(call, bot)

@router.callback_query(F.data.startswith(qm.QM_XAZINA_NUM))
async def f(call: CallbackQuery, bot: Bot):
    await qm.qm_xazina_pick(call, bot)

@router.callback_query(F.data.startswith(qm.QM_XAZINA))
async def f(call: CallbackQuery, bot: Bot):
    await qm.qm_xazina_start(call, bot)

@router.callback_query(F.data == "qm_noop")
async def f(call: CallbackQuery):
    await call.answer()

@router.callback_query(F.data.startswith("jin_choice_"))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await night_actions.jin_choice_handler(call, bot, state)

@router.callback_query(F.data.startswith("jin-victim_"))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await night_actions.jin_victim_handler(call, bot, state)

@router.callback_query(F.data.startswith(RoleNames.JIN))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await night_actions.jin_action_handler(call, bot, state)

@router.message(Command("ngame"))
async def f(message: Message, bot: Bot):
    await game_logic.create_nick_game_handler(message, bot)

@router.message(Command("extend"))
async def f(message: Message, bot: Bot):
    await game_logic.extend_game_timer(message, bot)

