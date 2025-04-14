from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMINS, DB_PATH
import sqlite3

router = Router()

@router.message(Command("admin"))
async def admin_menu(message: Message):
    if message.from_user.id not in ADMINS:
        await message.answer("⛔ Доступ запрещён.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список записей", callback_data="show_registrations")],
        [InlineKeyboardButton(text="📅 Мероприятия", callback_data="show_events")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])
    await message.answer("Добро пожаловать в админ-меню 👨‍💼", reply_markup=keyboard)


@router.callback_query(lambda c: c.data == "show_registrations")
async def show_registrations(callback: CallbackQuery):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                u.username,
                c.child_name,
                c.comment,
                c.child_age,
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

    if not rows:
        await callback.message.answer("Пока нет записей.")
        return

    text = "📋 <b>Список записей:</b>\n\n"
    for reg in rows:
        username, child, comment, child_age, date, time, payment_method = reg
        text += (
            f"👤 Пользователь: @{username or 'без username'}\n"
            f"👧 Ребёнок: {child} (возраст: {child_age or 'не указан'})\n"
            f"📅 Дата: {date} {time}\n"
            f"💬 Комментарий: {comment or '—'}\n"
            f"💰 Оплата: {payment_method}\n\n"
        )
    await callback.message.answer(text, parse_mode="HTML")


@router.callback_query(lambda c: c.data == "show_events")
async def show_events(callback: CallbackQuery):
    await callback.message.answer("Функционал просмотра мероприятий ещё в разработке.")


@router.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.answer("Возвращаемся в главное меню.")
