from aiogram.fsm.state import State, StatesGroup

class AdminEmojiStates(StatesGroup):
    waiting_for_emoji = State()

class AdminMemeStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_sticker = State()
