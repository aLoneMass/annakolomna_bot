from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.filters import StateFilter
from bot.states.admin import AdminCreateEventState
import sqlite3, re
from config import DB_PATH
from config import ADMINS 
from datetime import datetime, date
from bot.services.events import get_past_events

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

router = Router()
MAX_MESSAGE_LENGTH = 4000  # запас, чтобы не упереться в лимит

@router.message(Command("admin"))   #проверим является ли пользователь - админом и выведем ему админ меню.
async def admin_menu(message: Message):
    if message.from_user.id not in ADMINS:
        await message.answer("⛔ Доступ запрещён.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Участники", callback_data="show_registrations")],
        [InlineKeyboardButton(text="📅 Мероприятия", callback_data="show_events")],
        [InlineKeyboardButton(text="📸 Отправить ссылку фото", callback_data="send_link")],
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
    print(f"await state.get_state: {await state.get_state()}")



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
    print(f"[DEBUG show_event_confirmation] data: {data}")
    text = f"<b>Подтвердите создание мастер-класса:</b>"
    text += f"\nНазвание: {data.get('title') or data.get('AdminCreateEventState:title')}"
    text += f"\nОписание: {data.get('description') or data.get('AdminCreateEventState:description')}"
    text += f"\nЦена: {data.get('price')}₽"
    text += f"\nАдрес: {data.get('location') or data.get('AdminCreateEventState:location') }"
    text += f"\nСсылка оплаты: {data.get('payment_link') or data.get('AdminCreateEventState:payment_link')}"
    text += f"\n<b>Расписание:</b>\n"
    for date in data['dates']:
        times = ", ".join(data['time_by_date'][date])
        text += f"📅 {date}: {times}\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_event")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_event")]
    ])
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)



# Перемещённый обработчик в самый конец
@router.message(StateFilter(
    AdminCreateEventState.title,
    AdminCreateEventState.description,
    AdminCreateEventState.photo,
    AdminCreateEventState.qr,
    AdminCreateEventState.payment_link,
    AdminCreateEventState.location,
    AdminCreateEventState.price
))
async def handle_template_fields(message: Message, state: FSMContext):
    print(f"[DEBUG handle_template_fields] попали в заполнение шаблона")
    #print(f"[DEBUG FSM state] step_index = {step_index}, state = {current_state.state_name: message.text}")
    print(await state.get_state())
    data = await state.get_data()
    print(f"[DEBUG handle_template_fields] data:{data}")
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
        #Здесь сохраняем фото на диск

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
        next_prompt, next_state = template_fields[step_index]
        print(f"[DEBUG handle_template_fields] Пока индекс меньше или равен кол-ву строк шаблона: {next_prompt}, {next_state}")
        await message.answer(next_prompt)
        await state.set_state(next_state)
        await state.update_data(step_index=step_index)
    else:
        print(f"[DEBUG handle_template_fields] индекс >= строк в шаблоне: уходим на функцию event_dates")
        await message.answer("📅 Введите дату(ы) мероприятия в формате ДД.ММ.ГГГГ, через запятую:")
        await state.set_state(AdminCreateEventState.event_dates)



@router.callback_query(F.data == "confirm_event")
async def confirm_event_save(callback: CallbackQuery, state: FSMContext):
    print(f"[DEBUG confirm_event_save]")
    await save_event_template(state, callback.message)
    await callback.answer()


async def save_event_template(state: FSMContext, message: Message):
    print(f"[DEBUG save_event_template]")
    data = await state.get_data()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    print(f"[DEBUG save_event_template] data: {data}")
    print(f"[DEBUG save_event_template] Message: {message}")


    #AdminCreateEventState:title
    cursor.execute("""
        INSERT INTO event_templates (title, description, photo_path, qr_path, payment_link, location, price)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("title") or data.get("AdminCreateEventState:title"),
        data.get("description") or data.get("AdminCreateEventState:description"),
        data.get("photo") or data.get("AdminCreateEventState:photo"),
        data.get("qr") or data.get("AdminCreateEventState:qr"),
        data.get("payment_link") or data.get("AdminCreateEventState:payment_link"),
        data.get("location") or data.get("AdminCreateEventState:location"),
        data.get("price") or data.get("AdminCreateEventState:price")
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


#Выведем список всех зарегистрированных пользователей на всех мероприятиях    
@router.callback_query(F.data == "show_registrations")
async def show_all_registrations(callback: CallbackQuery):
    print('[DEBUG show_all_registrations]')
    today = date.today().isoformat()

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        # Достаем всю нужную информацию
        cur.execute("""
            SELECT
                et.title,           -- Название мастер-класса
                e.date,             -- Дата
                e.time,             -- Время
                u.full_name,        -- Имя родителя
                u.username,         -- Username родителя
                c.child_name,       -- Имя ребенка
                c.birth_date,       -- День рождения
                c.comment,          -- Комментарий (аллергии)
                p.payment_type      -- Тип оплаты
            FROM registrations r
            JOIN events e ON r.event_id = e.id
            JOIN event_templates et ON e.template_id = et.id
            JOIN users u ON r.user_id = u.id
            JOIN children c ON r.child_id = c.id
            LEFT JOIN payments p ON r.id = p.registration_id
            WHERE e.date >= ?
            ORDER BY e.date, e.time, et.title
        """, (today,))
        
        rows = cur.fetchall()

    if not rows:
        await callback.message.answer("Записей на мастер-классы нет.")
        await callback.answer()
        return

    # Группируем данные
    output = ""
    last_event = None
    last_datetime = None

    for row in rows:
        title, event_date, event_time, full_name, username, child_name, birth_date, comment, payment_type = row
        #event_header = f"{title}\n📅 {event_date} ⏰ {event_time}"
        event_key = (title, event_date, event_time)

        # if (title, event_date, event_time) != last_event:
        #     if last_event is not None:
        #         output += "\n"  # Разделение между мероприятиями
        #     output += f"\n<b>{event_header}</b>\n"
        #     last_event = (title, event_date, event_time)

        if event_key != last_event:
            if last_event is not None:
                output += "\n" + ("—" * 40) + "\n\n"
            output += (
                f"🎨 <b>{title}</b>\n"
                f"📅 <b>Дата:</b> {event_date}   ⏰ <b>Время:</b> {event_time}\n\n"
            )
            last_event = event_key

        payment_status = payment_type if payment_type else "не оплачено"
        output += (
            f"👤 Родитель: {full_name or 'нет имени'} (@{username or 'нет username'})\n"
            f"👶 Ребёнок: {child_name} (Дата рождения: {birth_date})\n"
            f"🧴 Аллергии: {comment}\n"
            f"💵 Оплата: {payment_status}\n\n"
        )
    for part in split_message(output.strip()):
        await callback.message.answer(part, parse_mode="HTML")
    #await callback.message.answer(output, parse_mode="HTML")
    await callback.answer()


#Функция деления сообщения на несколько до 4к символов.
def split_message(text: str, max_length=MAX_MESSAGE_LENGTH) -> list[str]:
    """Разбивает длинный текст на части по max_length, стараясь делить по \n\n"""
    parts = []
    while len(text) > max_length:
        split_index = text.rfind("\n\n", 0, max_length)
        if split_index == -1:
            split_index = max_length
        parts.append(text[:split_index].strip())
        text = text[split_index:].strip()
    if text:
        parts.append(text)
    return parts




@router.callback_query(F.data == "send_link")
async def send_link_past_event(callback: CallbackQuery, state: FSMContext):
    events = get_past_events()
    if events == 0:
        return
    (template_id, title, description, price,
            qr_path, payment_link, location, photo_uniq
        ) = events
    
    if not events:
        await callback.message.answer("Нет запланированных мероприятий.")
        await callback.answer()
        return
    
