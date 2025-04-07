import sqlite3
from config import DB_PATH

def get_all_events():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, photo_path, description, date, time, location, payment_link, qr_path
            FROM events
            ORDER BY date ASC, time ASC
        """)
        return cur.fetchall()
