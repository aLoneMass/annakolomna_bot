import sqlite3
from datetime import datetime
from typing import List, Tuple
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
                    e.id AS event_id,
                    et.title,
                    et.description,
                    et.location,
                    et.photo_path,
                    et.qr_path,
                    et.payment_link,
                    et.price,
                    e.date,
                    e.time
                FROM events e
                JOIN event_templates et ON e.template_id = et.id
                WHERE event_id = ?
            """, (query,))  #WHERE e.id = ?
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


# Новая функция выводит все шаблоны от текущей даты
def get_all_templates():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT et.id, et.title, et.description, et.price, et.qr_path, et.payment_link, et.location, et.photo_path 
            FROM event_templates et
            JOIN events e ON e.template_id = et.id
            WHERE date(e.date) >= date('now')
            ORDER BY e.date ASC;
        """)
        return cursor.fetchall()



def get_event_by_id(event_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                e.id AS event_id,
                et.title,
                et.description,
                et.location,
                et.photo_path,
                et.qr_path,
                et.payment_link,
                et.price,
                e.date,
                e.time
            FROM events e
            JOIN event_templates et ON e.template_id = et.id
            WHERE e.id = ?
        """, (event_id,))
        return cur.fetchone()



# Получим расписание (дату и время) для шаблона по id
def get_schedule_for_template(template_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT date, time
            FROM events
            WHERE template_id = ?
            ORDER BY date, time
        """, (template_id,))
        return cur.fetchall()


# Выберем последние события, упорядочим по убыванию и отобразим первые 10 штук
def get_past_events():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT et.id, et.title, et.description, et.price, et.qr_path, et.payment_link, et.location, et.photo_path 
            FROM event_templates et
            JOIN events e ON e.template_id = et.id
            WHERE date(e.date) <= date('now')
            ORDER BY e.date DESC;
        """)
        return cursor.fetchmany(10)




def get_upcoming_events_with_templates(now: datetime) -> List[Tuple[int, str, str, str, str]]:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT e.id, e.date, e.time, t.title, t.location
            FROM events e
            JOIN event_templates t ON e.template_id = t.id
            WHERE datetime(e.date || ' ' || e.time) > ?
        """, (now.isoformat(),))
        return cur.fetchall()
    


def get_event_registrations(event_id: int) -> List[int]:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM registrations WHERE event_id = ?", (event_id,))
        return [row[0] for row in cur.fetchall()]
