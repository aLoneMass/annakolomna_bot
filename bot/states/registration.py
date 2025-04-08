from aiogram.fsm.state import StatesGroup, State

class RegistrationState(StatesGroup):
    choosing_event = State()
    confirming_child = State()  # 🆕 новое состояние
    entering_child_name = State()
    entering_allergy_info = State()
    confirming_comment = State()
    waiting_for_payment_check = State()
    

