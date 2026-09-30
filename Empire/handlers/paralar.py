from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from utils import paralar
from config import ADMINS
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

router = Router()

class ParaGiftState(StatesGroup):
    waiting_for_amount = State()

class AnonymousChatState(StatesGroup):
    chatting = State()

@router.message(Command("para"))
async def f(message: Message, bot: Bot):
    await paralar.add_para_request(message)

@router.message(Command("mypara"))
async def f(message: Message, bot: Bot):
    await paralar.check_my_para(message)

@router.callback_query(F.data.startswith("para_"))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    if call.data.startswith("para_send_"):
        await paralar.start_para_gift(call, state)
    elif call.data == "para_chat_start":
        await paralar.para_chat_request(call, bot, state)
    elif call.data.startswith("para_chat_accept_"):
        requester_id = int(call.data.replace("para_chat_accept_", ""))
        await paralar.para_chat_respond(call, bot, state, "accept", requester_id)
    elif call.data.startswith("para_chat_decline_"):
        requester_id = int(call.data.replace("para_chat_decline_", ""))
        await paralar.para_chat_respond(call, bot, state, "decline", requester_id)
    else:
        await paralar.accept_para(call)

@router.message(Command("dpara"))
async def f(message: Message, bot: Bot):
    await paralar.del_my_para(message)

@router.callback_query(F.data == "my_para_menu")
async def f(call: CallbackQuery, state: FSMContext):
    await paralar.show_para_gift_menu(call)

@router.message(ParaGiftState.waiting_for_amount)
async def f(message: Message, state: FSMContext):
    await paralar.process_para_gift(message, state)

@router.callback_query(F.data.startswith("gender_select_"))
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    gender = call.data.split("_")[-1]  # "m" yoki "f"
    if gender in ("m", "f"):
        await paralar.select_gender(call, gender, state=state)

@router.callback_query(F.data == "gender_menu_open")
async def f(call: CallbackQuery, bot: Bot, state: FSMContext):
    await paralar.open_gender_menu(call)

@router.message(Command("rpara"))
async def f(message: Message, bot: Bot):
    await paralar.find_random_para_command(message, bot)

@router.callback_query(F.data == "find_random_para")
async def f(call: CallbackQuery, bot: Bot):
    await paralar.find_random_para(call, bot)

from aiogram.filters import StateFilter

@router.message(StateFilter("*"), F.text.in_(["❌ Suhbatni yopish", "/stopchat", "/stop_chat", "/endchat", "❌ Suhbatni tugatish", "Suhbatni yopish"]), F.chat.type == "private")
@router.message(StateFilter("*"), Command("stopchat", "stop_chat", "endchat"), F.chat.type == "private")
async def close_anon_chat_handler(message: Message, state: FSMContext, bot: Bot):
    await paralar.para_chat_close_action(user_id=message.from_user.id, bot=bot, state=state, send_notification=True)

@router.callback_query(StateFilter("*"), F.data == "para_chat_close")
async def close_anon_chat_cb(call: CallbackQuery, state: FSMContext, bot: Bot):
    await call.answer()
    await paralar.para_chat_close_action(user_id=call.from_user.id, bot=bot, state=state, send_notification=True)

@router.message(AnonymousChatState.chatting, F.chat.type == "private")
async def f(message: Message, state: FSMContext, bot: Bot):
    await paralar.para_chat_relay(message, state, bot)
    