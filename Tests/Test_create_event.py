import asyncio
import sqlite3
from config import DB_PATH

import pytest
from aiogram.fsm.context import FSMContext
from types import SimpleNamespace
from bot.handlers.admin import (
    start_create_template,
    handle_template_fields,
    receive_event_dates,
    receive_event_times,
    confirm_event_save
)
from bot.states.admin import AdminCreateEventState
from aiogram.types import Message, CallbackQuery
from unittest.mock import AsyncMock

class FakeMessage:
    def __init__(self, text=None, photo=None):
        self.text = text
        self.photo = photo or []
        self.answer = AsyncMock()

class FakeCallback:
    def __init__(self, data):
        self.data = data
        self.message = FakeMessage()
        self.answer = AsyncMock()

class FakeFSMContext:
    def __init__(self):
        self.data = {}
        self.state = None

    async def set_state(self, state):
        self.state = state

    async def get_state(self):
        return self.state

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def get_data(self):
        return self.data

    async def clear(self):
        self.state = None
        self.data.clear()

@pytest.mark.asyncio
async def test_create_event_flow():
    state = FakeFSMContext()

    # simulate button press
    callback = FakeCallback(data="create_event")
    await start_create_template(callback, state)

    # step-by-step input simulation
    texts = [
        "Тестовый мастер-класс",  # title
        "Описание события",        # description
        None,                     # photo (as file_id)
        None,                     # qr (as file_id)
        "https://pay.link",       # link
        "ул. Пушкина, 10",        # location
        "500"                     # price
    ]

    for i, text in enumerate(texts):
        msg = FakeMessage(text=text)
        if text is None:
            msg.photo = [SimpleNamespace(file_id=f"file_id_{i}")]
        await handle_template_fields(msg, state)

    # simulate date input
    await receive_event_dates(FakeMessage(text="24.04.2025, 26.04.2025"), state)

    # simulate time input for each date
    await receive_event_times(FakeMessage(text="10:00"), state)  # for 24
    await receive_event_times(FakeMessage(text="14:00"), state)  # for 26

    # simulate confirmation
    confirm_callback = FakeCallback(data="confirm_event")
    confirm_callback.message = FakeMessage()
    await confirm_event_save(confirm_callback, state)

    # assert final state cleared
    assert state.get_state() is None
    import sqlite3
    from config import DB_PATH

    # Проверка, что шаблон создан в БД
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT title, price FROM event_templates WHERE title = ?", ("Тестовый мастер-класс",))
    template_row = cursor.fetchone()
    assert template_row is not None, "⛔ Не найден шаблон мастер-класса в БД"
    assert template_row[1] == 500, "⛔ Неверная цена в шаблоне"

    cursor.execute("SELECT COUNT(*) FROM events WHERE template_id = (SELECT id FROM event_templates WHERE title = ?)", ("Тестовый мастер-класс",))
    event_count = cursor.fetchone()[0]
    assert event_count == 2, "⛔ Должно быть 2 события по датам"

        # Очистка созданных записей (cleanup)
    cursor.execute("DELETE FROM events WHERE template_id = (SELECT id FROM event_templates WHERE title = ?)", ("Тестовый мастер-класс",))
    cursor.execute("DELETE FROM event_templates WHERE title = ?", ("Тестовый мастер-класс",))
    conn.commit()
    conn.close()
    print("✅ FSM автотест завершён без ошибок и данные в БД корректны")

if __name__ == "__main__":
    asyncio.run(test_create_event_flow())
