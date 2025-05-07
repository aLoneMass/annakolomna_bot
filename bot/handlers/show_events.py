from aiogram import Router, F, types
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import sqlite3
from datetime import datetime
from config import GROUP_CHAT_ID
from bot.services.events import get_all_templates, get_schedule_for_template
from aiogram.exceptions import TelegramBadRequest

router = Router()

# === Формирование текста мероприятия ===
def format_event_message(template, schedule):
    title, desc, price, location = template[1], template[2], template[3], template[6]
    link = f"https://t.me/Annakolomnabot?start=event_{template[0]}"
    schedule_text = "\n".join(f"• {dt}" for dt in schedule)

    return (
        f"<b>{title}</b>\n\n"
        f"{desc}\n\n"
        f"<b>📅 Когда:</b>\n{schedule_text}\n\n"
        f"<b>📍 Где:</b> {location}\n"
        f"<b>💰 Стоимость:</b> {price} ₽\n\n"
        f"👉 <a href=\"{link}\">Записаться на мастер-класс</a>"
    )

# === Генерация клавиатуры ===
def generate_keyboard(index: int, total: int, template_id: int):
    buttons = []
    if index > 0:
        buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"event_prev_{index}"))
    if index < total - 1:
        buttons.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"event_next_{index}"))
    buttons_pub = InlineKeyboardButton(text="📣 Опубликовать в группе", callback_data=f"event_pub_{template_id}")
    return InlineKeyboardMarkup(inline_keyboard=[buttons, [buttons_pub]])

# === /show_events ===
@router.callback_query(F.data == "show_events")
async def show_events_handler(callback: types.CallbackQuery, state: FSMContext):
    print("[DEBUG show_events]")
    templates = get_all_templates()
    if not templates:
        await callback.message.answer("Нет запланированных мероприятий.")
        await callback.answer()
        return

    await state.update_data(templates=templates)
    await state.update_data(event_index=0)

    template = templates[0]
    #schedule = get_schedule_for_template(template[0])
    schedule = get_schedule_for_template(template[0])
    text = format_event_message(template, schedule)
    keyboard = generate_keyboard(0, len(templates), template[0])

    print(f"[DEBUG show_events]:template: {template}")
    await callback.message.answer_photo(photo=template[7], caption=text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()
    

# === Навигация вперёд/назад ===
@router.callback_query(F.data.startswith("event_"))
async def navigation_handler(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    templates = data.get("templates", [])
    index = data.get("event_index", 0)

    if "prev" in callback.data:
        index = max(0, index - 1)
    elif "next" in callback.data:
        index = min(len(templates) - 1, index + 1)

    await state.update_data(event_index=index)
    template = templates[index]
    schedule = get_schedule_for_template(template[0])
    text = format_event_message(template, schedule)
    keyboard = generate_keyboard(index, len(templates), template[0])
    try:
        await callback.message.edit_media(
            types.InputMediaPhoto(media=template[7], caption=text, parse_mode="HTML"),
            reply_markup=keyboard
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise
    await callback.answer()

# === Публикация в группу ===
@router.callback_query(F.data.startswith("event_pub_"))
async def publish_handler(callback: CallbackQuery):
    print("[DEBUG publish_handler]")
    template_id = int(callback.data.split("_")[-1])
    conn = sqlite3.connect("database/annakolomna.db")
    cursor = conn.cursor()
    cursor.execute("SELECT title, description, photo_path, price, location FROM event_templates WHERE id = ?", (template_id,))
    template = cursor.fetchone()
    conn.close()

    schedule = get_schedule_for_template(template_id)
    text = format_event_message((template_id, *template), schedule)

    try:
        await callback.bot.send_photo(
            chat_id=GROUP_CHAT_ID,
            photo=template[2],
            caption=text,
            parse_mode="HTML"
        )
        await callback.answer("Опубликовано в группе ✅", show_alert=True)
    except Exception as e:
        await callback.answer(f"Ошибка при публикации: {e}", show_alert=True)
