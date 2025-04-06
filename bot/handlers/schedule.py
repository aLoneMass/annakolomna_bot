from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile
from bot.services.calendar import generate_calendar_image

router = Router()

@router.callback_query(F.data == "show_schedule")
async def handle_schedule(callback: CallbackQuery):
    calendar_path = generate_calendar_image()
    calendar_file = FSInputFile(calendar_path)

    await callback.message.answer_photo(
        photo=calendar_file,
        caption="📅 Календарь мероприятий на этот месяц"
    )

    # TODO: показать первое мероприятие из базы
    await callback.answer()
