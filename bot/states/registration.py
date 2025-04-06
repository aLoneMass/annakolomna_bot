from aiogram.fsm.state import StatesGroup, State

class RegistrationState(StatesGroup):
    entering_child_name = State()
    entering_allergy_info = State()
    waiting_for_payment_check = State()
