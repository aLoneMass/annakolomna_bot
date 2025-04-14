import sqlite3
from config import DB_PATH

def get_all_events():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                id,
                description,
                date,
                time,
                qr_path,
                payment_link,
                photo_path,
                location
            FROM events
            ORDER BY date, time
        """)
        return cur.fetchall()

