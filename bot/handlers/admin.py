from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMINS  # ADMINS берется из .env, например, [123456789, 987654321]

router = Router()

@router.message(Command("admin"))
async def admin_menu(message: Message):
    # Проверка: если пользователь не в списке администраторов, возвращаем отказ
    if message.from_user.id not in ADMINS:
        await message.answer("⛔ Доступ запрещён.")
        return

    # Если проверка пройдена, выводим меню администратора
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список записей", callback_data="show_registrations")],
        [InlineKeyboardButton(text="📅 Мероприятия", callback_data="show_events")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])
    await message.answer("Добро пожаловать в админ-меню 👨‍💼", reply_markup=keyboard)


@router.callback_query(lambda c: c.data == "show_registrations")
async def show_registrations(callback: CallbackQuery):
    from database import get_all_registrations
    registrations = get_all_registrations()
    if not registrations:
        await callback.message.answer("Пока нет записей.")
        return

    text = "📋 <b>Список записей:</b>\n\n"
    for reg in registrations:
        username, child, comment, event_date, event_time, payment_method = reg
        text += (
            f"👤 Пользователь: <code>{username}</code>\n"
            f"👧 Ребёнок: {child}\n"
            f"📅 Дата: {event_date} {event_time}\n"
            f"💬 Комментарий: {comment or '—'}\n"
            f"💰 Оплата: {payment_method}\n\n"
        )

    await callback.message.answer(text)



@router.callback_query(lambda c: c.data == "show_events")
async def show_events(callback: CallbackQuery):
    # Добавьте здесь получение и вывод мероприятий
    await callback.message.answer("Функционал просмотра мероприятий еще в разработке.")


@router.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.answer("Возвращаемся в главное меню.")
