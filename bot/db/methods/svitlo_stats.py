from typing import Optional, List

from db.mongodb import db_instance
from types_.mixin_types import SvitloItem


async def create_light_on(soc: int, device_sn: int) -> SvitloItem:
    item = SvitloItem(svitlo=True, soc=soc, device_sn=device_sn)
    result = await db_instance["svitlo_stats"].insert_one(item.to_dict())
    item._id = result.inserted_id
    return item


async def create_light_off(soc: int, device_sn: int) -> SvitloItem:
    item = SvitloItem(svitlo=False, soc=soc, device_sn=device_sn)
    result = await db_instance["svitlo_stats"].insert_one(item.to_dict())
    item._id = result.inserted_id
    return item


async def get_last_event(device_sn: int) -> Optional[SvitloItem]:
    result = await db_instance["svitlo_stats"].find_one(
        {"device_sn": device_sn},
        sort=[("timestamp", -1)]
    )
    return SvitloItem.from_dict(result)


async def get_events_by_date(date_str: str) -> List[SvitloItem]:
    """All events on a specific date."""
    cursor = db_instance["svitlo_stats"].find(
        {"date_str": date_str}
    ).sort("timestamp", 1)

    documents = await cursor.to_list(None)
    return [SvitloItem.from_dict(doc) for doc in documents if doc]


async def get_events_by_date_range(start_date: str, end_date: str, device_sn: int) -> List[SvitloItem]:
    """Events for a given device within a date range (inclusive)."""
    cursor = db_instance["svitlo_stats"].find({
        "date_str": {"$gte": start_date, "$lte": end_date},
        "device_sn": {"$eq": device_sn}
    }).sort("timestamp", 1)

    documents = await cursor.to_list(None)
    return [SvitloItem.from_dict(doc) for doc in documents if doc]


async def get_first_svitlo_item(device_sn: int) -> SvitloItem:
    cursor = db_instance["svitlo_stats"].find(
        {"device_sn": device_sn},
        sort=[("timestamp", 1)]
    )
    documents = await cursor.to_list(None)
    return SvitloItem.from_dict(documents[0]) if documents else None


async def set_device_sn_to_all(device_sn: int):
    await db_instance["svitlo_stats"].update_many({}, {"$set": {"device_sn": device_sn}})
