from db.mongodb import db_instance
from types_.mixin_types import ScheduleYasno
from types_.types import ScheduleRaw


def _schedule_msg_doc_id(channel_id: int) -> str:
    return f"schedule_msg:{channel_id}"


async def update_schedule_msg_id(channel_id: int, msg_id: int) -> None:
    await db_instance["config"].update_one(
        {"_id": _schedule_msg_doc_id(channel_id)},
        {"$set": {"schedule_msg_id": msg_id}},
        upsert=True
    )


async def get_schedule_msg_id(channel_id: int) -> int | None:
    doc = await db_instance["config"].find_one({"_id": _schedule_msg_doc_id(channel_id)})
    return doc.get("schedule_msg_id") if doc else None


async def push_yasno_update(
        date_str: str,
        group: str,
        raw_schedule: ScheduleRaw,
) -> ScheduleYasno:
    """Append a new raw_schedule to the `updates` array for (date_str, group).
    Creates the document if none exists yet."""

    update_doc = {
        "$setOnInsert": {
            "date_str": date_str,
            "group": group,
        },
        "$push": {
            "updates": raw_schedule
        }
    }

    await db_instance["yasno"].update_one(
        {"date_str": date_str, "group": group},
        update_doc,
        upsert=True
    )

    doc = await db_instance["yasno"].find_one({"date_str": date_str, "group": group})
    return ScheduleYasno.from_dict(doc)


async def get_yasno_by_date(date_str: str, group: str) -> ScheduleYasno | None:
    doc = await db_instance["yasno"].find_one({"date_str": date_str, "group": group})
    if not doc:
        return None

    return ScheduleYasno.from_dict(doc)


async def get_last_yasno(group: str) -> ScheduleYasno | None:
    doc = await db_instance["yasno"].find_one({"group": group}, sort=[("_id", -1)])
    if not doc:
        return None
    return ScheduleYasno.from_dict(doc)