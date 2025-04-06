import calendar
import datetime
from PIL import Image, ImageDraw, ImageFont

def generate_calendar_image(path="data/calendar.png"):
    now = datetime.datetime.now()
    cal = calendar.monthcalendar(now.year, now.month)
    month_name = calendar.month_name[now.month]

    width, height = 700, 500
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    # Заголовок
    draw.text((width // 2 - 100, 20), f"{month_name} {now.year}", fill="black")

    # Шрифт
    try:
        font = ImageFont.truetype("arial.ttf", size=18)
    except:
        font = ImageFont.load_default()

    # День недели
    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    for i, day in enumerate(days):
        draw.text((50 + i * 90, 60), day, fill="black", font=font)

    # Числа
    for row, week in enumerate(cal):
        for col, day in enumerate(week):
            if day != 0:
                draw.text((50 + col * 90, 100 + row * 50), str(day), fill="black", font=font)

    image.save(path)
    return path
