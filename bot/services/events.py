import sqlite3
from config import DB_PATH

# def get_all_events(from_date: str):
#     with sqlite3.connect(DB_PATH) as conn:
#         cur = conn.cursor()
#         cur.execute("""
#             SELECT
#                 id,
#                 title,
#                 description,
#                 date,
#                 time,
#                 price,
#                 qr_path,
#                 payment_link,
#                 location,
#                 photo_path
#             FROM events
#             WHERE date >= ?
#             ORDER BY date, time
#         """, (from_date,))
#         events = cur.fetchall()
#         print(f"[DEBUG get_all_events]:{events}")
#         return events

# .mode column
# .headers on


def get_all_events(query: str | int):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        if isinstance(query, int):
            # Если это целое число — ищем по event_id
            cur.execute("""
                SELECT
                    id, title, description, date, time, price,
                    qr_path, payment_link, location, photo_path
                FROM events
                WHERE id = ?
            """, (query,))
        else:
            # Иначе — это дата в формате 'YYYY-MM-DD'
            cur.execute("""
                SELECT
                    id, title, description, date, time, price,
                    qr_path, payment_link, location, photo_path
                FROM events
                WHERE date >= ?
                ORDER BY date, time
            """, (query,))

        events = cur.fetchall()
        print(f"[DEBUG get_all_events]: {events}")
        return events
