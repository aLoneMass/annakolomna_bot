from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_inline_keyboard(): #Объявление функции. Она не принимает аргументов и возвращает клавиатуру с кнопкой
    return InlineKeyboardMarkup( #Возвращает объект InlineKeyboardMarkup — это встроенная клавиатура, которая отображается прямо под сообщением, а не внизу чата, как обычная
        inline_keyboard=[ #Параметр inline_keyboard принимает список списков кнопок, каждая вложенность — это отдельный ряд кнопок.
            [InlineKeyboardButton(text="📅 Расписание мероприятий", callback_data="show_schedule")] #Создаётся одна кнопка: text="📅 Расписание мероприятий" — то, что пользователь увидит на кнопке.
        ]                                                                                           #callback_data="show_schedule" — значение, которое будет отправлено боту при нажатии, для последующей обработки через CallbackQueryHandler.
    )


"""
CallbackQueryHandler — это обработчик (handler) для кнопок встроенной клавиатуры (InlineKeyboardButton), у которых задан параметр callback_data.

Он реагирует не на обычные сообщения, а на "нажатие кнопки" в сообщении, и позволяет выполнять соответствующее действие.
"""