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
    # Получим комментарий из прошлой записи (если есть)
    tg_user = callback.from_user

    import sqlite3
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT r.comment FROM registrations r
            JOIN users u ON u.id = r.user_id
            WHERE u.telegram_id = ?
            ORDER BY r.id DESC LIMIT 1
        """, (tg_user.id,))
        row = cur.fetchone()

    if row and row[0]:
        comment = row[0]
        await state.update_data(comment=comment)

        await callback.message.answer(
            f"📝 Ранее вы указывали комментарий:\n<code>{comment}</code>\nИспользовать его снова?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Да", callback_data="comment_confirm")],
                [InlineKeyboardButton(text="❌ Указать новый", callback_data="comment_reenter")]
            ]),
            parse_mode="HTML"
        )
        await state.set_state(RegistrationState.confirming_comment)
    else:
        await callback.message.answer("📝 Укажите, есть ли аллергии или пожелания для ребёнка.")
        await state.set_state(RegistrationState.entering_allergy_info)

    await callback.answer()



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
    await callback.message.answer("Спасибо! Вы записаны на мастер-класс! \n Мы передадим администратору, что вы оплатите наличными на месте.")
    await callback.answer()
    await state.clear()

@router.callback_query(F.data == "comment_confirm")
async def confirm_old_comment(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    comment = data.get("comment")

    await callback.message.answer("Спасибо! Используем предыдущий комментарий.")
    
    # Передаём его как будто пользователь только что его ввёл
    await handle_allergy_info(
        Message.model_construct(
            message_id=callback.message.message_id,
            chat=callback.message.chat,
            from_user=callback.from_user,
            text=comment
        ),
        state
    )
    await callback.answer()


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
    comment = data.get("comment")
    event_index = data.get("event_index")

    events = get_all_events()
    event = events[event_index]
    event_id = event[0]
    event_date = event[3]

    import sqlite3
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

        cur.execute("""
            INSERT INTO payments (registration_id, amount, check_path, created_at)
            VALUES (?, ?, ?, ?)
        """, (registration_id, "500", full_path, datetime.datetime.now().isoformat()))

        conn.commit()

    # Отправка админу
    for admin_id in ADMINS:
        await message.bot.send_message(
            chat_id=admin_id,
            text=(
                f"📥 Новая запись от @{tg_user.username} (ID: {tg_user.id})\n"
                f"👧 Имя ребёнка: {child_name}\n"
                f"📅 Мероприятие: {event_date}\n"
                f"📝 Комментарий: {comment}"
            )
        )
        if file_ext == "jpg":
            await message.bot.send_photo(chat_id=admin_id, photo=FSInputFile(full_path))
        elif file_ext == "pdf":
            await message.bot.send_document(chat_id=admin_id, document=FSInputFile(full_path))

    await message.answer("✅ Спасибо! Ваша запись сохранена. До встречи на мастер-классе! 🧡")
    await state.clear()

