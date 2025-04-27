# bot/states/admin.py
from aiogram.fsm.state import State, StatesGroup

class AdminCreateEventState(StatesGroup):
    title = State()
    description = State()
    photo = State()
    qr = State()
    payment_link = State()
    location = State()
    price = State()
    event_dates = State()
    event_times = State()
    confirm = State()
    