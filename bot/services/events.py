import sqlite3
from config import DB_PATH

# .mode column
# .headers on


def get_all_events(query: str | int):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        print("[DEBUG get_all_events]")
        if isinstance(query, int):
            # Если это целое число — ищем по event_id
            cur.execute("""
                SELECT
                    et.id, et.title, et.description, e.date, e.time, et.price,
                    et.qr_path, et.payment_link, et.location, et.photo_path
                FROM events e
                JOIN event_templates et ON e.template_id = et.id
                WHERE id = ?
            """, (query,))
        else:
            # Иначе — это дата в формате 'YYYY-MM-DD'
            cur.execute("""
                SELECT
                    e.id, et.title, et.description, e.date, e.time, et.price,
                    et.qr_path, et.payment_link, et.location, et.photo_path
                FROM events e
                JOIN event_templates et ON e.template_id = et.id
                WHERE e.date >= ?
                ORDER BY date, time
            """, (query,))

        events = cur.fetchall()
        print(f"[DEBUG get_all_events]: {events}")
        return events


def get_all_templates():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                id, title, description, price,
                qr_path, payment_link, location, photo_path
            FROM event_templates
            ORDER BY id;
        """)
        return cursor.fetchall()
