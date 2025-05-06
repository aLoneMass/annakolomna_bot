import asyncio
import sqlite3
from datetime import datetime, timedelta
from config import DB_PATH
from aiogram import Bot
from config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN)

async def notify_users():
    while True:
        now = datetime.now()
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT u.telegram_id, e.date, e.time, et.title, et.location
                FROM users u
                JOIN registrations r ON u.id = r.user_id
                JOIN events e ON r.event_id = e.id
                JOIN event_templates et ON e.template_id = et.id
            """)
            for user_id, date_str, time_str, title, location in cur.fetchall():
                event_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                delta = event_dt - now
                if timedelta(hours=0) < delta <= timedelta(hours=1):
                    await bot.send_message(user_id, f"Напоминаем! Через час начнется мастер-класс: {title}, по адресу: {location}")
                elif timedelta(days=0) < delta <= timedelta(days=1):
                    await bot.send_message(user_id, f"Завтра состоится мастер-класс: {title}, по адресу: {location}")
        await asyncio.sleep(1800)  # Проверять каждые 30 минут
