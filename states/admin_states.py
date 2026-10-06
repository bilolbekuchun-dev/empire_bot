from aiogram.fsm.state import State, StatesGroup

class AdminEmojiStates(StatesGroup):
    waiting_for_emoji = State()

class AdminSubStates(StatesGroup):
    waiting_for_channel = State()

class AdminBroadcastStates(StatesGroup):
    waiting_for_message = State()


