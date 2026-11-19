from typing import Optional, List

from db.mongodb import db_instance
from types_.mixin_types import DeyePersonal, Alerts


COLLECTION_NAME = "deye_personal"

async def create_deye_personal(personal: DeyePersonal) -> DeyePersonal:
    data = personal.to_dict()

    result = await db_instance[COLLECTION_NAME].insert_one(data)
    personal._id = result.inserted_id

    return personal


async def get_deye_personal_by_user_id(user_id: int) -> Optional[DeyePersonal]:
    doc = await db_instance[COLLECTION_NAME].find_one({
        "user_ids": user_id
    })

    return DeyePersonal.from_dict(doc)


async def get_all_deye_personals() -> List[DeyePersonal]:
    docs = await db_instance[COLLECTION_NAME].find({}).to_list(None)
    return [DeyePersonal.from_dict(doc) for doc in docs]


async def get_deye_personals_by_group(group: str) -> List[DeyePersonal]:
    docs = await db_instance[COLLECTION_NAME].find({"yasno_group": group}).to_list(None)
    return [DeyePersonal.from_dict(doc) for doc in docs]


async def get_deye_personal_by_plug_service(service: str) -> Optional[DeyePersonal]:
    doc = await db_instance[COLLECTION_NAME].find_one({"plug_service": service})
    return DeyePersonal.from_dict(doc)



async def add_user_to_device(device_sn: int, user_id: int) -> bool:
    result = await db_instance[COLLECTION_NAME].update_one(
        {"device_sn": device_sn},
        {"$addToSet": {"user_ids": user_id}}
    )

    return result.modified_count > 0


async def get_deye_personal_by_device_sn(device_sn: int) -> Optional[DeyePersonal]:
    doc = await db_instance[COLLECTION_NAME].find_one({
        "device_sn": device_sn
    })

    return DeyePersonal.from_dict(doc)


async def update_device_alerts(device_sn: int, alerts: list[Alerts]) -> bool:
    result = await db_instance[COLLECTION_NAME].update_one(
        {"device_sn": device_sn},
        {"$set": {"alerts": alerts}}
    )

    return result.modified_count > 0


async def set_access_tokens(device_sn: int, access_token: str, refresh_token: str):
    await db_instance[COLLECTION_NAME].update_one(
        {"device_sn": device_sn},
        {"$set": {"access_token": access_token, "refresh_token": refresh_token}}
    )

async def set_alerts(device_sn: int, alerts: List[Alerts]):
    await db_instance[COLLECTION_NAME].update_one(
        {"device_sn": device_sn},
        {"$set": {"alerts": alerts}}
    )

async def set_yasno_group(device_sn: int, yasno_group: str):
    await db_instance[COLLECTION_NAME].update_one(
        {"device_sn": device_sn},
        {"$set": {"yasno_group": yasno_group}}
    )


async def set_channel_id(device_sn: int, channel_id: int):
    await db_instance[COLLECTION_NAME].update_one(
        {"device_sn": device_sn},
        {"$set": {"channel_id": channel_id}}
    )


