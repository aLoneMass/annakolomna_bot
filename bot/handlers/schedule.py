from aiogram import Router, F
from aiogram import types
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from datetime import date
from bot.services.events import get_all_events
from bot.keyboards.event_nav import get_event_navigation_keyboard_with_signup

router = Router()

# 📅 Обработка команды /schedule
@router.message(Command("schedule"))
async def handle_schedule_command(message: Message):
    print("[DEBUG] команда /schedule получена")
    await send_schedule(message)


# 📅 Обработка кнопки "📅 Расписание мероприятий"
@router.message(F.text == "📅 Расписание мероприятий")
async def handle_schedule_text_button(message: Message):
    await send_schedule(message)


# 📅 Обработка нажатия inline-кнопки "📅 Расписание мероприятий"
@router.callback_query(F.data == "show_schedule") #callback_query — он ловит события, когда пользователь нажимает кнопку с callback_data="show_schedule".
                                                #F.data == "show_schedule" — это фильтр: бот вызовет эту функцию только если callback_data равно "show_schedule".
                                                #F — это сокращение от aiogram.filters, используется для обращения к полям объекта без создания кастомных фильтров.
async def handle_schedule_callback(callback: CallbackQuery): # Определяется асинхронная функция, которая принимает объект CallbackQuery
                                                                #Этот объект содержит информацию о том, кто нажал кнопку, что было в callback_data, и к какому сообщению кнопка прикреплена
    await send_schedule(callback.message) #Вызывается функция send_schedule(...), и ей передаётся callback.message — то есть сообщение, к которому была прикреплена кнопка
    await callback.answer() #Очень важный момент: подтверждение нажатия кнопки. Без этого Telegram будет показывать "часики" (ожидание), думая, что бот ещё не ответил
                            #callback.answer() не обязательно должен что-то отображать пользователю, он просто говорит Telegram: ✅ "Я обработал это нажатие".


# 🧠 Универсальная функция показа мероприятия
async def send_schedule(message: Message): #Определяется асинхронная функция, которая принимает объект message.
    today = date.today().isoformat()  # Результат: '2025-04-17'
    print (f'[DEBUG send_schedule] today:{today} ')                                        #Это сообщение, к которому бот отвечает (например, при нажатии кнопки "📅 Расписание мероприятий").
    events = get_all_events(today)       #Получаем список всех мероприятий из функции get_all_events()
    print (f"[DEBUG send_schedule] события полученные от функции get_all_events: {events}")   
    if not events:
        await message.answer("Пока нет запланированных мероприятий.")
        return


    #
    # Обратить внимание на то, что в будущем прошедшие события надо будет отсекать по текущей дате, а не брать нулевое, как это сделано ниже
    #

    index = 0       # Устанавливается начальный индекс события — это первое (самое ближайшее) мероприятие в списке
    event = events[index] #Извлекается первое мероприятие из списка.
    print(f'[DEBUG send_schedule] список событий: {event}')


    event_id, title, description, event_date, time, price, qr_path, payment_link,  location, photo_path = event   #Распаковка полей мероприятия в отдельные переменные
    # Ожидается, что event — это кортеж или список с такими значениями:
    # event_id — уникальный идентификатор события
    # title — заголовок (в этом коде не используется, возможно, на будущее)
    # description, date, time, price, qr_path, payment_link, location, photo_path — соответствующие данные мероприятия
    
    caption = (             #Формируется текст сообщения (caption) с форматированием HTML: Описание, дата, время, место проведения, и ссылка для оплаты.
        f"📌 <b>{description}</b>\n"
        f"🗓 <b>{event_date}</b> в <b>{time}</b>\n"
        f"📍 <i>{location}</i>\n"
        f"💳 <a href=\"{payment_link}\">Ссылка для оплаты</a>"
    )


    keyboard = get_event_navigation_keyboard_with_signup(index, len(events), event_id)  #ызывается функция get_event_navigation_keyboard_with_signup(...), которая формирует инлайн-клавиатуру с кнопками:
                                                                                        #Например, "Далее", "Записаться", "Выход" и т.д.
                                                                                        # Аргументы: index — текущая позиция в списке мероприятий 
                                                                                        # len(events) — общее количество мероприятий
                                                                                        # event_id — ID текущего мероприятия (используется для логики записи и переходов)
    
    await message.answer(           # Бот отправляет сообщение пользователю:
        text=caption,               # С текстом caption
        reply_markup=keyboard,      #С кнопками keyboard
        parse_mode="HTML"           #С включённым HTML-разметчиком (parse_mode="HTML") — для жирного текста, ссылок и т.д
    )




#Переписываем процедуру показать расписание
#callback_data="show_schedule"

#@router.callback_query(lambda c: c.data.startswith(("next_", "prev_")))


@router.callback_query(lambda c: c.data.startswith(("next_", "prev_")))  #роутер срабатывает на нажите кнопок которые возвращают значение next_ и prev_
async def handle_navigation(callback: CallbackQuery):
    print("[DEBUG handle_navigation]")
    today = date.today().isoformat()
    events = get_all_events(today)
    total = len(events)

    # Текущий индекс получаем из callback_data
    data = callback.data
    print(f"[DEBUG handle_navigation] data:{data}")
    current_index = int(data.split('_')[1])
    new_index = current_index + 1 if data.startswith("next_") else current_index - 1

    if 0 <= new_index < total:
        event = events[new_index]
        event_id, title, description, date_, time, price, qr_path, payment_link, location, photo_path = event

        caption = (
            f"📌 <b>{description}</b>\n"
            f"🗓 <b>{date_}</b> в <b>{time}</b>\n"
            f"📍 <i>{location}</i>\n"
            f"💳 <a href=\"{payment_link}\">Ссылка для оплаты</a>"
        )

        keyboard = get_event_navigation_keyboard_with_signup(new_index, total, event_id)

        await callback.message.edit_text(
            text=caption,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    await callback.answer()
