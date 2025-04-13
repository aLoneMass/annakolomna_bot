import sqlite3
from config import DB_PATH

def get_all_registrations():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                u.username, 
                u.child_name, 
                u.comment, 
                u.child_age, 
                e.date, 
                e.time, 
                CASE
                    WHEN p.check_path = 'CASH' THEN 'Наличными' 
                    ELSE 'Онлайн (чек отправлен)'
                END AS payment_method
            FROM registrations r
            JOIN users u ON u.id = r.user_id
            JOIN events e ON e.id = r.event_id
            JOIN payments p ON p.registration_id = r.id
            ORDER BY e.date DESC, e.time DESC;
        """)
        return cur.fetchall()
