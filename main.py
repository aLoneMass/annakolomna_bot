import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from config import BOT_TOKEN
from bot.handlers import start, schedule, registration, admin
from bot.keyboards import event_nav



async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="schedule", description="📅 Расписание мероприятий"),
        BotCommand(command="start", description="🔁 Перезапустить бота"),
        BotCommand(command="admin", description="👨‍💼 Админ-меню")
    ]
    await bot.set_my_commands(commands)

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Подключаем хендлеры
    dp.include_router(start.router)
    dp.include_router(schedule.router)
    dp.include_router(event_nav.router)
    dp.include_router(registration.router)
    dp.include_router(admin.router)

    print('Бот запущен')

    await setup_bot_commands(bot)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
