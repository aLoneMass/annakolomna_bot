import sqlite3
from pathlib import Path

DB_PATH = Path("database/db.sqlite3")

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        # Таблица мероприятий
        cur.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                photo_path TEXT,
                description TEXT,
                date TEXT,
                time TEXT,
                location TEXT,
                payment_link TEXT,
                qr_path TEXT
            )
        """)

        # Таблица пользователей
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                username TEXT,
                full_name TEXT
            )
        """)

        # Таблица регистраций
        cur.execute("""
            CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_id INTEGER,
                child_name TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(event_id) REFERENCES events(id)
            )
        """)

        # Таблица чеков
        cur.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                registration_id INTEGER,
                amount TEXT,
                check_path TEXT,
                created_at TEXT,
                FOREIGN KEY(registration_id) REFERENCES registrations(id)
            )
        """)

        conn.commit()
        print("✅ База данных и таблицы инициализированы.")

if __name__ == "__main__":
    init_db()
