from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMINS, DB_PATH
from aiogram.types import BufferedInputFile
import os
import sqlite3
import re
from datetime import datetime
from collections import defaultdict
#from bot.states.registration import RegistrationState
from aiogram.fsm.context import FSMContext
from bot.states.admin import AdminCreateEventState



router = Router()
PHOTO_DIR = "data/event_photos"


@router.message(Command("admin"))   #проверим является ли пользователь - админом и выведем ему админ меню.
async def admin_menu(message: Message):
    if message.from_user.id not in ADMINS:
        await message.answer("⛔ Доступ запрещён.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Участники", callback_data="show_registrations")],
        [InlineKeyboardButton(text="📅 Мероприятия", callback_data="show_events")],
        [InlineKeyboardButton(text="📅 Добавить Мастер-класс", callback_data="create_event")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="close")]
    ])
    await message.answer("Добро пожаловать в админ-меню 👨‍💼", reply_markup=keyboard)

#Вывести список зарегистрированных пользователей на мероприятия
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
    await callback.answer()                 #Эта строка прекращает моргание кнопки, будто она не работает. говорит телеграму, что мы обработали действие по кнопке.



#Тут Администратор создает новые мероприятия
@router.callback_query(F.data.startswith("create_event"))
async def create_event(callback: CallbackQuery,  estate: FSMContext):
    await callback.message.answer("Введите название для Мероприятия")
    await estate.set_state(AdminCreateEventState.event_name)
    await callback.answer()                 #Эта строка прекращает моргание кнопки, будто она не работает. говорит телеграму, что мы обработали действие по кнопке.

@router.message(AdminCreateEventState.event_name)
async def event_name(message:Message, estate:FSMContext):
    await estate.update_data(title=message.text)
    await message.answer("Введите описание мероприятия:")
    await estate.set_state("event_description")

@router.message(AdminCreateEventState.event_description)
async def event_description(message:Message, estate:FSMContext):
    await estate.update_data(event_description = message.text)
    await message.answer("Введите дату (или даты, через запятую) проведения в формате ДД.ММ.ГГГГ")
    await estate.set_state("event_date")

@router.message(AdminCreateEventState.event_date)
async def event_date(message:Message, estate:FSMContext):
    raw_text = message.text.strip()
    date_strings = [d.strip() for d in raw_text.split(",") if d.strip()]

    parsed_dates = []
    for ds in date_strings:
        # Поддержка ДД.ММ.ГГ и ДД.ММ.ГГГГ
        if re.match(r"^\d{2}\.\d{2}\.\d{2}(\d{2})?$", ds):
            try:
                # Распознаем короткий год
                if len(ds.split(".")[2]) == 2:
                    dt = datetime.strptime(ds, "%d.%m.%y")
                else:
                    dt = datetime.strptime(ds, "%d.%m.%Y")
                parsed_dates.append(dt.date())
            except ValueError:
                await message.answer(f"❗ Неверный формат даты: {ds}. Попробуйте снова.")
                return
        else:
            await message.answer(f"❗ Неверный формат даты: {ds}. Укажите даты через запятую в формате ДД.ММ.ГГ или ДД.ММ.ГГГГ")
            return
    # Сохраняем список дат в состояние
    await estate.update_data(dates=parsed_dates)
    await data = estate.get_data()
    await message.answer("Введите время начала мероприятий в формате ЧЧ:ММ, через запятую, для мастер-класса {data.title}, дата: {data.dates[0]}:")
    await estate.set_state("new_event_time")


@router.message(AdminCreateEventState.new_event_time)
async def event_time_input(message: Message, estate: FSMContext):
    data = await estate.get_data()
    title = data.get("title")
    dates = data.get("dates")
    time_by_date = data.get("time_by_date", {})
    current_index = data.get("current_date_index", 0)

    time_strings = [t.strip() for t in message.text.split(",") if re.match(r"^\d{2}:\d{2}$", t.strip())]
    
    if not time_strings:
        await message.answer("❗ Введите время(я) в формате ЧЧ:ММ, через запятую.")
        return

    # Сохраняем времена для текущей даты
    current_date = dates[current_index]
    time_by_date[str(current_date)] = time_strings

    # Обновляем индекс
    current_index += 1
    if current_index < len(dates):
        # Переход к следующей дате
        await estate.update_data(time_by_date=time_by_date, current_date_index=current_index)
        await message.answer(f"Введите время начала мероприятий в формате ЧЧ:ММ, через запятую, для мастер-класса {title}, дата: {dates[current_index]}")
    else:
        # Все даты обработаны
        await estate.update_data(time_by_date=time_by_date)
        await message.answer("✅ Времена для всех дат успешно сохранены.\n" \
                                "Введите стоимость для мероприятия {title}:")
        # Здесь можно перейти к следующему шагу, например сохранению в БД или подтверждению
    
    await  estate.set_state("event_price")



@router.message(AdminCreateEventState.event_price)
async def event_price(message: Message, estate: FSMContext):
    try:
        price = int(message.text.strip())
        if price < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❗ Введите корректную положительную стоимость, только число.")
        return

    await estate.update_data(price=price)
    await message.answer(f"✅ Стоимость мастер-класса сохранена: {price}₽")
    
    # Переход к следующему шагу, например, подтверждение:
    await estate.set_state(AdminCreateEventState.event_photo)



@router.message(AdminCreateEventState.event_photo, F.photo)
async def event_photo(message: Message, estate: FSMContext, bot):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_path = file.file_path
    filename = f"event_{message.date.timestamp()}.jpg"
    local_path = os.path.join(PHOTO_DIR, filename)

    # Скачать и сохранить
    await bot.download_file(file_path, local_path)

    # Обновить FSM
    await estate.update_data(photo_path=local_path)
    await message.answer("✅ Фото сохранено. Теперь отправьте QR-код для оплаты:")
    await estate.set_state(AdminCreateEventState.qr_code)





@router.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.answer("Возвращаемся в главное меню.")
    await callback.answer()
