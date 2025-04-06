from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.fsm.context import FSMContext
from bot.states.registration import RegistrationState
from bot.services.events import get_all_events

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
