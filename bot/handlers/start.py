from aiogram import Router
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command
from bot.keyboards.main_menu import get_main_inline_keyboard

router = Router()

@router.message(CommandStart()) #Это декоратор, который говорит aiogram, что нужно обрабатывать входящее сообщение, если это команда /start.
async def start_handler(message: Message): #Это асинхронная функция, которая будет вызвана, когда пользователь напишет /start. message: Message — объект сообщения Telegram, в котором есть вся информация о сообщении: текст, автор, чат и т.д.
    text = ( #Создаётся текст приветствия, который потом отправится пользователю.
        "Привет! 👋\n"
        "Добро пожаловать! Здесь ты можешь узнать о предстоящих мастер-классах и записаться на них.\n\n"
        "📅 Нажми кнопку ниже, чтобы посмотреть расписание мероприятий или перейти в главное меню 👇"
    )
    await message.answer(text, reply_markup=get_main_inline_keyboard()) #метод, который отправляет сообщение в ответ на то сообщение, которое пришло
                                                                        #text — сам текст, который мы составили выше.
                                                                        #reply_markup=get_main_inline_keyboard() — к сообщению добавляется инлайн-клавиатура, которую возвращает функция get_main_inline_keyboard().
