import os
from aiogram import Bot
from datetime import datetime

def calculate_age(birth_date: datetime) -> int:
    today = datetime.today()
    return today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )

async def notify_admins_about_registration(
    bot: Bot,
    admins: list[int],
    parent_name: str,
    child_name: str,
    birth_date: str,
    comment: str,
    event_title: str,
    event_date: str,
    event_time: str,
):
    birth_info = birth_date
    try:
        birth_dt = datetime.strptime(birth_date, "%Y-%m-%d")
        age = calculate_age(birth_dt)
        birth_info += f" ({age} лет)"
    except Exception:
        pass

    message = (
        f"👤 <b>Новая запись</b>\n"
        f"👪 Родитель: <b>{parent_name}</b>\n"
        f"🧒 Ребёнок: <b>{child_name}</b>\n"
        f"🎂 Дата рождения: <b>{birth_info}</b>\n"
        f"📅 Мероприятие: <b>{event_title}</b>\n"
        f"🕒 Время: <b>{event_date} в {event_time}</b>\n"
        f"💬 Комментарий: <i>{comment or 'нет'}</i>"
    )

    for admin_id in admins:
        try:
            await bot.send_message(admin_id, message, parse_mode="HTML")
        except Exception as e:
            print(f"[ERROR] Не удалось отправить уведомление админу {admin_id}: {e}")
