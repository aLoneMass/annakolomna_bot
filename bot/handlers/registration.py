from aiogram import Bot
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import hbold
from aiogram.fsm.context import FSMContext
from bot.states.registration import RegistrationState
from bot.services.events import get_all_events
import os
import re
import sqlite3
import datetime
from config import CHECKS_DIR, ADMINS, DB_PATH
from bot.utils.notifications import notify_admins_about_registration
from config import ADMINS  # список ID из .env


router = Router()



@router.callback_query(F.data.startswith("signup_event:"))
async def handle_signup_event(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id

    # Сохраняем event_id в state
    await state.update_data(event_id=event_id)

    # Проверка: зарегистрирован ли пользователь на это мероприятие
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.payment_type
            FROM registrations r
            LEFT JOIN payments p ON r.id = p.registration_id
            WHERE r.user_id = ? AND r.event_id = ?
        """, (user_id, event_id))
        reg = cur.fetchone()

        if reg:
            payment_type = reg[0]
            if payment_type == "CASH":
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💳 Оплатить онлайн", callback_data="pay_online")],
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="cancel_registration")]
                ])
                await callback.message.answer(
                    "Вы уже записаны на это мероприятие и выбрали оплату наличными.\n"
                    "Хотите оплатить онлайн?",
                    reply_markup=keyboard
                )
            else:
                await callback.message.answer("✅ Вы уже записаны на это мероприятие.")
            await callback.answer()
            return

    # Проверка: есть ли сохранённый ребёнок
    cur = conn.cursor()
    cur.execute("""
        SELECT child_name, comment, birth_date
        FROM children
        WHERE user_id = ?
        LIMIT 1
    """, (user_id,))
    child = cur.fetchone()

    if child:
        child_name, comment, birth_date = child
        # Сохраняем в state для подтверждения
        await state.update_data(
            child_name=child_name,
            comment=comment,
            birth_date=birth_date
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да", callback_data="confirm_child_info")],
            [InlineKeyboardButton(text="✏️ Ввести заново", callback_data="new_child_info")]
        ])

        await callback.message.answer(
            f"👶 Найдены данные ребёнка:\n"
            f"Имя: {hbold(child_name)}\n"
            f"Комментарий: {comment or '–'}\n"
            f"День рождения: {birth_date}\n\n"
            f"Использовать эти данные?",
            reply_markup=keyboard
        )
        await callback.answer()
        return

    # Если данных о ребёнке нет — переходим к ручному вводу
    await callback.message.answer("Введите имя ребёнка:")
    await state.set_state(RegistrationState.entering_child_name)
    await callback.answer()


#Если пользователь подтвердил использование имеющихся данных
@router.callback_query(F.data == "confirm_child_info")
async def handle_confirm_child_info(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    await callback.message.answer("Отлично! Используем сохранённые данные.")

    # Переходим сразу к этапу подтверждения оплаты
    # Здесь можно показать сообщение с QR-кодом, кнопкой "Оплата наличными" и т.д.

    # Подразумеваем, что после подтверждения пользователь попадает на оплату:
    await state.set_state(RegistrationState.checking_payment)

    await callback.answer()
    await handle_child_birth_date(message=callback.message, state=state)




# -- Утилита создания или получения пользователя --
def get_or_create_user(telegram_id, username=None, full_name=None):
    print(f"[DEBUG] Утилита создания или получения пользователя:")
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute("INSERT INTO users (telegram_id, username, full_name) VALUES (?, ?, ?)",
                    (telegram_id, username or '', full_name or ''))
        return cur.lastrowid

# -- Утилита создания или получения ребенка --
def get_or_create_child(user_id, child_name, comment, birth_date):
    print(f"[DEBUG] Утилита создания или получения ребенка: user_id: {user_id}, child_name: {child_name}, comment: {comment}, birth_date:{birth_date}")
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id FROM children
            WHERE user_id = ? AND child_name = ? AND comment = ? AND birth_date = ?
        """, (user_id, child_name, comment, birth_date))
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute("""
            INSERT INTO children (user_id, child_name, comment, birth_date)
            VALUES (?, ?, ?, ?)
        """, (user_id, child_name, comment, birth_date ))
        return cur.lastrowid

# -- Начало регистрации --
@router.callback_query(lambda c: c.data and c.data.startswith("signup_"))
async def handle_register(callback: CallbackQuery, state: FSMContext):
    print(f"[DEBUG] Начало регистрации")
    event_index = int(callback.data.split("_")[1])
    events = get_all_events()
    event = events[event_index]

    # Распакуем нужные поля
    event_id, title, description, date, time, price, qr_path, payment_link, location, photo_path = event

    # Сохраняем всё в FSMContext
    await state.update_data(
        event_index=event_index,
        event_id=event_id,
        event_title=title,
        event_date=date,
        event_time=time
    )

    await callback.message.answer("👧 Введите имя ребёнка:")
    await state.set_state(RegistrationState.entering_child_name)
    await callback.answer()

# -- Имя ребёнка --
@router.message(RegistrationState.entering_child_name)
async def handle_child_name(message: Message, state: FSMContext):
    print(f"[DEBUG] Имя ребёнка: message: {Message}, state: {FSMContext}")
    await state.update_data(child_name=message.text.strip())
    await message.answer("❗ Есть ли у ребёнка аллергии или пожелания?")
    await state.set_state(RegistrationState.entering_allergy_info)

# -- Комментарий --
@router.message(RegistrationState.entering_allergy_info)
async def handle_allergy_info(message: Message, state: FSMContext):
    print(f"[DEBUG] Комментарий message: {Message}, state: {FSMContext}")
    await state.update_data(comment=message.text.strip())
    await message.answer("🎂 Пожалуйста, укажите дату рождения в формате ДД.ММ.ГГГГ:")
    await state.set_state(RegistrationState.entering_birth_date)

# -- Возраст ребёнка --
@router.message(RegistrationState.entering_birth_date)
async def handle_child_birth_date(message: Message, state: FSMContext):
    print(f"[DEBUG] Возраст ребёнка")
    await state.update_data(event_id=event_id)
    birth_date = message.text.strip()

    # Простейшая валидация: дата в формате ДД.ММ.ГГГГ
    if not re.match(r"^\d{2}\.\d{2}\.\d{4}$", birth_date):
        await message.answer("❗ Пожалуйста, укажите дату рождения в формате ДД.ММ.ГГГГ.")
        return


    await state.update_data(birth_date=birth_date)
    data = await state.get_data()
    user = message.from_user
    user_id = get_or_create_user(user.id, user.username, user.full_name)
    child_id = get_or_create_child(user_id, data['child_name'], data['comment'], data['birth_date'])

    event = get_all_events()[data['event_index']]
    event_id, _, _, event_date, event_time, _, qr_path, payment_link, _, _ = event

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO registrations (user_id, event_id, child_id) VALUES (?, ?, ?)",
                    (user_id, event_id, child_id))
        registration_id = cur.lastrowid

    caption = (
        f"Спасибо! Для завершения записи переведите оплату по ссылке ниже:\n"
        f'<a href="{payment_link}">Оплатить участие</a>\n\n'
        f"💳 Стоимость: 500₽\n"
        f"После оплаты, пожалуйста, отправьте чек (фото или PDF) в ответ на это сообщение."
    )

    qr_file = FSInputFile(qr_path)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Оплачу наличными", callback_data="pay_cash")]
    ])

    await message.answer_photo(photo=qr_file, caption=caption, parse_mode="HTML", reply_markup=keyboard)
    await state.update_data(user_id=user_id, registration_id=registration_id)
    await state.set_state(RegistrationState.notify_admins_about_registration) #вызов следующего шага

# -- Оплата наличными --
@router.callback_query(F.data == "pay_cash")
async def handle_cash_payment(callback: CallbackQuery, state: FSMContext):
    print(f"[DEBUG] Оплата наличными: callback:{CallbackQuery}, state: {FSMContext}")
    data = await state.get_data()
    user = callback.from_user

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO payments (registration_id, user_id, payment_type, check_path) VALUES (?, ?, ?, ?)",
                    (data['registration_id'], data['user_id'], "наличными", "CASH"))


    #вызовем функцию уведомления администратора и передадим данные
    data = await state.get_data()

    await notify_admins_about_registration(
        bot=callback.message.bot,
        admins=ADMINS,
        parent_name=callback.from_user.full_name,
        username=callback.from_user.username,
        child_name=data["child_name"],
        birth_date=data["birth_date"],
        comment=data["comment"],
        event_title=data["event_title"],
        event_date=data["event_date"],
        event_time=data["event_time"],
    )

    await callback.message.answer("Спасибо! Вы записаны. Администратор уведомлен.")
    await callback.answer()
    await state.set_state(RegistrationState.waiting_for_payment_check) #вызов следующего шага
    await state.clear()

# -- Получение чека --
@router.message(RegistrationState.waiting_for_payment_check)
async def handle_payment_check(message: Message, state: FSMContext):
    print(f"[DEBUG] Получение чека: message:{Message}, state: {FSMContext}")
    tg_user = message.from_user
    file = message.photo[-1] if message.photo else message.document
    ext = "jpg" if message.photo else "pdf"

    if not file:
        await message.answer("Пожалуйста, пришлите чек как фото или PDF-документ.")
        return

    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{tg_user.id}_{now_str}.{ext}"
    full_path = os.path.join(CHECKS_DIR, filename)

    await message.bot.download(file.file_id, destination=full_path)
    data = await state.get_data()

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO payments (registration_id, user_id, payment_type, check_path) VALUES (?, ?, ?, ?)",
                    (data['registration_id'], data['user_id'], "онлайн", full_path))
        

    #вызовем функцию уведомления администратора и передадим данные
    data = await state.get_data()

    await notify_admins_about_registration(
        bot=message.bot,
        admins=ADMINS,
        parent_name=message.from_user.full_name,
        username=message.from_user.username,
        child_name=data["child_name"],
        birth_date=data["birth_date"],
        comment=data["comment"],
        event_title=data["event_title"],
        event_date=data["event_date"],
        event_time=data["event_time"],
    )


    await message.answer("✅ Спасибо! Чек получен. До встречи на мастер-классе!")
    await state.set_state(RegistrationState.notify_admins_about_registration) #вызов следующего шага
    await state.clear()
    

#Отправка уведомлений администраторам
#@router.message(RegistrationState.notify_admins_about_registration)
async def notify_admins_about_registration(
    bot: Bot,
    admins: list[int],
    parent_name: str,
    username: str | None,
    child_name: str,
    birth_date: str,
    comment: str,
    event_title: str,
    event_date: str,
    event_time: str
):
    #data = await state.get_data()
    """
    Уведомление администраторов о новой записи
    """
    text = (
        f"📢 {hbold('Новая запись!')}\n\n"
        f"👤 Родитель: {parent_name}\n"
        f"👤 Логин: {username}\n"
        f"👶 Ребёнок: {child_name}\n"
        f"🎂 День рождения: {birth_date}\n"
        f"📌 Комментарий: {comment or '–'}\n\n"
        f"🎨 Мастер-класс: {event_title}\n"
        f"📅 Дата: {event_date}\n"
        f"🕒 Время: {event_time}"
    )

    for admin_id in admins:
        try:
            await bot.send_message(admin_id, text)
        except Exception as e:
            print(f"[ERROR] Не удалось отправить сообщение админу {admin_id}: {e}")

    #await callback.message.answer("Спасибо! Вы записаны. Администратор уведомлен.")
    #await callback.answer()
    #await state.clear()





