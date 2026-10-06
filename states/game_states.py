from aiogram.fsm.state import State, StatesGroup

class GeroyNameState(StatesGroup):
    waiting_for_name = State()  