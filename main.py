import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from bot.handlers import start, schedule, registration

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Здесь будут хендлеры и роутеры
    dp.include_router(start.router)
    dp.include_router(schedule.router)
    dp.include_router(registration.router)
    print('Бот запущен')
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
