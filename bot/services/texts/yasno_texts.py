from types_.mixin_types import ScheduleYasno
from types_.types import ScheduleRaw, ScheduleSlot
from utils._time import tz_now, minutes_to_hhmm, normalize_yasno_date

EMOJI = {
    "Definite": "🔌",
    "NotPlanned": "💡",
}

class SvitloEmoji:
    off = "🔌"
    on = "💡"

class SlotTypes:
    off = "Definite"
    on = "NotPlanned"


def get_n_line_schedule(yasno: ScheduleYasno | None, lines: int = 2) -> str:
    if yasno is None:
        return "група Ясно не вказана 🤷"

    schedule = yasno.updates[-1]
    current_slot_idx = _get_current_slot_index(schedule["today"]["slots"])
    if current_slot_idx is None:
        return "не можу знайти графік 😭"

    combined = _merge_today_tomorrow(schedule)
    return _slots_to_text(combined[current_slot_idx: current_slot_idx + lines])


def get_schedule_text(yasno: ScheduleYasno | None) -> str:
    if yasno is None:
        return "Група Ясно не вказана для цього користувача 🤷"

    status = yasno.updates[-1]["today"]["status"]
    if status == "EmergencyShutdowns":
        return "❗️Екстрені відключення"

    current_schedule = yasno.updates[-1]
    today, tomorrow = current_schedule["today"], current_schedule["tomorrow"]
    now = tz_now()

    today_str = normalize_yasno_date(today["date"])

    schedule = f"📊 <b>Сьогодні</b> (<i>{today_str}</i>)"
    schedule += "\n" + _slots_to_text(today["slots"])

    if tomorrow["slots"]:
        tomorrow_str = normalize_yasno_date(tomorrow["date"])
        schedule += f"\n\n📊 <b>Завтра</b> (<i>{tomorrow_str}</i>)"
        schedule += "\n" + _slots_to_text(tomorrow["slots"], with_arrow=False)

    updated = f"🕐 <b>Оновлено:</b> <i>{now.strftime('%H:%M')}</i>"
    yasno_group = f"⚡ <i><b>Черга:</b> {yasno.group}</i>"

    return (f"{schedule}\n\n"
            f"{yasno_group}\n"
            f"{updated}")


def _merge_today_tomorrow(yasno_item: ScheduleRaw) -> list[ScheduleSlot]:
    today, tomorrow = yasno_item["today"]["slots"], yasno_item["tomorrow"]["slots"]
    if not tomorrow:
        return [*today]

    if today[-1]["type"] == tomorrow[0]["type"]:
        today[-1]["end"] += tomorrow[0]["end"]
        return [*today, *tomorrow[1:]]

    return [*today, *tomorrow]


def _get_current_slot_index(slots: list[ScheduleSlot]) -> int | None:
    now = tz_now()
    now_minutes = now.hour * 60 + now.minute

    for index, slot in enumerate(slots):
        start, end = slot["start"], slot["end"]
        if start < now_minutes < end:
            return index

    return None


def _slots_to_text(slots: list[ScheduleSlot], with_arrow: bool = True) -> str | None:
    now = tz_now()
    now_minutes = now.hour * 60 + now.minute
    text = []
    for slot in slots:
        start, end = slot["start"], slot["end"]
        slot_text = f"{EMOJI[slot['type']]} {minutes_to_hhmm(start)}–{minutes_to_hhmm(end)}"
        if with_arrow and start < now_minutes < end:
            slot_text += " ← зараз"

        text.append(f"{slot_text}")

    return "\n".join(text)
