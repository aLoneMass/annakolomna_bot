from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMINS = list(map(int, os.getenv('ADMINS', '').split(',')))
DB_PATH = 'database/db.sqlite3'
PHOTO_DIR = 'data/event_photos/'
CHECKS_DIR = 'data/payment_checks/'
QR_DIR = 'data/qr_codes/'
