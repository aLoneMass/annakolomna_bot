import sqlite3
from config import DB_PATH

event = {
    "photo_path": "data/event_photos/2025-04-13.png",
    "description": "Мастер-класс по созданию яркого и оригинального пасхального сувенира. Будем украшать пасхальное яйцо в технике «пластилинография».\nРасширим представления о традициях украшения пасхального яйца.",
    "date": "2025-04-13",
    "time": "14:00",
    "location": "https://yandex.ru/maps/-/CHVj6R6N",
    "payment_link": "https://www.tbank.ru/cf/6O1xmjCNVKI",
    "qr_path": "data/qr_codes/2025-04-13_payment.jpg"
}

def add_event(e):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO events (photo_path, description, date, time, location, payment_link, qr_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            e["photo_path"],
            e["description"],
            e["date"],
            e["time"],
            e["location"],
            e["payment_link"],
            e["qr_path"]
        ))
        conn.commit()
        print("✅ Мероприятие успешно добавлено.")

if __name__ == "__main__":
    add_event(event)
