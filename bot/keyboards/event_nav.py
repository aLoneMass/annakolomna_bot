import sqlite3
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram import Router, F
from aiogram.types import CallbackQuery
from config import DB_PATH
from bot.handlers.registration import handle_signup_event
from aiogram.fsm.context import FSMContext
from types import SimpleNamespace

#from bot.handlers.schedule import get_dates_for_event


router = Router()

# def get_event_navigation_keyboard(index: int, total: int, event_id: int) -> InlineKeyboardMarkup:

#     dates = get_dates_for_event(event_id)
#     print(f"[DEBUG get_event_navigation_keyboard] dates:{dates}")

#     date_buttons = [
#         [InlineKeyboardButton(text=f"📅 {d}", callback_data=f"date_{event_id}_{d}")]
#         for d in dates
#     ]
#     print(f"[DEBUG get_event_navigation_keyboard] date_buttons:{date_buttons}")
#     buttons = []
#     nav_row = []
#     if total-1 == 0:
#         print('мероприятие одно, кнопки навигации не добавляем')
#     elif (index == 0) and (index < total - 1):
#         nav_row.append(InlineKeyboardButton(text="▶️ Далее", callback_data=f"next_{index}"))
#     elif (index > 0) and (index < total-1):
#         nav_row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"prev_{index}"))
#         nav_row.append(InlineKeyboardButton(text="▶️ Далее", callback_data=f"next_{index}"))
#     elif (index == total-1) and (total > 0):
#         nav_row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"prev_{index}"))
#     buttons.append(nav_row)

#     # buttons.append([
#     #     InlineKeyboardButton(text="✅ Записаться", callback_data=f"signup_event:{event_id}")
#     # ])
#     buttons.append([
#         InlineKeyboardButton(text="❌ Закрыть", callback_data="close")
#     ])

#     if buttons:
#         date_buttons.append(buttons)

#     return InlineKeyboardMarkup(inline_keyboard=date_buttons )

def get_dates_for_event(event_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT date FROM events
            WHERE template_id = ?
            ORDER BY date;
        """, (event_id,))
        rows = cursor.fetchall()
        return [r[0] for r in rows]


def get_times_for_event_on_date(event_id: int, date_str: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT time FROM events
            WHERE template_id = ? AND date = ?
            ORDER BY time;
        """, (event_id, date_str))
        rows = cursor.fetchall()
        return [r[0] for r in rows]


def get_event_navigation_keyboard(event_index: int, total_events: int, event_id: int):
    dates = get_dates_for_event(event_id)
    print(F"[DEBUG get_event_navigation_keyboard] dates:\n {dates}")

    date_buttons = [
        [InlineKeyboardButton(text=f"📅 {d}", callback_data=f"date_{event_id}_{d}")]
        for d in dates
    ]

    #
    nav_buttons = []
    if total_events - 1 == 0:
        print('мероприятие одно, кнопки навигации не добавляем')
    elif event_index == 0 and event_index < total_events - 1:
        nav_buttons = [
            InlineKeyboardButton(text="▶️ Далее", callback_data=f"next_{event_index}")
        ]
    elif 0 < event_index < total_events - 1:
        nav_buttons = [
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"prev_{event_index}"),
            InlineKeyboardButton(text="▶️ Далее", callback_data=f"next_{event_index}")
        ]
    elif event_index == total_events - 1 and total_events > 0:
        nav_buttons = [
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"prev_{event_index}")
        ]

    if nav_buttons:
        date_buttons.append(nav_buttons)

    date_buttons.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="close")])
    print(F"[DEBUG get_event_navigation_keyboard] Сформировали кнопки и вернем их. date_buttons: {date_buttons}")
    return InlineKeyboardMarkup(inline_keyboard=date_buttons)


@router.callback_query(lambda c: c.data.startswith("date_"))
async def handle_date_selection(callback: CallbackQuery):
    print(f"[DEBUG handle_date_selection] выведем список дат под масте-классом")
    data_parts = callback.data.split("_")
    event_id = int(data_parts[1])
    date_str = data_parts[2]

    times = get_times_for_event_on_date(event_id, date_str)

    time_buttons = [
        [InlineKeyboardButton(text=f"🕑 {t}", callback_data=f"time_{event_id}_{date_str}_{t}")]
        for t in times
    ]

    back_button = [
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"prev_0")]
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=time_buttons + back_button)

    # caption = (
    #     text=f"📅 <b>{date_str}</b>\n\n\Выберите время, чтобы записаться на мастер-класс:"
    # )

    #media = InputMediaPhoto(caption=caption, parse_mode="HTML")

    #await callback.message.edit_media(media=media, reply_markup=keyboard)
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("time_"))
async def handle_time_selection(callback: CallbackQuery, state: FSMContext):
    _, event_id, date_str, time_str = callback.data.split("_")

    keyboard = InlineKeyboardMarkup(
        inline_keyboard = [
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="close")]
        ]
    )
    # Сюда можно добавить запись в таблицу регистраций, если нужна
    await callback.message.edit_caption(
        caption=f"✅ Вы записаны на мастер-класс!\n\n📅 <b>{date_str}</b> в <b>{time_str}</b>",
        parse_mode="HTML",
        reply_markup=keyboard
    )

    fake_callback = SimpleNamespace(
        from_user=callback.from_user,
        message=callback.message,
        data=f"signup_event:{event_id}"
    )   

    await callback.answer("Запись подтверждена ✅")
    callback.data = f"signup_event:{event_id}"
    #await handle_signup_event(callback, state)
    await handle_signup_event(fake_callback, state)


@router.callback_query(lambda c: c.data == "close")
async def handle_close(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()






