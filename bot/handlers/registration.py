from aiogram import Bot
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import hbold
from aiogram.fsm.context import FSMContext
from bot.states.registration import RegistrationState
from bot.services.events import get_all_events, get_event_by_id
import os
import re
import sqlite3
import datetime
from config import CHECKS_DIR, ADMINS, DB_PATH
from config import ADMINS  # список ID из .env


router = Router()

#Функция вызывается при нажатии на кнопку "Записаться"
@router.callback_query(F.data.startswith("signup_event:"))
#async def handle_signup_event(user_id: int, event_id: int, state: FSMContext):
async def handle_signup_event(callback: CallbackQuery, state: FSMContext):  #В переменной callback будет содержаться значение event_id отправленное с нажатием кнопки "записаться"
    print (f'[DEBUG signup] Пользоваель нажал записаться. вызвано событие signup_event: {F.data.startswith} and bcallback: {callback.data}')
    event_id = int(callback.data.split(":")[1])                             #Вот тут вытаскивается это значение из коллбек.дата в эвент_ид
    user_id = callback.from_user.id
    print (f'[DEBUG signup]   callback.from_user.id: {callback.from_user}')
    # Сохраняем event_id в state
    await state.update_data(event_id=event_id)

    # Проверка: зарегистрирован ли пользователь на это мероприятие
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT p.payment_type
            FROM registrations r
            JOIN users u ON r.user_id = u.id
            LEFT JOIN payments p ON r.id = p.registration_id
            WHERE u.telegram_id = ? AND r.event_id = ?;

        """, (user_id, event_id))
        reg = cur.fetchone()
        print(f'[DEBUG signup] Тип платежа: reg: {reg}')

        if reg:
            payment_type = reg[0]
            print(f'[DEBUG signup] payment_type: {payment_type}')
            if payment_type == "наличными":
                print(f'[DEBUG signup] провалилсь в if "наличными" ')
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💳 Оплатить онлайн", callback_data="pay_online")],
                    # [InlineKeyboardButton(text="🔙 Назад", callback_data="cancel_registration")]
                    [InlineKeyboardButton(text="❌ Закрыть", callback_data="close")]
                ])
                await callback.message.answer(                
                    "Вы уже записаны на это мероприятие и выбрали оплату наличными.\n"
                    "Хотите оплатить онлайн?",
                    reply_markup=keyboard
                )
            elif payment_type == "оплачено":
                print(f'[DEBUG signup] провалилсь в else "оплачено"')
                await callback.message.answer("✅ Вы уже записаны на это мероприятие.")
            else:
                print(f'[DEBUG signup] провалилсь в if "наличными" ')
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💳 Оплатить онлайн", callback_data="pay_online")],
                    [InlineKeyboardButton(text="💶 Оплачу на месте", callback_data="pay_cash")]
                    [InlineKeyboardButton(text="❌ Закрыть", callback_data="close")]
                ])
                await callback.message.answer(                
                    "Вы уже записаны на это мероприятие, но оплата не произведена.\n"
                    "Хотите оплатить онлайн или наличными?",
                    reply_markup=keyboard
                )
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
    print(f'[DEBUG signup] проверка наличия ребенка: {child}')

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
    print(f"[DEBUG get_or_create_user] Утилита создания или получения пользователя:")
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
    print(f"[DEBUG get_or_create_child] user_id: {user_id}, child_name: {child_name}, comment: {comment}, birth_date:{birth_date}")
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id FROM children
            WHERE user_id = ? AND child_name = ?
        """, (user_id, child_name)
        )
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute("""
            INSERT INTO children (user_id, child_name, comment, birth_date)
            VALUES (?, ?, ?, ?)
        """, (user_id, child_name, comment, birth_date ))
        return cur.lastrowid



#1 -- Имя ребёнка --
@router.message(RegistrationState.entering_child_name)
async def handle_child_name(message: Message, state: FSMContext):
    print(f"[DEBUG child_name] message: {Message}, state: {FSMContext}")
    await state.update_data(child_name=message.text.strip())
    await message.answer("❗ Есть ли у ребёнка аллергии или пожелания?")
    await state.set_state(RegistrationState.entering_allergy_info)

#2 -- Запрос комментария --
@router.message(RegistrationState.entering_allergy_info)
async def handle_allergy_info(message: Message, state: FSMContext):
    print(f"[DEBUG coment_step] message: {Message}, state: {FSMContext}")
    await state.update_data(comment=message.text.strip())
    await message.answer("🎂 Пожалуйста, укажите дату рождения в формате ДД.ММ.ГГГГ:")
    await state.set_state(RegistrationState.entering_birth_date)

#3 -- Возраст ребёнка --
@router.message(RegistrationState.entering_birth_date)
async def handle_child_birth_date(message: Message, state: FSMContext):
    data = await state.get_data()
    print(f"[DEBUG birth_date] данные в памяти: {data}")
    event_id = data.get("event_id")      # Получаем event_id из состояния

    print(f"[DEBUG birth_date] event_id: {event_id}")

    birth_date = message.text.strip()   #В переменную birh_date запомним введеное с клавиатуры значение дня рождения

    # Простейшая валидация: дата в формате ДД.ММ.ГГГГ
    if not re.match(r"^\d{2}\.\d{2}\.\d{2}(\d{2})?$", birth_date):
        await message.answer("❗ Пожалуйста, укажите дату рождения в формате ДД.ММ.ГГГГ.")
        return

    await state.update_data(birth_date=birth_date)
    data = await state.get_data()
    print(f"[DEBUG birth_date] данные в памяти обновлены: {data}")
    user = message.from_user
    
    user_id = get_or_create_user(user.id, user.username, user.full_name)
    await state.update_data(user_id=user_id)            # <-- добавь это, важно!
    print(f"[DEBUG birth_date] данные в user_id: {user_id}")
    child_id = get_or_create_child(user_id, data['child_name'], data['comment'], data['birth_date'])
    await state.update_data(child_id=child_id)          # <-- добавь это, важно!
    print(f"[DEBUG birth_date] данные в child_id: {child_id}")

    
    #Тут возможны два варианта, либо вызов процедуры либо выполнение запроса в теле функции.
    event = get_event_by_id(data['event_id'])
    if not event:
        await message.answer("Ошибка: мероприятие не найдено.")
    
    print(f"[DEBUG birth_date] event: {event}")
    (event_id, title, description, location, photo_path, qr_file, payment_link, price, event_date, event_time) = event

    print(f"[DEBUG birth_date] данные в event: {event}")

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO registrations (user_id, child_id, event_id) VALUES (?, ?, ?)
        """, (user_id, child_id, event_id))
        registration_id = cur.lastrowid
    await state.update_data(registration_id=registration_id)    # <-- сохраняем registration_id в состояние

    caption = (
        f"Спасибо! Для завершения записи переведите оплату по ссылке ниже:\n"
        f'<a href="{payment_link}">Оплатить участие</a>\n\n'
        f"💳 Стоимость: 500₽\n"
        f"После оплаты, пожалуйста, отправьте чек (фото или PDF) в ответ на это сообщение."
    )

    #qr_file = FSInputFile(qr_path)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Оплачу наличными", callback_data="pay_cash")]
    ])

    #await message.answer_photo(photo=qr_file, caption=caption, parse_mode="HTML", reply_markup=keyboard)
    if qr_file:
        await message.answer_photo(
            photo=qr_file,
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    else:
        await message.answer(
            text=caption,
            parse_mode="HTML",
            reply_markup=keyboard
        )

    await state.update_data(
        event_id=event_id,
        title=title,
        description=description,
        location=location,
        photo_path=photo_path,
        qr_path=qr_path,
        payment_link=payment_link,
        price=price,
        event_date=event_date,
        event_time=event_time
    )
    await state.set_state(RegistrationState.notify_admins_about_registration) #вызов следующего шага



# -- Оплата наличными --
@router.callback_query(F.data == "pay_cash")
async def handle_cash_payment(callback: CallbackQuery, state: FSMContext):
    print(f"[DEBUG pay_cash] Оплата наличными")
    data = await state.get_data()
    user = callback.from_user
    print(f"[DEBUG pay_cash] user: {user}")

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""INSERT INTO payments (registration_id, user_id, payment_type, check_path) VALUES (?, ?, ?, ?)""",
            (data['registration_id'], data['user_id'], "наличными", "CASH"))
        
    await state.update_data(payment_type="наличными")  # для наличных


    #вызовем функцию уведомления администратора и передадим данные
    data = await state.get_data()
    print(f'[DEBUG cash_payment] admin notification. data:{data}')

    await notify_admins_about_registration(
        bot=callback.message.bot,
        admins=ADMINS,
        parent_name=callback.from_user.full_name,
        username=callback.from_user.username,
        child_name=data["child_name"],
        birth_date=data["birth_date"],
        comment=data["comment"],
        event_title=data["title"],
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
    await state.update_data(payment_type="онлайн", check_path=full_path)    

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












