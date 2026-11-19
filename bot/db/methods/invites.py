import secrets
from datetime import datetime
from typing import Optional

from db.mongodb import db_instance

COLLECTION_NAME = "invites"

INVITE_TTL_SECONDS = 24 * 3600  # 24h


async def create_invite(device_sn: int) -> str:
    """Create a one-shot invite token tied to a device_sn. Returns the token."""
    token = secrets.token_urlsafe(10)
    await db_instance[COLLECTION_NAME].insert_one({
        "_id": token,
        "device_sn": device_sn,
        "created_at": datetime.utcnow(),
    })
    return token


async def consume_invite(token: str) -> Optional[int]:
    """Atomically delete the invite and return its device_sn, or None if missing."""
    doc = await db_instance[COLLECTION_NAME].find_one_and_delete({"_id": token})
    return doc.get("device_sn") if doc else None
