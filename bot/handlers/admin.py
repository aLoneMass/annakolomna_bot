from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMINS, DB_PATH
import sqlite3
from datetime import datetime
from collections import defaultdict



router = Router()

@router.message(Command("admin"))   #проверим является ли пользователь - админом и выведем ему админ меню.
async def admin_menu(message: Message):
    if message.from_user.id not in ADMINS:
        await message.answer("⛔ Доступ запрещён.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Участники", callback_data="show_registrations")],
        [InlineKeyboardButton(text="📅 Мероприятия", callback_data="show_events")],
        [InlineKeyboardButton(text="📅 Добавить Мастер-класс", callback_data="show_events")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close")]
    ])
    await message.answer("Добро пожаловать в админ-меню 👨‍💼", reply_markup=keyboard)


@router.callback_query(lambda c: c.data == "show_registrations")
async def show_registrations(callback: CallbackQuery):
    #await callback.answer()
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                e.id,
                e.title,
                u.username,
                c.child_name,
                c.comment,
                c.birth_date,
                e.date,
                e.time,
                CASE 
                    WHEN p.payment_type = 'наличными' THEN 'Наличными'
                    WHEN p.payment_type = 'онлайн' THEN 'Онлайн'
                    ELSE 'Не оплачено'
                END AS payment_method
            FROM registrations r
            JOIN users u ON u.id = r.user_id
            JOIN children c ON c.id = r.child_id
            JOIN events e ON e.id = r.event_id
            LEFT JOIN payments p ON p.registration_id = r.id
            ORDER BY e.date DESC, e.time DESC
        """)
        rows = cur.fetchall()
    
    await callback.answer()

    if not rows:
        await callback.message.answer("Пока нет записей.")
        return


    grouped = defaultdict(list)
    event_info = {}

    for row in rows:
        event_id, event_title, username, child, comment, birth_date, date, time, payment_method = row
        grouped[event_id].append((username, child, comment, birth_date, payment_method))
        event_info[event_id] = (event_title, date, time)

    text = "📋 <b>Список записей:</b>\n\n"
    
    for event_id, registrations in grouped.items():
        title, date, time = event_info[event_id]
        text += f"🎨 <b>{title}</b>\n📅 <i>{date} в {time}</i>\n\n"

        for username, child, comment, birth_date, payment_method in registrations:
            birth_date_str = birth_date or 'не указана'
            if birth_date:
                try:
                    birth_dt = datetime.strptime(birth_date, "%Y-%m-%d")
                    today = datetime.today()
                    age = today.year - birth_dt.year - ((today.month, today.day) < (birth_dt.month, birth_dt.day))
                    birth_info = f"{birth_date_str} (возраст: {age})"
                except:
                    birth_info = birth_date_str
            else:
                birth_info = "не указана"

            text += (
                f"👤 Пользователь: @{username or 'без username'}\n"
                f"👧 Ребёнок: {child}\n🎂 День рождения: {birth_info}\n"
                f"💬 Заметка: {comment or '—'}\n"
                f"💰 Оплата: {payment_method}\n\n"
            )

    await callback.message.answer(text, parse_mode="HTML")


@router.callback_query(lambda c: c.data == "show_events")
async def show_events(callback: CallbackQuery):
    await callback.message.answer("Функционал просмотра мероприятий ещё в разработке.")


@router.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.answer("Возвращаемся в главное меню.")
