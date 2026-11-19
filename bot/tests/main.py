import asyncio
from pprint import pprint

from db import mongodb
from services.master_service import create_master_service


async def main():
    master_service = create_master_service()
    try:
        personal = await mongodb.get_deye_personal_by_user_id(357108179)
        if personal is None:
            print("No DeyePersonal found for user_id=357108179")
            return

        await master_service.deye_manager.ensure_device(personal)
        item = await master_service.deye_manager.get_item(personal.device_sn)
        pprint(item)
    finally:
        await master_service.deye_client_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
