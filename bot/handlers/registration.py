from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.fsm.context import FSMContext
from bot.states.registration import RegistrationState
from bot.services.events import get_all_events
import os
import datetime
from config import CHECKS_DIR, ADMINS

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
    allergy_info = message.text.strip()
    await state.update_data(allergy_info=allergy_info)

    data = await state.get_data()
    event_index = data.get("event_index")
    events = get_all_events()
    event = events[event_index]

    payment_link = event[5]
    qr_path = event[6]

    caption = (
        f"Спасибо! Для завершения записи переведите оплату по ссылке ниже:\n"
        f"<a href=\"{payment_link}\">Оплатить участие</a>\n\n"
        f"💳 Стоимость: 500₽\n"
        f"После оплаты, пожалуйста, отправьте чек (фото) в ответ на это сообщение."
    )

    qr_file = FSInputFile(qr_path)
    await message.answer_photo(
        photo=qr_file,
        caption=caption,
        parse_mode="HTML"
    )

    await state.set_state(RegistrationState.waiting_for_payment_check)
    
@router.message(RegistrationState.waiting_for_payment_check)
async def handle_payment_check(message: Message, state: FSMContext):
    if not message.photo:
        await message.answer("Пожалуйста, пришлите чек как фотографию.")
        return

    # Получаем наибольшее качество фото
    photo = message.photo[-1]
    file_id = photo.file_id
    tg_user = message.from_user

    # Сохраняем чек на диск
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{tg_user.id}_{now_str}.jpg"
    full_path = os.path.join(CHECKS_DIR, filename)
    await photo.download(destination=full_path)

    # Получаем данные из состояния
    data = await state.get_data()
    child_name = data.get("child_name")
    comment = data.get("comment")
    event_index = data.get("event_index")

    from bot.services.events import get_all_events
    events = get_all_events()
    event = events[event_index]
    event_id = event[0]
    event_date = event[3]

    # Сохраняем в базу
    import sqlite3
    from config import DB_PATH
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        # users
        cur.execute("INSERT OR IGNORE INTO users (telegram_id, username, full_name) VALUES (?, ?, ?)", (
            tg_user.id,
            tg_user.username,
            tg_user.full_name
        ))

        cur.execute("SELECT id FROM users WHERE telegram_id = ?", (tg_user.id,))
        user_id = cur.fetchone()[0]

        # registrations
        cur.execute("""
            INSERT INTO registrations (user_id, event_id, child_name, comment)
            VALUES (?, ?, ?, ?)
        """, (user_id, event_id, child_name, comment))

        registration_id = cur.lastrowid

        # payments
        cur.execute("""
            INSERT INTO payments (registration_id, amount, check_path, created_at)
            VALUES (?, ?, ?, ?)
        """, (registration_id, "500", full_path, datetime.datetime.now().isoformat()))

        conn.commit()

    # Уведомление админу
    for admin_id in ADMINS:
        await message.bot.send_message(
            chat_id=admin_id,
            text=(
                f"📥 Новая запись на мероприятие от @{tg_user.username} (ID: {tg_user.id})\n"
                f"🧒 Имя ребёнка: {child_name}\n"
                f"📅 Дата мероприятия: {event_date}\n"
                f"📝 Комментарий: {comment}"
            )
        )
        await message.bot.send_photo(chat_id=admin_id, photo=FSInputFile(full_path))

    await message.answer("✅ Спасибо! Ваша запись сохранена. До встречи на мастер-классе! 🧡")
    await state.clear()
