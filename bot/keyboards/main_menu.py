from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_inline_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Расписание мероприятий", callback_data="show_schedule")]
        ]
    )
