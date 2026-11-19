from typing import Optional, List

from db.mongodb import db_instance
from types_.mixin_types import Plug

COLLECTION_NAME = "plugs"


async def get_plugs() -> List[Plug]:
    docs = await db_instance[COLLECTION_NAME].find().to_list(None)
    return [Plug.from_dict(doc) for doc in docs]

async def get_watcher_enabled_plugs() -> List[Plug]:
    # watcher_enabled shud be True
    docs = await db_instance[COLLECTION_NAME].find({"watcher_enabled": True}).to_list(None)
    return [Plug.from_dict(doc) for doc in docs]

async def get_plug_by_ip(ip: str) -> Optional[Plug]:
    data = await db_instance[COLLECTION_NAME].find_one({"ip": ip})
    return Plug.from_dict(data)

async def update_watcher_enable_state(ip: str, enabled: bool) -> None:
    await db_instance[COLLECTION_NAME].update_one({"ip": ip}, {"$set": {"watcher_enabled": enabled}})

async def update_device_on_state(ip: str, enabled: bool) -> None:
    await db_instance[COLLECTION_NAME].update_one({"ip": ip}, {"$set": {"device_on": enabled}})

async def update_is_online_state(ip: str, enabled: bool) -> None:
    await db_instance[COLLECTION_NAME].update_one({"ip": ip}, {"$set": {"is_online": enabled}})

async def sync_plug_device_info(plug: Plug) -> None:
    await db_instance[COLLECTION_NAME].update_one(
        {"ip": plug.ip},
        {
            "$set": {
                "nickname": plug.nickname,
                "device_on": plug.device_on,
                "is_online": plug.is_online,
                "last_sync": plug.last_sync,
            }
        },
        upsert=True
    )


async def force_update_plug(plug: Plug) -> Optional[Plug]:
    data = plug.to_dict()

    await db_instance[COLLECTION_NAME].update_one(
        {"ip": plug.ip},
        {"$set": data},
        upsert=True
    )

    return plug



