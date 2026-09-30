from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery
from aiogram.filters import Command
from utils import geroylar_game, geroylar_user, geroy_market
from aiogram.fsm.context import FSMContext
from states.game_states import GeroyNameState

router = Router()

@router.callback_query(F.data == "my_geroy")
async def f(call: CallbackQuery):
    await geroylar_user.my_geroy_info_handler(call=call)

@router.message(Command("geroyinfo"))
async def f(message: Message):
    await geroylar_user.geroy_info_handler(message=message)

@router.message(F.text.startswith("/tgeroy"))
async def f(message: Message):
    await geroylar_user.transfer_geroy(message=message)

@router.message(Command("geroy"))
async def f(message: Message):
    await geroylar_user.give_geroy_from_admin(message=message)

@router.message(Command("rgeroy"))
async def f(message: Message):
    await geroylar_user.remove_geroy_from_admin(message=message)

@router.callback_query(F.data.startswith("geroy_"))
async def f(call: CallbackQuery, state: FSMContext):
    await geroylar_user.geroy_shop(call=call, state=state)

@router.message(GeroyNameState.waiting_for_name)
async def f(message: Message, state: FSMContext):
    await geroylar_user.process_new_geroy_name(message=message, state=state)

@router.callback_query(F.data.startswith("game-geroy_attack_"))
async def f(call: CallbackQuery, state: FSMContext):
    await geroylar_game.geroy_attack_type_handler(call=call, state=state)

@router.callback_query(F.data.startswith("game-geroy_skype"))
async def f(call: CallbackQuery, state: FSMContext):
    await geroylar_game.geroy_skip_handler(call=call, state=state)

@router.callback_query(F.data.startswith("game-geroy-attack_"))
async def f(call: CallbackQuery, state: FSMContext):
    await geroylar_game.geroy_attack_handler(call=call, state=state)

@router.callback_query(F.data.startswith("game-geroy_shield_"))
async def f(call: CallbackQuery, state: FSMContext):
    await geroylar_game.geroy_shield_handler(call=call, state=state)

@router.callback_query(F.data == "add_my_geroy_market")
async def f(call: CallbackQuery, state: FSMContext):
    await geroy_market.add_my_geroy_market(call=call, state=state)

@router.message(geroy_market.GeroyMarketPrice.waiting_for_price)
async def f(message: Message, state: FSMContext):
    await geroy_market.process_geroy_market_price(message=message, state=state)

@router.callback_query(F.data.startswith("market-geroy-buy_"))
async def f(call: CallbackQuery, bot: Bot):
    await geroy_market.buy_geroy_market(call=call, bot=bot)

@router.message(F.text.startswith("/gmstats"))
async def f(message: Message):
    await geroy_market.stats_geroy_market(message=message)


