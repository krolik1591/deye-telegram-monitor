"""
One-shot: register a new DeyePersonal in MongoDB.

Usage:
    1. Fill in the literals in `build_personal()` below.
    2. Run from the `bot/` directory:
           python tests/add_deye_personal.py
    3. The script refuses to insert if a personal with the same device_sn
       already exists — edit that one manually or delete it first.
"""

import asyncio
from pprint import pprint

from db import mongodb
from types_.mixin_types import BasicDeyePersonal, DeyePersonal


# ---------------------------------------------------------------------------
# EDIT THIS to describe the personal you want to add.
# `password` must already be the Deye-API SHA-256 hex (lowercase).
# ---------------------------------------------------------------------------

def build_personal() -> DeyePersonal:
    basic = BasicDeyePersonal(
        user_ids=[357108179],              # Telegram user_id(s) allowed to control this device
        app_id=202511091041006,            # Deye app id
        app_secret="put-app-secret-here",  # Deye app secret
        email="deye-account@example.com",  # Deye account email
        password="put-sha256-hex-here",    # Deye account password (SHA-256 hex)
        device_sn=1234567890,              # Deye device serial number
        battery_capacity_kwh=10,           # kWh (used by the status text / time-to-discharge)
    )
    return DeyePersonal.from_basic(basic)  # alerts=DEFAULT_ALERTS by default


async def main() -> None:
    personal = build_personal()

    existing = await mongodb.get_deye_personal_by_device_sn(personal.device_sn)
    if existing is not None:
        print(f"⚠️  device_sn={personal.device_sn} already exists:")
        pprint(existing)
        print("\nDelete or edit it manually and re-run.")
        return

    created = await mongodb.create_deye_personal(personal)
    print("✅ Inserted DeyePersonal:")
    pprint(created)


if __name__ == "__main__":
    asyncio.run(main())
