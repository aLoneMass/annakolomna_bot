from aiogram import Router, F
from aiogram import types
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from datetime import date
from bot.services.events import get_all_events, get_all_templates
from bot.keyboards.event_nav import get_event_navigation_keyboard
from aiogram.types import FSInputFile
from aiogram.types import InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
from config import DB_PATH




router = Router()
PHOTO_DIR = "data/event_photos"

#Переписал процедуру "показать расписание"
@router.callback_query(lambda c: c.data.startswith(("next_", "prev_")))  #роутер срабатывает на нажите кнопок которые возвращают значение next_ и prev_
async def handle_navigation(callback: CallbackQuery):
    print("[DEBUG handle_navigation]")
    #today = date.today().isoformat()  
    #events = get_all_events(today)

    templates = get_all_templates()
    total = len(templates)

    # Текущий индекс получаем из callback_data
    data = callback.data
    print(f"[DEBUG handle_navigation] data:{data}")
    current_index = int(data.split('_')[1])
    new_index = current_index + 1 if data.startswith("next_") else current_index - 1

    if 0 <= new_index < total:
        template = templates[new_index]
        (template_id, title, description, price,
            qr_path, payment_link, location, photo_uniq
        ) = template

        print(f"[DEBUG handle_navigation] отладка для  Фото: filename: {photo_uniq}")
        caption = (
            f"🍯 <b>{title}</b>\n"
            f"📌 <b>{description}</b>\n"
            #f"📍 <a href=\"{location}\">Адрес тут</a>\n"
            #f"\n💳 <a href=\"{payment_link}\">Ссылка для оплаты</a>"
        )

        keyboard = get_event_navigation_keyboard(new_index, total, template_id)

        print(f"[DEBUG handle_navigation] photo_uniq={photo_uniq}")
        print(f"[DEBUG handle_navigation] caption:\n{caption}")

        media = InputMediaPhoto(media=photo_uniq, caption=caption, parse_mode="HTML")
        print(f"[DEBUG handle_navigation] media прошла, вызовем возврат кнопок и медиа пользователю")
        await callback.message.edit_media(media=media, reply_markup=keyboard)

    await callback.answer()




@router.callback_query(lambda c: c.data.startswith("date_"))
async def handle_date_selection(callback: CallbackQuery):
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

    await callback.message.edit_text(
        text=f"📅 <b>{date_str}</b>\n\n\Выберите время, чтобы записаться на мастер-класс:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()




@router.callback_query(lambda c: c.data.startswith("time_"))
async def handle_time_selection(callback: CallbackQuery):
    _, event_id, date_str, time_str = callback.data.split("_")

    # Сюда можно добавить запись в таблицу регистраций, если нужна
    await callback.message.edit_text(
        text=f"✅ Вы записаны на мастер-класс!\n📅 <b>{date_str}</b> в <b>{time_str}</b>",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == "close")
async def handle_close(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()




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