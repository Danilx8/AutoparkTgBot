from aiogram.fsm.state import StatesGroup, State


class Authorization(StatesGroup):
    start = State()
    success = State()


class Mileage(StatesGroup):
    start = State()
    interval_input = State()
    dates_input = State()
