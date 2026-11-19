from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi

from settings.dotenv_config import dotenv_config

client = AsyncIOMotorClient(dotenv_config.mongo_connection_string, server_api=ServerApi('1'))
db_instance = client["Electric"]

async def create_db_indexes():
    await db_instance["deye_personal"].create_index("device_sn", unique=True)
    # TTL: invites auto-delete 24h after creation
    await db_instance["invites"].create_index("created_at", expireAfterSeconds=24 * 3600)
