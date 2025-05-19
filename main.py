import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from config import BOT_TOKEN
from bot.handlers import start, schedule, registration, admin
from bot.keyboards import event_nav
from bot.background.notifications import scheduler, prepare_all_notifications
from bot.handlers.show_events import router as events_router




async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="📅 Расписание мероприятий"),
        #BotCommand(command="start", description="🔁 Перезапустить бота"),
        BotCommand(command="admin", description="👨‍💼 Админ-меню")
    ]
    await bot.set_my_commands(commands)

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    scheduler.start()
    prepare_all_notifications(bot)

    # Подключаем хендлеры
    dp.include_router(start.router)
    dp.include_router(schedule.router)
    dp.include_router(event_nav.router)
    dp.include_router(registration.router)
    dp.include_router(admin.router)
    dp.include_router(events_router)
    

    print('Бот запущен')

    asyncio.create_task(notify_users())

    await setup_bot_commands(bot)
    await dp.start_polling(bot)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
    
    
