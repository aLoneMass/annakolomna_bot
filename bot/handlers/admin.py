from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from config import ADMINS
from database import get_all_registrations
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router()

@router.message(Command("admin"))
async def admin_menu(message: Message):
    if message.from_user.id not in ADMINS:
        await message.answer("У вас нет доступа к админ-меню.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список записей", callback_data="show_registrations")],
        [InlineKeyboardButton(text="📅 Мероприятия", callback_data="show_events")],
    ])
    await message.answer("Добро пожаловать в админ-меню 👨‍💼", reply_markup=keyboard)

@router.callback_query(F.data == "show_registrations")
async def show_registrations(callback: CallbackQuery):
    registrations = get_all_registrations()
    if not registrations:
        await callback.message.answer("Пока нет записей.")
        return

    text = "📋 <b>Список записей:</b>\n\n"
    for reg in registrations:
        user, child, comment, event_date, event_time, payment = reg
        text += (
            f"👤 Пользователь: <code>{user}</code>\n"
            f"👧 Ребёнок: {child}\n"
            f"📅 Дата: {event_date} {event_time}\n"
            f"💬 Комментарий: {comment or '—'}\n"
            f"💰 Оплата: {payment}\n\n"
        )

    await callback.message.answer(text)
