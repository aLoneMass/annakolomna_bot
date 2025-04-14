from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton




def get_event_navigation_keyboard_with_signup(index: int, total: int) -> InlineKeyboardMarkup:
    buttons = []

    nav_row = []
    if index > 0:
        nav_row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"prev_{index}"))
    if index < total - 1:
        nav_row.append(InlineKeyboardButton(text="▶️ Далее", callback_data=f"next_{index}"))
    if nav_row:
        buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton(text="✅ Записаться", callback_data=f"signup_{index}")
    ])
    buttons.append([
        InlineKeyboardButton(text="❌ Закрыть", callback_data="close")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

