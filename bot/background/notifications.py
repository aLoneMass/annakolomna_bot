import asyncio
import sqlite3
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from bot.services.events import get_upcoming_events_with_templates, get_event_registrations
from bot.background.notifications import scheduler, prepare_all_notifications

from config import DB_PATH
from aiogram import Bot
from config import BOT_TOKEN


scheduler = AsyncIOScheduler(timezone=timezone.utc)

# === Напоминание пользователю ===
async def send_event_reminder(bot: Bot, user_id: int, title: str, location: str, when: str):
    await bot.send_message(
        user_id,
        f"❗️ Напоминаем, что {when} состоится мастер-класс: <b>{title}</b>\n\n📍 Адрес: {location}",
        parse_mode="HTML"
    )

# === Назначение напоминаний для события ===
def schedule_event_notifications(bot: Bot, event_id: int, event_datetime: datetime, title: str, location: str, user_ids: list[int]):
    notify_times = [
        ("через 24 часа", event_datetime - timedelta(hours=24)),
        ("через 1 час", event_datetime - timedelta(hours=1))
    ]

    for when_label, notify_time in notify_times:
        for user_id in user_ids:
            job_id = f"notify_{when_label.replace(' ', '_')}_event{event_id}_user{user_id}"
            scheduler.add_job(
                send_event_reminder,
                trigger=DateTrigger(run_date=notify_time),
                args=[bot, user_id, title, location, when_label],
                id=job_id,
                replace_existing=True
            )

# === Подготовка напоминаний при запуске ===
def prepare_all_notifications(bot: Bot):
    now = datetime.now(timezone.utc)
    events = get_upcoming_events_with_templates(now)

    for event_id, date_str, time_str, title, location in events:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        dt = dt.replace(tzinfo=timezone.utc)

        user_ids = get_event_registrations(event_id)
        schedule_event_notifications(bot, event_id, dt, title, location, user_ids)

# В main.py нужно вызывать:
# scheduler.start()
# prepare_all_notifications(bot)
