from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from bot.keyboards.main_menu import get_main_inline_keyboard

router = Router()

@router.message(CommandStart())
async def start_handler(message: Message):
    text = (
        "Привет! 👋\n"
        "Добро пожаловать! Здесь ты можешь узнать о предстоящих мастер-классах и записаться на них.\n\n"
        "📅 Нажми кнопку ниже, чтобы посмотреть расписание мероприятий или перейти в главное меню 👇"
    )
    await message.answer(text, reply_markup=get_main_inline_keyboard())
