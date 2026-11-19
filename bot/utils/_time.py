from datetime import datetime

import pytz


def tz_now():
    kyiv_tz = pytz.timezone("Europe/Kyiv")
    return datetime.now(kyiv_tz)


def minutes_to_hhmm(minutes: int | float) -> str:
    minutes = int(minutes)
    if minutes > 1440:
        minutes -= 1440

    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def humanize_minutes(minutes: int | float) -> str:
    minutes = int(minutes)
    if minutes > 1440:
        h = minutes // 60
        m = minutes % 60
        return f"{h} год {m} хв"
    h = minutes // 60
    m = minutes % 60
    return f"{h} год {m} хв"


def humanize_seconds(seconds: int) -> str:
    if seconds <= 0:
        return "0 хв"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours > 0 and minutes > 0:
        return f"{hours} год {minutes} хв"
    elif hours > 0:
        return f"{hours} год"
    elif minutes > 0:
        return f"{minutes} хв"
    else:
        return f"{seconds} сек"

def normalize_yasno_date(date: str) -> str:
    yasno_date = datetime.fromisoformat(date)
    return yasno_date.strftime("%Y-%m-%d")


# print(tz_now().strftime('%Y-%m-%d'))