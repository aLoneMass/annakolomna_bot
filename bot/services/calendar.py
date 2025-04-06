import calendar
import datetime
from PIL import Image, ImageDraw, ImageFont
import locale

def generate_calendar_image(path="data/calendar.png"):
    # Устанавливаем русскую локаль (если поддерживается)
    try:
        locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")
    except locale.Error:
        pass  # Если русская локаль недоступна, останется дефолт

    now = datetime.datetime.now()
    cal = calendar.monthcalendar(now.year, now.month)
    month_name = now.strftime("%B").capitalize()

    width, height = 800, 600
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    # Используем системный шрифт или fallback
    try:
        font_large = ImageFont.truetype("DejaVuSans.ttf", size=36)
        font = ImageFont.truetype("DejaVuSans.ttf", size=24)
    except:
        font_large = ImageFont.load_default()
        font = ImageFont.load_default()

    # Заголовок месяца
    draw.text((width // 2 - 100, 20), f"{month_name} {now.year}", fill="black", font=font_large)

    # Дни недели
    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    for i, day in enumerate(days):
        draw.text((60 + i * 100, 80), day, fill="black", font=font)

    # Числа
    for row, week in enumerate(cal):
        for col, day in enumerate(week):
            if day != 0:
                draw.text((65 + col * 100, 130 + row * 60), str(day), fill="black", font=font)

    image.save(path)
    return path
