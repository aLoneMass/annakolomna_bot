from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, FSInputFile
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
@router.callback_query(F.data.startswith("signup_"))
async def handle_signup(callback: CallbackQuery, state: FSMContext):
    index = int(callback.data.split("_")[1])
    events = get_all_events()

    if index >= len(events):
        await callback.answer("Ошибка: мероприятие не найдено.")
        return

    event = events[index]
    await state.update_data(event_index=index)

    await callback.message.answer("👶 Введите имя ребёнка для записи:")
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
    await message.answer_photo(
        photo=qr_file,
        caption=caption,
        parse_mode="HTML"
    )

    await state.set_state(RegistrationState.waiting_for_payment_check)
    
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

