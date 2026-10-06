from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from utils import chat_settings

router = Router()

@router.message(Command("sozlamalar"))
async def f(message: Message, bot: Bot):
    await chat_settings.send_settings_to_admin(message, bot)

@router.callback_query(F.data.startswith("del_msg"))
async def f(call: CallbackQuery, bot: Bot):
    await call.message.delete()

@router.callback_query(F.data == "ignore")
async def f(call: CallbackQuery, bot: Bot):
    await call.answer()

@router.callback_query(F.data.startswith("set-time_"))
async def f(call: CallbackQuery):
    await chat_settings.open_set_time_answer(call)

@router.callback_query(F.data.startswith("set-weapons_"))
async def f(call: CallbackQuery):
    await chat_settings.open_set_weapons_answer(call)

@router.callback_query(F.data.startswith("set-more_"))
async def f(call: CallbackQuery):
    await chat_settings.open_set_more_answer(call)

@router.callback_query(F.data.startswith("set-roles_"))
async def f(call: CallbackQuery):
    await chat_settings.open_set_role_answer(call)

@router.callback_query(F.data.startswith("show-settings_"))
async def f(call: CallbackQuery):
    await chat_settings.show_settings_handler(call)

@router.callback_query(F.data.startswith("set-leave_"))
async def f(call: CallbackQuery):
    await chat_settings.set_leave_action_handler(call)

@router.callback_query(F.data.startswith("set-give_"))
async def f(call: CallbackQuery):
    await chat_settings.open_set_give_answer(call)
@router.callback_query(F.data.startswith("set-cmdperm_"))
async def f(call: CallbackQuery):
    await chat_settings.open_set_command_permissions(call)

@router.callback_query(F.data.startswith("set-wgroupperm_"))
async def f(call: CallbackQuery):
    await chat_settings.open_set_write_group_perm_answer(call)

@router.message(Command("gsend"))
@router.message(F.text.startswith("/gsend"))
async def f(message: Message):
    await chat_settings.add_diamond_group_balance(message)

@router.message(Command("ginfo"))
@router.message(F.text == "/ginfo")
async def f(message: Message, bot: Bot):
    await chat_settings.group_info_handler(message=message, bot=bot)

@router.callback_query(F.data.startswith("set-gmode_"))
async def f(call: CallbackQuery):
    await chat_settings.open_set_game_mode(call)
