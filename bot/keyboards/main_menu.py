from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📅 Расписание мероприятий")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
