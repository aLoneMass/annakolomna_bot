from aiogram import Router, F
from aiogram import types
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from datetime import date
from bot.services.events import get_all_templates
from bot.keyboards.event_nav import get_event_navigation_keyboard, handle_date_selection
from aiogram.types import FSInputFile
from aiogram.types import InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
from config import DB_PATH




router = Router()
#PHOTO_DIR = "data/event_photos"

#Переписал процедуру "показать расписание"
@router.callback_query(lambda c: c.data.startswith(("next_", "prev_")))  #роутер срабатывает на нажите кнопок которые возвращают значение next_ и prev_
async def handle_navigation(callback: CallbackQuery):
    print("[DEBUG handle_navigation]")

    templates = get_all_templates()
    total = len(templates)

    print(f"[DEBUG handle_navigation] teplates: {templates}")
    print(f"[DEBUG handle_navigation] total: {total}")
    if total == 0:
        print("[DEBUG handle_navigation] зашли в условие, когда нет событий")
        await callback.message.answer("🔔 Сейчас нет доступных мастер-классов. Следите за обновлениями!")
        await callback.answer()
        return

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
            f"📍 <a href=\"{location}\">Адрес тут</a>\n"
            f"💵 Стоимость: {price}"
            #f"\n💳 <a href=\"{payment_link}\">Ссылка для оплаты</a>"
        )

        keyboard = get_event_navigation_keyboard(new_index, total, template_id)

        print(f"[DEBUG handle_navigation] photo_uniq={photo_uniq}")
        print(f"[DEBUG handle_navigation] caption:\n{caption}")

        media = InputMediaPhoto(media=photo_uniq, caption=caption, parse_mode="HTML")
        await callback.message.edit_media(media=media, reply_markup=keyboard)

    await callback.answer()








