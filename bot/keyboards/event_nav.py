from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_event_navigation_keyboard(event_index: int, total_events: int):
    buttons = []

    # Назад
    if event_index > 0:
        buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"event_{event_index - 1}"))
    else:
        buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data="disabled"))

    # Далее
    if event_index < total_events - 1:
        buttons.append(InlineKeyboardButton(text="▶️ Далее", callback_data=f"event_{event_index + 1}"))
    else:
        buttons.append(InlineKeyboardButton(text="▶️ Далее", callback_data="disabled"))

    # Записаться и Выход
    buttons_bottom = [
        InlineKeyboardButton(text="✅ Записаться", callback_data=f"signup_{event_index}"),
        InlineKeyboardButton(text="❌ Выход", callback_data="exit")
    ]

    return InlineKeyboardMarkup(inline_keyboard=[buttons, buttons_bottom])
