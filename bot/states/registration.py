from aiogram.fsm.state import StatesGroup, State

class RegistrationState(StatesGroup):
    choosing_event = State()
    confirming_child = State()  
    entering_child_name = State()
    entering_allergy_info = State()
    confirming_comment = State()
    entering_birth_date = State()  # 🆕 новое состояние
    waiting_for_payment_check = State()
    notify_admins_about_registration = State()
    create_event = State()
    

    

