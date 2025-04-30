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

def get_dates_for_event(template_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT date FROM events
            WHERE template_id = ?
            ORDER BY date;
        """, (template_id,))
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

@router.callback_query(lambda c: c.data.startswith("show_dates_"))
async def handle_show_dates(callback: CallbackQuery):
    template_id = int(callback.data.split("_")[2])
    print(f"[DEBUG handle_show_dates] привязать даты к кнопкам. template_id:{template_id}")
    dates = get_dates_for_event(template_id)
    print(f"[DEBUG handle_show_dates] привязать даты к кнопкам. dates:{dates}")
    date_buttons = [
        [InlineKeyboardButton(text=f"📅 {d}", callback_data=f"date_{template_id}_{d}")]
        for d in dates
    ]
    date_buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"prev_0")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=date_buttons)

    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer()


def get_event_navigation_keyboard(template_index: int, total_templates: int, template_id: int):

    #dates = get_dates_for_event(event_id)
    #record_button = record_event_navigation_button(event_id)
    print(F"[DEBUG get_event_navigation_keyboard] template_id: {template_id}, template_index: {template_index}, total_templates: {total_templates}")

    # date_buttons = [
    #     [InlineKeyboardButton(text=f"📅 {d}", callback_data=f"date_{event_id}_{d}")]
    #     for d in dates
    # ]

    #
    date_buttons = []
    nav_buttons = []
    if total_templates - 1 == 0:
        print('мероприятие одно, кнопки навигации не добавляем')
    elif template_index == 0 and template_index < total_templates - 1:
        nav_buttons = [
            InlineKeyboardButton(text="▶️ Далее", callback_data=f"next_{template_index}")
        ]
    elif 0 < template_index < total_templates - 1:
        nav_buttons = [
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"prev_{template_index}"),
            InlineKeyboardButton(text="▶️ Далее", callback_data=f"next_{template_index}")
        ]
    elif template_index == total_templates - 1 and total_templates > 0:
        nav_buttons = [
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"prev_{template_index}")
        ]

    if nav_buttons:
        date_buttons.append(nav_buttons)
    
    date_buttons.append([InlineKeyboardButton(text="📝 Записаться", callback_data=f"show_dates_{template_id}")])
    date_buttons.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="close")])
    print(F"[DEBUG get_event_navigation_keyboard] Сформировали кнопки и вернем их. date_buttons: {date_buttons}")
    return InlineKeyboardMarkup(inline_keyboard=date_buttons)


@router.callback_query(lambda c: c.data.startswith("date_"))
async def handle_date_selection(callback: CallbackQuery):
    print(f"[DEBUG handle_date_selection] выведем список дат под масте-классом")
    data_parts = callback.data.split("_")
    print(f"[DEBUG handle_date_selection] data_parts:{data_parts}")
    template_id = int(data_parts[1])
    print(f"[DEBUG handle_date_selection] event_id:{template_id}")
    date_str = data_parts[2]

    times = get_times_for_event_on_date(template_id, date_str)
    print(f"[DEBUG handle_date_selection] times:{times}")
    time_buttons = []
    for t in times:
        event_id = get_event_id(template_id, date_str, t)   #За счет t -> event_id каждый раз разный
        time_buttons.append([InlineKeyboardButton(text=f"{t}", callback_data=f"signup_event:{event_id}")])

    # time_buttons = [
    #     #[InlineKeyboardButton(text=f"🕑 {t}", callback_data=f"time_{event_id}_{date_str}_{t}")]
    #     [InlineKeyboardButton(text=f"{t}", callback_data=f"signup_event:{template_id}")]            #тут надо поменять и передавать не template_id, а event_id
    #     for t in times
    # ]

    back_button = [
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"prev_0")]
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=time_buttons + back_button)

    await callback.message.edit_reply_markup(reply_markup=keyboard)
    
    await callback.answer()


def get_event_id(template_id: int, date_str: str, time_str: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM events
            WHERE template_id = ? AND date = ? AND time = ?
            LIMIT 1;
        """, (template_id, date_str, time_str))
        row = cursor.fetchone()
        if row:
            return row[0]
        return None




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

    await callback.answer("Запись подтверждена ✅")
    #callback.data = f"signup_event:{event_id}"
    #await handle_signup_event(callback, state)
    #await handle_signup_event(fake_callback, state)
    #await handle_signup_event(callback.from_user.id, event_id, state)



@router.callback_query(lambda c: c.data == "close")
async def handle_close(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@router.callback_query(lambda c: c.data == "reg_back")
async def handle_reg_back(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()