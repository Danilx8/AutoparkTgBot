from aiogram.fsm.state import StatesGroup, State


class Authorization(StatesGroup):
    start = State()
    success = State()
    fail = State()
