from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile
from bot.services.calendar import generate_calendar_image
from bot.services.events import get_all_events
from bot.keyboards.event_nav import get_event_navigation_keyboard

router = Router()

@router.callback_query(F.data == "show_schedule")
async def handle_schedule(callback: CallbackQuery):
    # Календарь
    calendar_path = generate_calendar_image()
    calendar_file = FSInputFile(calendar_path)

    await callback.message.answer_photo(
        photo=calendar_file,
        caption="📅 Календарь мероприятий на этот месяц"
    )

    # Мероприятия
    events = get_all_events()

    if not events:
        await callback.message.answer("Пока нет запланированных мероприятий.")
    else:
        index = 0
        event = events[index]
        event_id, photo_path, description, date, time, location = event

        caption = (
            f"📌 <b>{description}</b>\n"
            f"🗓 {date} в {time}\n"
            f"📍 <a href=\"{location}\">Адрес мероприятия</a>"
        )
        photo_file = FSInputFile(photo_path)

        keyboard = get_event_navigation_keyboard(index, len(events))

        await callback.message.answer_photo(
            photo=photo_file,
            caption=caption,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    await callback.answer()
