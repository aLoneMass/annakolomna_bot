from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from bot.states.registration import RegistrationState
from bot.services.events import get_all_events




import os
import datetime
import sys
from pathlib import Path
sys.path.append(str((Path(__file__).resolve().parent.parent)))
from config import CHECKS_DIR, ADMINS
from config import DB_PATH


import sqlite3
from config import DB_PATH

def get_or_create_user(telegram_id: int, username=None, full_name=None,
                       child_name=None, comment=None, child_age=None) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        # Проверяем, существует ли пользователь
        cur.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cur.fetchone()
        if row:
            # Обновляем данные ребенка, если они заданы (используя COALESCE, чтобы не перезаписывать, если новое значение пустое)
            cur.execute("""
                UPDATE users 
                SET child_name = CASE WHEN ? != '' THEN ? ELSE child_name END,
                    comment = CASE WHEN ? != '' THEN ? ELSE comment END,
                    child_age = CASE WHEN ? IS NOT NULL THEN ? ELSE child_age END
                WHERE telegram_id = ?
            """, (child_name, child_name, comment, comment, child_age, child_age, telegram_id))
            conn.commit()
            return row[0]
        else:
            cur.execute("""
                INSERT INTO users (telegram_id, username, full_name, child_name, comment, child_age)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (telegram_id, username or '', full_name or '', child_name or '', comment or '', child_age))
            conn.commit()
            return cur.lastrowid


router = Router()

# 1. Обработка кнопки "Записаться"
@router.callback_query(lambda c: c.data and c.data.startswith("signup_"))
async def handle_register(callback: CallbackQuery, state: FSMContext):
    event_index = int(callback.data.split("_")[1])
    user = callback.from_user

    # Сохраняем индекс события
    await state.update_data(event_index=event_index)

    # Проверка: есть ли уже имя ребёнка для этого telegram_id
    import sqlite3
    from config import DB_PATH

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT r.child_name FROM registrations r
            JOIN users u ON u.id = r.user_id
            WHERE u.telegram_id = ?
            ORDER BY r.id DESC LIMIT 1
        """, (user.id,))
        row = cur.fetchone()

    if row:
        child_name = row[0]
        await state.update_data(child_name=child_name)
        await callback.message.answer(
            f"👧 Ранее вы записывали ребёнка по имени <b>{child_name}</b>.\n"
            "Хотите записать его на этот мастер-класс?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Да", callback_data="confirm_child"),
                 InlineKeyboardButton(text="❌ Указать другое", callback_data="enter_new_child")]
            ]),
            parse_mode="HTML"
        )
        await state.set_state(RegistrationState.confirming_child)
    else:
        await callback.message.answer("👧 Введите имя ребёнка, которого вы хотите записать:")
        await state.set_state(RegistrationState.entering_child_name)

@router.callback_query(F.data == "confirm_child")
async def confirm_existing_child(callback: CallbackQuery, state: FSMContext):
    tg_user = callback.from_user

    import sqlite3
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT child_name, comment, child_age FROM users WHERE telegram_id = ?
        """, (tg_user.id,))
        row = cur.fetchone()

    if row:
        child_name, comment, child_age = row
        await state.update_data(child_name=child_name, comment=comment)
        if child_age is None:
            await callback.message.answer("Пожалуйста, укажите возраст ребенка:")
            await state.set_state(RegistrationState.entering_child_age)
        else:
            await callback.message.answer(
                f"Использовать ранее указанные данные? \nИмя: <b>{child_name}</b>\nКомментарий: <code>{comment or 'Нет'}</code>\nВозраст: {child_age}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Да", callback_data="data_confirm")],
                    [InlineKeyboardButton(text="❌ Изменить данные", callback_data="data_reenter")]
                ]),
                parse_mode="HTML"
            )
            await state.set_state(RegistrationState.confirming_child)
    else:
        await callback.message.answer("👧 Введите имя ребенка:")
        await state.set_state(RegistrationState.entering_child_name)

    await callback.answer()


@router.message(RegistrationState.entering_child_age)
async def handle_child_age(message: Message, state: FSMContext):
    try:
        child_age = int(message.text.strip())
    except ValueError:
        await message.answer("Пожалуйста, введите возраст числом.")
        return

    await state.update_data(child_age=child_age)
    # После ввода возраста переходим к шагу с комментариями, если они еще не заданы
    data = await state.get_data()
    if not data.get("comment"):
        await message.answer("📝 Укажите, есть ли аллергии или пожелания для ребенка.")
        await state.set_state(RegistrationState.entering_allergy_info)
    else:
        # Если комментарий уже есть, переходим к оплате
        await handle_allergy_info(message, state)



@router.callback_query(F.data == "enter_new_child")
async def enter_new_child(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("👧 Введите новое имя ребёнка:")
    await state.set_state(RegistrationState.entering_child_name)
    await callback.answer()


# 2. Ввод имени ребёнка → спрашиваем об аллергиях
@router.message(RegistrationState.entering_child_name)
async def handle_child_name(message: Message, state: FSMContext):
    child_name = message.text.strip()
    await state.update_data(child_name=child_name)

    await message.answer("❗ Есть ли у ребёнка (или детей) аллергии на какие-либо материалы? Напишите в свободной форме.")
    await state.set_state(RegistrationState.entering_allergy_info)


# 3. Ввод аллергий → выдаём оплату и QR
@router.message(RegistrationState.entering_allergy_info)
async def handle_allergy_info(message: Message, state: FSMContext):
    comment = message.text.strip()
    await state.update_data(comment=comment)

    data = await state.get_data()
    event_index = data.get("event_index")
    events = get_all_events()
    event = events[event_index]

    payment_link = event[6]
    qr_path = event[7]


    caption = (
        f"Спасибо! Для завершения записи переведите оплату по ссылке ниже:\n"
        f'<a href="{payment_link}">Оплатить участие</a>\n\n'
        f"💳 Стоимость: 500₽\n"
        f"После оплаты, пожалуйста, отправьте чек (фото) в ответ на это сообщение."
    )

    print(f"[DEBUG] qr_path = {qr_path}")

    qr_file = FSInputFile(qr_path)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💵 Оплачу наличными", callback_data="pay_cash")]
    ])

    await message.answer_photo(
        photo=qr_file,
        caption=caption,
        parse_mode="HTML",
        reply_markup=keyboard
    )

    await state.set_state(RegistrationState.waiting_for_payment_check)

@router.callback_query(F.data == "pay_cash")
async def handle_cash_payment(callback: CallbackQuery, state: FSMContext):
    from config import ADMINS
    import sqlite3

    data = await state.get_data()
    tg_user = callback.from_user
    child_name = data.get("child_name")
    comment = data.get("comment", "")
    event_index = data.get("event_index")
    user_id = get_or_create_user_id(
        tg_user.id,
        username=tg_user.username,
        full_name=tg_user.full_name
    )

    events = get_all_events()
    event = events[event_index]
    event_id = event[0]
    event_date = event[3]
    event_time = event[4]


    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO users (telegram_id, username, full_name) VALUES (?, ?, ?)", (
            tg_user.id, tg_user.username, tg_user.full_name
        ))
        cur.execute("SELECT id FROM users WHERE telegram_id = ?", (tg_user.id,))
        user_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO registrations (user_id, event_id, child_name, comment)
            VALUES (?, ?, ?, ?)
        """, (user_id, event_id, child_name, comment))

        registration_id = cur.lastrowid

        # помечаем, что будет наличная оплата (без чека)
        cur.execute("""
            INSERT INTO payments (registration_id, amount, check_path, created_at)
            VALUES (?, ?, ?, ?)
        """, (registration_id, "500", "CASH", datetime.datetime.now().isoformat()))

        conn.commit()

    # Уведомление администраторам
    for admin_id in ADMINS:
        
        chat_id=admin_id,
        #from_user = callback.message.from_user
        from_user = callback.from_user
        username = from_user.username
        full_name = from_user.full_name

        if username and full_name:
            user_display = f"@{username} ({full_name})"
        elif username:
            user_display = f"@{username}"
        else:
            user_display = full_name or "Без имени"

        admin_text = (
            f"📩 Новая запись от {user_display}\n"
            f"👧 Имя ребёнка: {child_name}\n"
            f"📅 Мероприятие: {event_date}\n"
            f"🕒 Время: {event_time}\n"
            f"💬 Комментарий: {comment or '—'}\n"
            f"💰 Оплата: наличными"
        )
        await callback.bot.send_message(chat_id=admin_id, text=admin_text)
    
        

    await callback.message.answer("Спасибо! Вы записаны на мастер-класс! \nМы передадим администратору, что вы оплатите наличными на месте.")
    await callback.answer()
    await state.clear()


@router.callback_query(F.data == "comment_confirm")
async def confirm_old_comment(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    comment = data.get("comment")

    await callback.message.answer("Спасибо! Используем предыдущий комментарий.")
    
    # Передаём его как будто пользователь только что его ввёл
    # Сохраняем комментарий в состояние
    await state.update_data(comment=comment)

    # Получаем данные
    data = await state.get_data()
    event_index = data.get("event_index")
    events = get_all_events()
    event = events[event_index]

    payment_link = event[6]
    qr_path = event[7]

    caption = (
        f"Спасибо! Для завершения записи переведите оплату по ссылке ниже:\n"
        f'<a href="{payment_link}">Оплатить участие</a>\n\n'
        f"💳 Стоимость: 500₽\n"
        f"После оплаты, пожалуйста, отправьте чек (фото) в ответ на это сообщение."
    )

    qr_file = FSInputFile(qr_path)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💵 Оплачу наличными", callback_data="pay_cash")]
    ])

    await callback.message.answer_photo(
        photo=qr_file,
        caption=caption,
        parse_mode="HTML",
        reply_markup=keyboard
    )

    await state.set_state(RegistrationState.waiting_for_payment_check)



@router.callback_query(F.data == "comment_reenter")
async def reenter_comment(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("✍️ Хорошо, введите новый комментарий.")
    await state.set_state(RegistrationState.entering_allergy_info)
    await callback.answer()


    
@router.message(RegistrationState.waiting_for_payment_check)
async def handle_payment_check(message: Message, state: FSMContext):
    tg_user = message.from_user

    file = None
    file_ext = None

    if message.photo:
        file = message.photo[-1]
        file_ext = "jpg"
    elif message.document:
        if message.document.mime_type == "application/pdf":
            file = message.document
            file_ext = "pdf"

    if not file:
        await message.answer("Пожалуйста, пришлите чек как фотографию или PDF-документ.")
        return

    # Сохраняем файл
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{tg_user.id}_{now_str}.{file_ext}"
    full_path = os.path.join(CHECKS_DIR, filename)

    await message.bot.download(file.file_id, destination=full_path)

    # Получаем данные из состояния
    data = await state.get_data()
    child_name = data.get("child_name")
    comment = data.get("comment", "")
    event_index = data.get("event_index")

    events = get_all_events()
    event = events[event_index]
    event_id = event[0]
    event_date = event[3]
    event_time = event[4]

    user_id = get_or_create_user(
        tg_user.id,
        username=tg_user.username,
        full_name=tg_user.full_name,
        child_name=data.get("child_name"),
        comment=data.get("comment"),
        child_age=data.get("child_age")
    )

    import sqlite3
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO registrations (user_id, event_id)
            VALUES (?, ?)
        """, (user_id, event_id))
        registration_id = cur.lastrowid

        # В таблицу payments добавляем новую колонку payer_telegram_id
        cur.execute("""
            INSERT INTO payments (registration_id, amount, check_path, created_at, payer_telegram_id)
            VALUES (?, ?, ?, ?, ?)
        """, (registration_id, "500", full_path, datetime.datetime.now().isoformat(), tg_user.id))
        conn.commit()



    # Отправка админу
    for admin_id in ADMINS:
        await message.bot.send_message(
            chat_id=admin_id,
            text=(
                f"📥 Новая запись от @{message.from_user.username or 'пользователя'} (ID: {message.from_user.id})</b>\n"
                f"👧 Имя ребёнка: {child_name}\n"
                f"📅 Мероприятие: {event_date}\n"
                f"🕒 Время: {event_time}\n"
                f"📝 Комментарий: {comment or 'Нет'}"
            )
        )
        if file_ext == "jpg":
            await message.bot.send_photo(chat_id=admin_id, photo=FSInputFile(full_path))
        elif file_ext == "pdf":
            await message.bot.send_document(chat_id=admin_id, document=FSInputFile(full_path))

    await message.answer("✅ Спасибо! Ваша запись сохранена. До встречи на мастер-классе! 🧡")
    await state.clear()

