from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.states.admin import AdminCreateEventState
import sqlite3, os, re
from config import DB_PATH
from config import ADMINS 
from datetime import datetime

router = Router()

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

#Шаблон создания мероприятия
template_fields = [
    ("Введите название мастер-класса:", AdminCreateEventState.title),
    ("Введите описание:", AdminCreateEventState.description),
    ("Отправьте фото-анонс:", AdminCreateEventState.photo),
    ("Отправьте QR-код для оплаты:", AdminCreateEventState.qr),
    ("Введите ссылку для онлайн-оплаты:", AdminCreateEventState.payment_link),
    ("Введите адрес проведения мероприятия:", AdminCreateEventState.location),
    ("Введите стоимость (только число):", AdminCreateEventState.price)
]

@router.callback_query(F.data == "create_event")
async def start_create_template(callback: CallbackQuery, state: FSMContext):
    print(f"[DEBUG create_event]")
    await callback.message.answer(template_fields[0][0])
    await state.set_state(template_fields[0][1])
    await state.update_data(step_index=0)
    await callback.answer()
    print(f"[DEBUG create_event]template_fields[0][1]:{template_fields[0][1]}")




@router.message(AdminCreateEventState.event_dates)
async def receive_event_dates(message: Message, state: FSMContext):
    print(f"[DEBUG receive_event_dates] - мы в него попали через вызов роутера - event_dates")
    raw_dates = message.text.split(',')
    print(f"[DEBUG receive_event_dates] строчки дат raw_dates:{raw_dates}")
    parsed_dates = []
    for d in raw_dates:
        try:
            parsed = datetime.strptime(d.strip(), "%d.%m.%Y").date()
            parsed_dates.append(str(parsed))
            print(f"[DEBUG receive_event_dates] Преобразовали дату в формат dates:{parsed_dates}")
        except ValueError:
            await message.answer(f"❗ Неверный формат даты: {d.strip()}")
            print(f"[DEBUG receive_event_dates] Ошибка получения дат:{ValueError}")
            return
    await state.update_data(dates=parsed_dates, time_by_date={}, current_date_index=0)
    await state.set_state(AdminCreateEventState.event_times)
    await message.answer(f"⏰ Введите время(я) начала (ЧЧ:ММ, через запятую) для {parsed_dates[0]}:")

@router.message(AdminCreateEventState.event_times)
async def receive_event_times(message: Message, state: FSMContext):
    print(f"[DEBUG receive_event_times]")
    data = await state.get_data()
    dates = data["dates"]
    index = data["current_date_index"]
    time_by_date = data.get("time_by_date", {})

    times = [t.strip() for t in message.text.split(',') if re.match(r"^\d{2}:\d{2}$", t.strip())]
    if not times:
        await message.answer("❗ Введите корректные времена в формате ЧЧ:ММ, через запятую.")
        return

    time_by_date[dates[index]] = times
    index += 1
    if index < len(dates):
        await state.update_data(time_by_date=time_by_date, current_date_index=index)
        await message.answer(f"⏰ Введите время(я) начала для {dates[index]}:")
    else:
        await state.update_data(time_by_date=time_by_date)
        await state.set_state(AdminCreateEventState.confirm)
        await show_event_confirmation(state, message)

async def show_event_confirmation(state: FSMContext, message: Message):
    print(f"[DEBUG show_event_confirmation]")
    data = await state.get_data()
    text = f"<b>Подтвердите создание мастер-класса:</b>\n"
    text += f"Название: {data['title']}\n"
    text += f"Описание: {data['description']}\n"
    text += f"Цена: {data['price']}₽\n"
    text += f"Адрес: {data['location']}\n"
    text += f"Ссылка оплаты: {data['payment_link']}\n"
    text += f"\n<b>Расписание:</b>\n"
    for date in data['dates']:
        times = ", ".join(data['time_by_date'][date])
        text += f"📅 {date}: {times}\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_event")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_event")]
    ])
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

@router.callback_query(F.data == "confirm_event")
async def confirm_event_save(callback: CallbackQuery, state: FSMContext):
    print(f"[DEBUG confirm_event_save]")
    await save_event_template(state, callback.message)
    await callback.answer()


# Перемещённый обработчик в самый конец
@router.message(AdminCreateEventState.title,
                AdminCreateEventState.description,
                AdminCreateEventState.photo,
                AdminCreateEventState.qr,
                AdminCreateEventState.payment_link,
                AdminCreateEventState.location,
                AdminCreateEventState.price)
async def handle_template_fields(message: Message, state: FSMContext):
    print(f"[DEBUG handle_template_fields] попали в заполнение шаблона")
    data = await state.get_data()
    if "step_index" not in data:
        print(f"[DEBUG handle_template_fields] индекс шага не существует. ошибка. пробуй заново")
        await message.answer("⚠️ Ошибка: шаблон не был корректно инициализирован. Пожалуйста, начните заново.")
        return
    step_index = data.get("step_index", 0)

    if step_index >= len(template_fields):
        print(f"[DEBUG handle_template_fields] step_index >= кол-ву полей в шаблоне {step_index}")
        return

    field_name, current_state = template_fields[step_index]
    print(f"[DEBUG handle_template_fields] Распаковали field_name: {field_name}, current_state: {current_state}")
    if current_state in [AdminCreateEventState.photo, AdminCreateEventState.qr]:
        print(f"[DEBUG handle_template_fields] зашли в if current_state in [AdminCreateEventState.photo, AdminCreateEventState.qr]")
        if not message.photo:
            await message.answer("❗ Пожалуйста, отправьте изображение.")
            return
        file_id = message.photo[-1].file_id
        await state.update_data(**{current_state.state: file_id})
    elif current_state == AdminCreateEventState.price:
        print(f"[DEBUG handle_template_fields] шаг .price")
        try:
            price = int(message.text.strip())
            await state.update_data(price=price)
            print(f"[DEBUG handle_template_fields] шаг .price:{price}")
        except ValueError:
            await message.answer("❗ Введите корректную стоимость.")
            print(f"[DEBUG handle_template_fields] шаг .price ошибка значения:{ValueError}")
            return
    else:
        print(f"[DEBUG handle_template_fields] Если не фото и не qr, тообновить state.update_data: {message.text}")
        await state.update_data(**{current_state.state: message.text})

    step_index += 1
    print(f"[DEBUG handle_template_fields] Увеличили индекс+1")
    if step_index < len(template_fields):
        print(f"[DEBUG handle_template_fields] Пока индекс меньше или равен кол-ву строк шаблона: {next_prompt}, {next_state}")
        next_prompt, next_state = template_fields[step_index]
        await message.answer(next_prompt)
        await state.set_state(next_state)
        await state.update_data(step_index=step_index)
    else:
        print(f"[DEBUG handle_template_fields] индекс >= строк в шаблоне: уходим на функцию event_dates")
        await message.answer("📅 Введите дату(ы) мероприятия в формате ДД.ММ.ГГГГ, через запятую:")
        await state.set_state(AdminCreateEventState.event_dates)

async def save_event_template(state: FSMContext, message: Message):
    data = await state.get_data()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO event_templates (title, description, photo_path, qr_path, payment_link, location, price)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["title"],
        data["description"],
        data["photo"],
        data["qr"],
        data["payment_link"],
        data["location"],
        data["price"]
    ))
    template_id = cursor.lastrowid

    for date in data["dates"]:
        for time in data["time_by_date"][date]:
            cursor.execute("""
                INSERT INTO events (template_id, date, time)
                VALUES (?, ?, ?)
            """, (template_id, date, time))

    conn.commit()
    conn.close()

    await message.answer("✅ Мастер-класс и все мероприятия успешно созданы.")
    await state.clear()
