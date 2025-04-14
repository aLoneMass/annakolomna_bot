from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command

from bot.services.calendar import generate_calendar_image
from bot.services.events import get_all_events
from bot.keyboards.event_nav import get_event_navigation_keyboard_with_signup

router = Router()

# 📅 Обработка команды /schedule
@router.message(Command("schedule"))
async def handle_schedule_command(message: Message):
    await send_schedule(message)


# 📅 Обработка кнопки "📅 Расписание мероприятий"
@router.message(F.text == "📅 Расписание мероприятий")
async def handle_schedule_text_button(message: Message):
    await send_schedule(message)


# 📅 Обработка нажатия inline-кнопки "Показать расписание"
@router.callback_query(F.data == "show_schedule")
async def handle_schedule_callback(callback: CallbackQuery):
    await send_schedule(callback.message)
    await callback.answer()


# 🧠 Универсальная функция показа календаря и первого мероприятия
async def send_schedule(message: Message):
    #calendar_path = generate_calendar_image()
    #calendar_file = FSInputFile(calendar_path)

    #await message.answer_photo(
    #    photo=calendar_file,
    #    caption="📅 Календарь мероприятий на этот месяц"
    #)

    events = get_all_events()
    if not events:
        await message.answer("Пока нет запланированных мероприятий.")
        return

    index = 0
    event = events[index]
    event_id, photo_path, description, date, time, location, payment_link, qr_path = event

    caption = (
        f"📌 <b>{description}</b>\n"
        f"🗓 <b>{date}</b> в <b>{time}</b>\n"
        f"📍 <a href=\"{location}\">Адрес мероприятия</a>"
    )
    photo_file = FSInputFile(photo_path)
    keyboard = get_event_navigation_keyboard_with_signup(index, len(events))

    await message.answer_photo(
        photo=photo_file,
        caption=caption,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
