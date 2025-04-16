import sqlite3
from config import DB_PATH

def get_all_events():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                id,
                title,
                description,
                date,
                time,
                price,
                qr_path,
                payment_link,
                location,
                photo_path
            FROM events
            ORDER BY date, time
        """)
        print(f"[DEBUG get_al_events]:{cur.fetchall()}")
        return cur.fetchall()

