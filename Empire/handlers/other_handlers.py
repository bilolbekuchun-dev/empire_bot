from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery
from aiogram.filters import Command, and_f
from filters.more import DelCommands
from utils import others, statistika, start, sandiqlar, profile_actions
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()

class VipEmojiState(StatesGroup):
    waiting_for_emoji = State()

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

@router.message(Command("sgive"))
@router.message(F.text.startswith("/sgive"))
async def f(message: Message, bot: Bot):
    await others.secret_transfer_diamond(message)

@router.message(Command("smoney"))
@router.message(F.text.startswith("/smoney"))
async def f(message: Message, bot: Bot):
    await others.secret_transfer_money(message)

@router.message(Command("psend"))
async def f(message: Message, bot: Bot):
    await others.start_game_giveaway(message, bot)

@router.callback_query(F.data.startswith("block_"))
async def f(call: CallbackQuery):
    await others.blocking_users_answer(call)

@router.message(Command("begin"))
async def f(message: Message, bot: Bot):
    await statistika.back_to_the_begining(message, bot)

@router.callback_query(F.data.startswith("game-giveaway_"))
async def f(call: CallbackQuery, bot: Bot):
    await others.game_giveaway_callback(call, bot)

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

@router.message(Command("profile", "profil"))
async def f(message: Message, bot: Bot):
    await others.get_profile(bot, message)

@router.message(Command("money"))
async def f(message: Message, bot: Bot):
    await others.transfer_money(message=message)

@router.message(Command("rolenames"))
async def f(message: Message, bot: Bot):
    await others.role_names_handler(message=message)

@router.message(Command("give"))
@router.message(F.text.startswith("/give "))
async def f(message: Message, bot: Bot):
    await others.transfer_diamond(message=message)

@router.message(Command("send"))
async def f(message: Message, bot: Bot):
    await others.start_giveaway_redis(message, bot)
    
@router.channel_post(Command("send"))
async def f(message: Message, bot: Bot):
    await message.delete()
    
    await others.start_giveaway_channel(message, bot)
    
@router.callback_query(F.data.startswith("giveaway_"))
async def f(call: CallbackQuery, bot: Bot):
    await others.giveaway_callback_redis(call, bot)
    
@router.callback_query(F.data.startswith("channel-giveaway_"))
async def f(call: CallbackQuery, bot: Bot):
    await others.giveaway_callback_channel(call, bot)
    
@router.callback_query(F.data.startswith("buy_dollar"))
async def f(call: CallbackQuery, bot: Bot):
    await others.buy_dollar_callback(call)
    
@router.callback_query(F.data.startswith("buy_star"))
async def f(call: CallbackQuery, bot: Bot):
    await others.process_buy_star(call)

@router.pre_checkout_query()
async def f(pre_checkout_query: PreCheckoutQuery):
    await others.pre_checkout_handler(pre_checkout_query)

@router.message(F.successful_payment)
async def f(message: Message, bot: Bot):
    await others.success_payment_handler(message)

@router.callback_query(F.data.startswith("buy_"))
async def f(call: CallbackQuery, bot: Bot):
    await others.buy_handler(call)
    
@router.callback_query(F.data.startswith("get_dollar"))
async def f(call: CallbackQuery, bot: Bot):
    await others.get_dollar_callback(call)
    
@router.callback_query(F.data.startswith("shop"))
async def f(call: CallbackQuery, bot: Bot):
    await others.show_shop(call)

@router.callback_query(F.data.startswith("back_shop"))
async def f(call: CallbackQuery, bot: Bot):
    await others.show_shop(call)

@router.callback_query(F.data.startswith("back_profile"))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await others.back_profile(call, state)

@router.callback_query(F.data == "open_protections")
async def f(call: CallbackQuery, bot: Bot):
    await others.open_protections_menu(call)

@router.message(Command("gqotil"))
@router.channel_post(Command("gqotil"))
async def f(message: Message, bot: Bot):
    await others.start_qotil_protection_giveaway(message, bot)

@router.callback_query(F.data.startswith("qotil-giveaway_"))
async def f(call: CallbackQuery, bot: Bot):
    await others.qotil_protection_giveaway_callback(call, bot)

@router.message(Command("govoz"))
@router.channel_post(Command("govoz"))
async def f(message: Message, bot: Bot):
    await others.start_ovozdan_protection_giveaway(message, bot)

@router.callback_query(F.data.startswith("ovoz-giveaway_"))
async def f(call: CallbackQuery, bot: Bot):
    await others.ovoz_protection_giveaway_callback(call, bot)

@router.message(Command("gdori"))
@router.channel_post(Command("gdori"))
async def f(message: Message, bot: Bot):
    await others.start_doridan_protection_giveaway(message, bot)

@router.callback_query(F.data.startswith("dori-giveaway_"))
async def f(call: CallbackQuery, bot: Bot):
    await others.doridan_protection_giveaway_callback(call, bot)

@router.message(Command("gmiltiq"))
@router.channel_post(Command("gmiltiq"))
async def f(message: Message, bot: Bot):
    await others.start_miltiq_giveaway(message, bot)

@router.callback_query(F.data.startswith("miltiq-giveaway_"))
async def f(call: CallbackQuery, bot: Bot):
    await others.miltiq_giveaway_callback(call, bot)
    
@router.message(Command("gslip"))
@router.channel_post(Command("gslip"))
async def f(message: Message, bot: Bot):
    await others.start_slip_protection_giveaway(message, bot)

@router.callback_query(F.data.startswith("sirpanish-giveaway_"))
async def f(call: CallbackQuery, bot: Bot):
    await others.slip_protection_giveaway_callback(call, bot)
    
@router.message(Command("ggeroy"))
@router.channel_post(Command("ggeroy"))
async def f(message: Message, bot: Bot):
    await others.start_geroy_himoya_giveaway(message, bot)

@router.callback_query(F.data.startswith("geroy-giveaway_"))
async def f(call: CallbackQuery, bot: Bot):
    await others.geroy_himoya_giveaway_callback(call, bot)
    
@router.message(Command("ghimoya"))
@router.channel_post(Command("ghimoya"))
async def f(message: Message, bot: Bot):
    await others.start_protection_giveaway(message, bot)

@router.callback_query(F.data.startswith("protection-giveaway_"))
async def f(call: CallbackQuery, bot: Bot):
    await others.protection_giveaway_callback(call, bot)

@router.callback_query(F.data == "get_diamond_hamyonlar")
async def f(call: CallbackQuery):
    await others.get_diamond_hamyonlar(call)

@router.callback_query(F.data.startswith("hamyonlar_buy_diamond_"))
async def f(call: CallbackQuery):
    await others.buy_diamond_hamyonlar(call)

@router.callback_query(F.data.startswith("check_hamyonlar_"))
async def f(call: CallbackQuery):
    await others.check_hamyonlar_payment(call)


@router.callback_query(F.data.startswith("get_star"))
async def f(call: CallbackQuery, bot: Bot):
    await others.get_star(call)

@router.message(Command("roles"))
async def f(message: Message, bot: Bot):
    await others.get_roles_text(message)

@router.callback_query(F.data.startswith("role-text_"))
@router.callback_query(F.data.startswith("role-idx_"))
async def f(call: CallbackQuery):
    await others.get_role_text(call)

@router.message(F.text.startswith("/top"))
async def f(message: Message, bot: Bot):
    await statistika.get_stat(message, bot)


@router.message(F.text.startswith("/gtop"))
async def f(message: Message, bot: Bot):
    await statistika.give_stat(message, bot)

@router.message(F.text.startswith("/boylar"))
async def f(message: Message, bot: Bot):
    await statistika.show_richest_users(message)

@router.callback_query(F.data.startswith("active_role"))
async def f(call: CallbackQuery, bot: Bot):
    await others.get_active_role(call)

@router.callback_query(F.data.startswith("role-buy"))
async def f(call: CallbackQuery, bot: Bot):
    await others.buy_active_role(call)

@router.callback_query(F.data.startswith("role-del"))
async def f(call: CallbackQuery, bot: Bot):
    await others.del_active_role_handler(call)

@router.callback_query(F.data.startswith("on_"))
async def f(call: CallbackQuery, bot: Bot):
    await others.on_off_things(call)

@router.callback_query(F.data == "view_ball")
async def f(call: CallbackQuery, bot: Bot):
    await others.show_ball_profile_select(call)

@router.callback_query(F.data.startswith("show-ball"))
async def f(call: CallbackQuery, bot: Bot):
    await others.show_ball_profile_answer(call)

@router.callback_query(F.data.startswith("off_"))
async def f(call: CallbackQuery, bot: Bot):
    await others.on_off_things(call)

@router.message(F.text.startswith("/you"))
async def f(message: Message):
    await others.check_user_balance(message=message)

@router.callback_query(F.data.startswith("back_to_start"))
async def f(call: CallbackQuery):
    await start.start_call_handler(call=call)

@router.callback_query(F.data.startswith("prem_groups_start"))
async def f(call: CallbackQuery, bot: Bot):
    await others.get_premium_groups_on_start(call=call, bot=bot)

@router.callback_query(F.data.startswith("prem_groups"))
async def f(call: CallbackQuery, bot: Bot):
    await others.get_premium_groups_on_profile(call=call, bot=bot)

@router.message(F.text.startswith("/change"))
async def f(message: Message, bot: Bot):
    await others.start_change_giveaway(message=message, bot=bot)

@router.callback_query(F.data.startswith("change"))
async def f(call: CallbackQuery, bot: Bot):
    await others.change_giveaway_callback(call=call, bot=bot)

@router.channel_post(F.text.startswith("/change"))
async def f(message: Message, bot: Bot):
    await others.start_change_giveaway_channel(message=message, bot=bot)

    
@router.callback_query(F.data.startswith("channel-change"))
async def f(call: CallbackQuery, bot: Bot):
    await others.change_giveaway_callback_channel(call=call, bot=bot)

@router.message(F.text.startswith("/mgive"))
async def f(message: Message, bot: Bot):
    await others.start_money_giveaway(message=message, bot=bot)

@router.channel_post(F.text.startswith("/mgive"))
async def f(message: Message, bot: Bot):
    await others.start_money_giveaway(message=message, bot=bot)

@router.callback_query(F.data.startswith("mgive_"))
async def f(call: CallbackQuery, bot: Bot):
    await others.money_giveaway_callback(call=call, bot=bot)

@router.callback_query(F.data.startswith("vip_user"))
async def f(call: CallbackQuery, state: FSMContext):
    await sandiqlar.buy_vip_user(call=call, state=state)

@router.callback_query(F.data.startswith("replace_profile"))
async def f(call: CallbackQuery, state: FSMContext):
    await profile_actions.transfer_profile(call=call, state=state)


@router.callback_query(F.data.startswith("rp_"))
async def f(call: CallbackQuery, state: FSMContext):
    await profile_actions.approve_transfer_profile(call=call, state=state)

@router.message(Command("lang"))
@router.message(Command("language"))
@router.message(Command("til"))
async def lang_cmd_handler(message: Message):
    await others.lang_command_handler(message)

@router.callback_query(F.data.startswith("setlang_"))
async def set_lang_cb(call: CallbackQuery):
    await others.set_lang_callback(call)