import sqlite3
from config import DB_PATH

def get_all_registrations():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT u.username, r.child_name, r.comment, e.date, e.time, r.payment_type
            FROM registrations r
            JOIN users u ON u.id = r.user_id
            JOIN events e ON e.id = r.event_id
            ORDER BY e.date DESC, e.time DESC
        """)
        return cur.fetchall()
