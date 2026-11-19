import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import List, Dict

from PIL import Image, ImageDraw

from types_.mixin_types import SvitloItem
from .const_ import (
    ROW_HEIGHT, COLOR_BG, FONT, COLOR_TEXT,
    COLOR_ON, COLOR_OFF, BLOCK_WIDTH,
    BLOCK_HEIGHT, BLOCK_SPACING, FONT_BOLD, FONT_SMALL, get_color
)

SECONDS_IN_HOUR = 3600
SECONDS_IN_DAY = 86400


# ======================
# UTILS
# ======================

def parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d")


def day_start_ts(date_str: str) -> int:
    return int(parse_date(date_str).timestamp())


def build_extended_events(events, start_ts, end_ts, start_state):
    extended = [{"timestamp": start_ts, "svitlo": start_state}]

    for e in events:
        extended.append({"timestamp": e.timestamp, "svitlo": e.svitlo})

    extended.append({
        "timestamp": end_ts,
        "svitlo": events[-1].svitlo if events else start_state
    })

    return extended


def calc_overlap(cur, nxt, start, end):
    overlap_start = max(cur["timestamp"], start)
    overlap_end = min(nxt["timestamp"], end)

    if overlap_start >= overlap_end:
        return 0

    return overlap_end - overlap_start


# ======================
# HOURLY STATE
# ======================

def collect_switches(nxt_ts, hour_start, hour_end):
    if hour_start <= nxt_ts < hour_end:
        return [(nxt_ts - hour_start) // 60]
    return []


def classify_hour(on_time, off_time, switches):
    if on_time == 0:
        return "off"
    if off_time == 0:
        return "on"

    is_mixed = any(20 <= m <= 40 for m in switches)
    if is_mixed:
        return "mixed"

    return "on" if on_time > off_time else "off"


def get_hourly_state(day_events, date_str, start_state):
    base_ts = day_start_ts(date_str)

    if not day_events:
        return ["on" if start_state else "off"] * 24

    events = sorted(day_events, key=lambda x: x.timestamp)
    extended = build_extended_events(
        events,
        base_ts,
        base_ts + SECONDS_IN_DAY,
        start_state
    )

    result = []

    for hour in range(24):
        h_start = base_ts + hour * SECONDS_IN_HOUR
        h_end = h_start + SECONDS_IN_HOUR

        on_time = 0
        off_time = 0
        switches = []

        for i in range(len(extended) - 1):
            cur, nxt = extended[i], extended[i + 1]

            duration = calc_overlap(cur, nxt, h_start, h_end)
            if not duration:
                continue

            if cur["svitlo"]:
                on_time += duration
            else:
                off_time += duration

            switches += collect_switches(nxt["timestamp"], h_start, h_end)

        result.append(classify_hour(on_time, off_time, switches))

    return result


# ======================
# EVENTS
# ======================

def group_events_by_day(events) -> Dict[str, List[SvitloItem]]:
    grouped = defaultdict(list)
    for e in events:
        grouped[e.date_str].append(e)
    return grouped


def build_days_range(start_date: datetime, end_date: datetime):
    days = []
    current = start_date

    while current <= end_date:
        days.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    return days


# ======================
# TOTALS
# ======================

def calculate_totals(events, start_ts, end_ts):
    events = sorted(events, key=lambda x: x.timestamp)

    if not events:
        return 0, end_ts - start_ts

    start_state = not events[0].svitlo
    extended = build_extended_events(events, start_ts, end_ts, start_state)

    total_on = 0
    total_off = 0

    for i in range(len(extended) - 1):
        cur, nxt = extended[i], extended[i + 1]
        duration = nxt["timestamp"] - cur["timestamp"]

        if cur["svitlo"]:
            total_on += duration
        else:
            total_off += duration

    return total_on, total_off


# ======================
# DRAW HELPERS
# ======================

# COLORS FOR SUMMARY BAR (tweak freely)
SUMMARY_COLORS = {
    "0_25": (40, 40, 40),       # black
    "25_50": (220, 50, 50),     # red
    "50_75": (255, 140, 0),     # orange
    "75_100": (50, 200, 80),    # green
}


def format_duration(seconds: int):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours} год {minutes} хв"


def format_date_range(start_ts: int, end_ts: int):
    start = datetime.fromtimestamp(start_ts).strftime("%d.%m")
    end = datetime.fromtimestamp(end_ts).strftime("%d.%m")
    return f"{start} - {end}"


def find_best_worst_periods(events, start_ts, end_ts):
    if not events:
        return None, None

    events = sorted(events, key=lambda x: x.timestamp)

    extended = []
    start_state = not events[0].svitlo

    extended.append({"timestamp": start_ts, "svitlo": start_state})

    for e in events:
        extended.append({"timestamp": e.timestamp, "svitlo": e.svitlo})

    extended.append({"timestamp": end_ts, "svitlo": events[-1].svitlo})

    best = {"duration": 0}
    worst = {"duration": 0}

    for i in range(len(extended) - 1):
        cur, nxt = extended[i], extended[i + 1]
        duration = nxt["timestamp"] - cur["timestamp"]

        if cur["svitlo"]:  # light is on
            if duration > best.get("duration", 0):
                best = {
                    "duration": duration,
                    "start": cur["timestamp"],
                    "end": nxt["timestamp"]
                }
        else:  # light is off
            if duration > worst.get("duration", 0):
                worst = {
                    "duration": duration,
                    "start": cur["timestamp"],
                    "end": nxt["timestamp"]
                }

    return best, worst


def get_summary_color(percent):
    if percent < 25:
        return SUMMARY_COLORS["0_25"]
    elif percent < 50:
        return SUMMARY_COLORS["25_50"]
    elif percent < 75:
        return SUMMARY_COLORS["50_75"]
    return SUMMARY_COLORS["75_100"]


def draw_header(draw, width, start_date, end_date):
    padding = 10

    days = (end_date - start_date).days + 1

    title = f"Статистика за {days} днів"
    date_range = f"{start_date.strftime('%d.%m.%Y')} → {end_date.strftime('%d.%m.%Y')}"

    # text sizes
    title_bbox = draw.textbbox((0, 0), title, font=FONT_BOLD)
    date_bbox = draw.textbbox((0, 0), date_range, font=FONT)

    title_width = title_bbox[2] - title_bbox[0]
    date_width = date_bbox[2] - date_bbox[0]

    text_width = max(title_width, date_width)

    title_height = title_bbox[3] - title_bbox[1]
    date_height = date_bbox[3] - date_bbox[1]
    text_height = title_height + date_height + 5

    # centered block coords
    left = (width - text_width) // 2 - padding
    right = left + text_width + padding * 2
    top = 5
    bottom = top + text_height + padding + 5

    # background rect
    draw.rounded_rectangle([left, top, right, bottom], radius=6, fill=(30, 30, 30))

    # centered title
    title_x = (width - title_width) // 2
    current_y = top + padding // 2
    draw.text((title_x, current_y), title, fill=COLOR_TEXT, font=FONT_BOLD)

    # centered date range
    date_x = (width - date_width) // 2
    current_y += title_height + 5
    draw.text((date_x, current_y), date_range, fill=COLOR_TEXT, font=FONT)

    return bottom  # caller uses this to lay out rows below the header


def _draw_labeled_value_centered(draw, x_center, y, label, value, value_color=COLOR_ON):
    """Draw a `label: value` pair, horizontally centered on `x_center`."""
    label_bbox = draw.textbbox((0, 0), label, font=FONT)
    value_bbox = draw.textbbox((0, 0), value, font=FONT)

    label_width = label_bbox[2] - label_bbox[0]
    value_width = value_bbox[2] - value_bbox[0]

    total_width = label_width + 5 + value_width

    start_x = x_center - total_width // 2

    draw.text((start_x, y), label, fill=COLOR_TEXT, font=FONT)
    draw.text((start_x + label_width + 5, y), value, fill=value_color, font=FONT)


def _draw_period_block(draw, left, right, top, bottom, title, title_color, start_ts, end_ts):
    """Draw a best/worst-period block (title + start/end date)."""
    center_x = (left + right) // 2

    # centered title
    title_bbox = draw.textbbox((0, 0), title, font=FONT_BOLD)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = center_x - title_width // 2
    draw.text((title_x, top + 5), title, fill=title_color, font=FONT_BOLD)

    start = datetime.fromtimestamp(start_ts)
    end = datetime.fromtimestamp(end_ts)

    start_value = start.strftime('%d.%m %H:%M')
    end_value = end.strftime('%d.%m %H:%M')

    block_center_y = (top + bottom) // 2

    _draw_labeled_value_centered(draw, center_x, block_center_y - 12, "Старт:", start_value)
    _draw_labeled_value_centered(draw, center_x, block_center_y + 8, "Кінець:", end_value)


def _draw_total_block(draw, left, right, top, bottom, percent_on):
    """Draw the global stats block (bar + percentages)."""
    center_x = (left + right) // 2

    # centered title
    title = "Загальна статистика"
    title_bbox = draw.textbbox((0, 0), title, font=FONT_BOLD)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = center_x - title_width // 2
    draw.text((title_x, top + 5), title, fill=COLOR_TEXT, font=FONT_BOLD)

    # progress bar (15px padding either side)
    bar_width = (right - left) - 30
    bar_height = 15
    bar_y = (top + bottom) // 2 - bar_height // 2 - 5

    bar_left = center_x - bar_width // 2
    bar_right = bar_left + bar_width

    on_width = int(bar_width * percent_on / 100)
    color = get_summary_color(percent_on)

    draw.rectangle([bar_left, bar_y, bar_left + on_width, bar_y + bar_height], fill=color)
    draw.rectangle([bar_left + on_width, bar_y, bar_right, bar_y + bar_height], fill=COLOR_OFF)

    # centered percentages
    percent_text = f"{percent_on:.1f}% / {100 - percent_on:.1f}%"
    percent_bbox = draw.textbbox((0, 0), percent_text, font=FONT)
    percent_width = percent_bbox[2] - percent_bbox[0]
    percent_x = center_x - percent_width // 2
    draw.text((percent_x, bar_y + bar_height + 5), percent_text, fill=COLOR_TEXT, font=FONT)


def draw_footer(draw, y, width, percent_on, best, worst):
    padding = 30
    block_height = 120
    block_width = (width - padding * 2) // 3
    block_spacing = 10

    for i in range(3):
        left = padding + i * block_width
        right = left + block_width - block_spacing
        top = y
        bottom = y + block_height

        # block border
        draw.rectangle([left, top, right, bottom], outline=COLOR_TEXT)

        if i == 0:
            _draw_total_block(draw, left, right, top, bottom, percent_on)

        elif i == 1 and best:
            _draw_period_block(draw, left, right, top, bottom, "Найкращі години",
                               get_color("green"), best["start"], best["end"])

        elif i == 2 and worst:
            _draw_period_block(draw, left, right, top, bottom, "Найгірші години",
                               get_color("red"), worst["start"], worst["end"])


def draw_time_scale(draw, grid_x, y_offset=10):
    x = grid_x

    for hour in range(24):
        label = f"{hour:02d}"

        bbox = draw.textbbox((0, 0), label, font=FONT_SMALL)
        text_w = bbox[2] - bbox[0]

        text_x = x + (BLOCK_WIDTH - text_w) // 2
        text_y = y_offset

        draw.text(
            (text_x, text_y),
            label,
            fill=COLOR_TEXT,
            font=FONT_SMALL
        )

        x += BLOCK_WIDTH + BLOCK_SPACING


def draw_hour_grid(draw, grid_x, start_y, end_y):
    x = grid_x

    # 23 dividers between the 24 hour blocks
    for _ in range(23):
        x += BLOCK_WIDTH  # advance to the right edge of this block
        draw.line(
            [(x, start_y), (x, end_y)],
            fill=(80, 80, 80),
            width=1
        )
        x += BLOCK_SPACING  # skip the inter-block gap


def draw_day_label(draw, date_str, x, y):
    formatted = parse_date(date_str).strftime("%d.%m.%Y")
    draw.text((x, y), formatted, fill=COLOR_TEXT, font=FONT)


def get_mixed_colors(hours, idx):
    if idx > 0:
        is_on_before = hours[idx - 1] == "on"
        return (
            (COLOR_ON, COLOR_OFF)
            if is_on_before else
            (COLOR_OFF, COLOR_ON)
        )

    is_on_after = hours[idx + 1] == "on"
    return (
        (COLOR_OFF, COLOR_ON)
        if is_on_after else
        (COLOR_ON, COLOR_OFF)
    )


def draw_hour_block(draw, x, y, state, hours, idx):
    left = x
    top = y + (ROW_HEIGHT - BLOCK_HEIGHT) // 2 - 7
    right = x + BLOCK_WIDTH
    bottom = top + BLOCK_HEIGHT

    if state == "on":
        draw.rounded_rectangle([left, top, right, bottom], radius=3, fill=COLOR_ON)

    elif state == "off":
        draw.rounded_rectangle([left, top, right, bottom], radius=3, fill=COLOR_OFF)


    else:
        mid = left + BLOCK_WIDTH // 2
        left_fill, right_fill = get_mixed_colors(hours, idx)

        draw.rounded_rectangle([left, top, mid, bottom], radius=3, fill=left_fill)
        draw.rounded_rectangle([mid, top, right, bottom], radius=3, fill=right_fill)


# ======================
# MAIN DRAW
# ======================

def draw_stats(days, grouped_events, all_events, start_date, end_date):
    DATE_X = 25
    GRID_X = 125  # gives more room for date labels

    width = GRID_X + (BLOCK_WIDTH + BLOCK_SPACING) * 24 + 25
    height = ROW_HEIGHT * len(days) + 220

    img = Image.new("RGB", (width, height), COLOR_BG)
    draw = ImageDraw.Draw(img)

    header_bottom = draw_header(draw, width, start_date, end_date)

    # hour scale below the header
    draw_time_scale(draw, GRID_X, y_offset=header_bottom + 10)

    y = header_bottom + 30

    first_event = next((grouped_events[d][0] for d in days if grouped_events.get(d)), None)
    last_state = not first_event.svitlo if first_event else False

    for date_str in days:
        events = grouped_events.get(date_str, [])
        hours = get_hourly_state(events, date_str, last_state)

        draw_day_label(draw, date_str, DATE_X, y)

        x = GRID_X
        for idx, state in enumerate(hours):
            draw_hour_block(draw, x, y, state, hours, idx)
            x += BLOCK_WIDTH + BLOCK_SPACING

        if events:
            last_state = events[-1].svitlo

        y += ROW_HEIGHT

    # === TOTALS ===
    start_ts = day_start_ts(days[0])
    end_ts = day_start_ts(days[-1]) + SECONDS_IN_DAY

    total_on, total_off = calculate_totals(all_events, start_ts, end_ts)
    total = total_on + total_off

    percent_on = (total_on / total) * 100 if total else 0

    best, worst = find_best_worst_periods(all_events, start_ts, end_ts)

    # FOOTER
    draw_footer(draw, y + 10, width, percent_on, best, worst)
    _save_pic(img)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer

def _save_pic(img, filename: str = "stats.png"):
    current_dir = Path(__file__).parent
    output_path = current_dir / filename
    img.save(output_path)

# ======================
# PUBLIC API
# ======================

def _print_event_logs(grouped: Dict[str, List[SvitloItem]]):
    for date_str, events in grouped.items():
        print(f"\nDate: {date_str}. Events: {len(events)}")
        for event in events:
            event_time = datetime.fromtimestamp(event.timestamp).strftime('%H:%M')

            status = "on" if event.svitlo else "off"
            print(f"  [{event_time}]: {status}")


async def generate_visual_stats(events: List[SvitloItem], start_date, end_date):
    """Build the PNG off the event loop so the dispatcher stays responsive
    during the draw (PIL work is pure-CPU + fs writes)."""
    days = build_days_range(start_date, end_date)
    grouped = group_events_by_day(events)
    _print_event_logs(grouped)

    return await asyncio.to_thread(
        draw_stats, days, grouped, events, start_date, end_date
    )


