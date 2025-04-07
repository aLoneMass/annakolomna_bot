import sqlite3
from config import DB_PATH

def migrate():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("ALTER TABLE registrations ADD COLUMN comment TEXT")
        conn.commit()
        print("✅ Поле comment добавлено в таблицу registrations.")

if __name__ == "__main__":
    migrate()
