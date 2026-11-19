from datetime import datetime, timedelta

from db import mongodb
from services.image.render import generate_visual_stats


async def get_stats(year: int, month: int, day: int, duration: int, device_sn: int):
    """Explicit start-date + duration variant — used by the /stats CLI command."""
    duration -= 1
    start_date_obj = datetime(year, month, day)

    first_event = await mongodb.get_first_svitlo_item(device_sn)
    if first_event is None:
        raise ValueError(f"No svitlo events for device_sn={device_sn}")

    first_event_obj = datetime.strptime(first_event.date_str, "%Y-%m-%d")

    if start_date_obj < first_event_obj:
        start_date_obj = first_event_obj

    desired_end_date = start_date_obj + timedelta(days=duration)

    today = datetime.now().date()
    end_date_obj = min(desired_end_date.date(), today - timedelta(days=1))
    end_date_obj = datetime.combine(end_date_obj, datetime.min.time())

    start_date = start_date_obj.strftime("%Y-%m-%d")
    end_date = end_date_obj.strftime("%Y-%m-%d")

    events = await mongodb.get_events_by_date_range(start_date, end_date, device_sn)
    return await generate_visual_stats(events, start_date_obj, end_date_obj)


async def get_stats_last_days(device_sn: int, days: int):
    """Stats for the last `days` full days ending yesterday."""
    first_event = await mongodb.get_first_svitlo_item(device_sn)
    if first_event is None:
        raise ValueError(f"No svitlo events for device_sn={device_sn}")

    today = datetime.now().date()
    end = today - timedelta(days=1)
    start = end - timedelta(days=days - 1)

    first_date = datetime.strptime(first_event.date_str, "%Y-%m-%d").date()
    if start < first_date:
        start = first_date

    start_obj = datetime.combine(start, datetime.min.time())
    end_obj = datetime.combine(end, datetime.min.time())

    events = await mongodb.get_events_by_date_range(
        start.strftime("%Y-%m-%d"),
        end.strftime("%Y-%m-%d"),
        device_sn,
    )
    return await generate_visual_stats(events, start_obj, end_obj)


async def get_stats_all_time(device_sn: int):
    """Stats from the very first recorded event to yesterday."""
    first_event = await mongodb.get_first_svitlo_item(device_sn)
    if first_event is None:
        raise ValueError(f"No svitlo events for device_sn={device_sn}")

    start_obj = datetime.strptime(first_event.date_str, "%Y-%m-%d")
    today = datetime.now().date()
    end = max(today - timedelta(days=1), start_obj.date())
    end_obj = datetime.combine(end, datetime.min.time())

    events = await mongodb.get_events_by_date_range(
        start_obj.strftime("%Y-%m-%d"),
        end.strftime("%Y-%m-%d"),
        device_sn,
    )
    return await generate_visual_stats(events, start_obj, end_obj)


async def get_stats_current_month(device_sn: int):
    """Stats from the 1st of this month through yesterday."""
    first_event = await mongodb.get_first_svitlo_item(device_sn)
    if first_event is None:
        raise ValueError(f"No svitlo events for device_sn={device_sn}")

    today = datetime.now().date()
    start = today.replace(day=1)
    end = today - timedelta(days=1)

    if end < start:
        # it's the 1st of the month — no complete days yet
        raise ValueError("Поточний місяць ще не має завершених днів")

    first_date = datetime.strptime(first_event.date_str, "%Y-%m-%d").date()
    if start < first_date:
        start = first_date
    if end < start:
        raise ValueError(f"No svitlo events for device_sn={device_sn}")

    start_obj = datetime.combine(start, datetime.min.time())
    end_obj = datetime.combine(end, datetime.min.time())

    events = await mongodb.get_events_by_date_range(
        start.strftime("%Y-%m-%d"),
        end.strftime("%Y-%m-%d"),
        device_sn,
    )
    return await generate_visual_stats(events, start_obj, end_obj)


async def get_stats_previous_month(device_sn: int):
    """Stats for the entire previous calendar month."""
    first_event = await mongodb.get_first_svitlo_item(device_sn)
    if first_event is None:
        raise ValueError(f"No svitlo events for device_sn={device_sn}")

    today = datetime.now().date()
    first_of_this_month = today.replace(day=1)
    end = first_of_this_month - timedelta(days=1)
    start = end.replace(day=1)

    first_date = datetime.strptime(first_event.date_str, "%Y-%m-%d").date()
    if end < first_date:
        raise ValueError("Немає даних за минулий місяць")
    if start < first_date:
        start = first_date

    start_obj = datetime.combine(start, datetime.min.time())
    end_obj = datetime.combine(end, datetime.min.time())

    events = await mongodb.get_events_by_date_range(
        start.strftime("%Y-%m-%d"),
        end.strftime("%Y-%m-%d"),
        device_sn,
    )
    return await generate_visual_stats(events, start_obj, end_obj)
