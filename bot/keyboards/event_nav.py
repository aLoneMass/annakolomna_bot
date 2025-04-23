from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from schedule import get_dates_for_event


def get_event_navigation_keyboard(index: int, total: int, event_id: int) -> InlineKeyboardMarkup:

    dates = get_dates_for_event(event_id)

    date_buttons = [
        [InlineKeyboardButton(text=f"📅 {d}", callback_data=f"date_{event_id}_{d}")]
        for d in dates
    ]
    buttons = []
    nav_row = []
    if total-1 == 0:
        print('мероприятие одно, кнопки навигации не добавляем')
    elif (index == 0) and (index < total - 1):
        nav_row.append(InlineKeyboardButton(text="▶️ Далее", callback_data=f"next_{index}"))
    elif (index > 0) and (index < total-1):
        nav_row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"prev_{index}"))
        nav_row.append(InlineKeyboardButton(text="▶️ Далее", callback_data=f"next_{index}"))
    elif (index == total-1) and (total > 0):
        nav_row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"prev_{index}"))
    buttons.append(nav_row)

    # buttons.append([
    #     InlineKeyboardButton(text="✅ Записаться", callback_data=f"signup_event:{event_id}")
    # ])
    buttons.append([
        InlineKeyboardButton(text="❌ Закрыть", callback_data="close")
    ])

    return InlineKeyboardMarkup(inline_keyboard=date_buttons + [buttons] if buttons else date_buttons)

