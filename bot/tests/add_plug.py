"""
One-shot: register a new TAPO P110 plug in MongoDB.

PREREQS
    - The bot process must be on the SAME LAN as the plug — Tapo P110 uses a
      local control API (no cloud round-trip). Hosting the bot on a VPS
      won't work for plug control.
    - TAPO_USERNAME and TAPO_PASSWORD must be set in bot/.env (Tapo cloud
      account used only for the handshake; everything else is on LAN).
    - Only the TAPO P110 model is supported today. Other Tapo models (P100,
      P105, P115…) use different handlers in the `tapo` library and would
      need PlugClient changes.

USAGE
    1. Edit DEVICE_IP below to the LAN address of your plug.
    2. From the `bot/` dir:  python tests/add_plug.py

    If the plug already exists in Mongo the record is overwritten with
    fresh info pulled from the device (ip / nickname / device_on /
    is_online / last_sync). Fields controlled by the user (watcher_enabled)
    are preserved via the `force_update_plug` upsert semantics.
"""

import asyncio
from pprint import pprint

from clients.plug_client import PlugClient
from db import mongodb


DEVICE_IP = "192.168.68.130"


async def main() -> None:
    client = PlugClient()

    print(f"Probing TAPO P110 at {DEVICE_IP}…")
    try:
        plug = await client.get_device_info(DEVICE_IP)
    except Exception as e:
        print(f"\n❌ Can't reach TAPO device at {DEVICE_IP}: {e!r}\n")
        print("Checklist:")
        print("  - Is the bot on the SAME LAN as the plug?")
        print("  - Is DEVICE_IP correct? (ping it first)")
        print("  - Are TAPO_USERNAME / TAPO_PASSWORD set in bot/.env?")
        print("  - Is the device a TAPO P110? (other models need code changes)")
        return

    existing = await mongodb.get_plug_by_ip(DEVICE_IP)
    action = "overwrote existing record" if existing else "inserted new record"

    await mongodb.force_update_plug(plug)
    print(f"\n✅ {action} for {plug.nickname!r} ({DEVICE_IP}):")
    pprint(plug)

    if existing:
        print("\n(Prior state — for reference:)")
        pprint(existing)


if __name__ == "__main__":
    asyncio.run(main())
