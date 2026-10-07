from aiogram.fsm.state import State, StatesGroup

class AdminEmojiStates(StatesGroup):
    waiting_for_emoji = State()
