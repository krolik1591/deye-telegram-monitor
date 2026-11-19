"""
Manual event trigger: emit SvitloOn/Off, PowerAlert, New/UpdateSchedule from
code so you can test the whole EventsService pipeline (Telegram DM + channel
posts + pinned-message edit) without waiting for Deye/Yasno polls.

HOW
    1. Make sure the bot is NOT running in another process — otherwise two
       aiohttp sessions / two message-sends will race on the same Telegram
       account.
    2. Edit USER_ID below.
    3. In main(), comment/uncomment the event you want to fire.
    4. From the `bot/` dir:  python tests/emit_events.py

WARNING
    - SvitloOn/Off handlers insert a real row into `svitlo_stats` for the
      device_sn. That row will influence the next Deye poll's transition
      detection. Delete it from Mongo if you don't want that side effect.
    - PowerAlert does NOT write to DB.
    - New/UpdateSchedule do NOT write to the yasno collection (they only
      post/edit the pinned message in `personal.channel_id`).
"""

import asyncio
import time

from db import mongodb
from services.master_service import create_master_service
from types_.mixin_types import (
    DeyeItem,
    NewScheduleEvent,
    PowerAlertEvent,
    SvitloItem,
    SvitloOffEvent,
    SvitloOnEvent,
    UpdateScheduleEvent,
)
from utils._time import tz_now


USER_ID = 357108179


async def main() -> None:
    master = create_master_service()
    try:
        personal = await mongodb.get_deye_personal_by_user_id(USER_ID)
        if personal is None:
            print(f"No DeyePersonal for user_id={USER_ID}")
            return

        # ---- pick one (or several) to fire ----
        await emit_svitlo_off(master, personal)
        # await emit_svitlo_on(master, personal)
        # await emit_power_alert(master, personal, soc=20, emoji="‼️")
        # await emit_new_schedule(master, personal)
        # await emit_update_schedule(master, personal)

    finally:
        await master.deye_client_manager.close()


# ---------------------------------------------------------------------------
# emitters
# ---------------------------------------------------------------------------

async def emit_svitlo_off(master, personal) -> None:
    item = _fake_deye_item(personal, soc=68, battery_power=1800, grid_voltage=0.0)
    prev = _fake_prev_svitlo(personal, svitlo=True, soc=80, minutes_ago=90)
    await master.event_bus.emit(SvitloOffEvent(item=item, prev_event=prev))


async def emit_svitlo_on(master, personal) -> None:
    item = _fake_deye_item(personal, soc=55, battery_power=-2000, grid_voltage=230.0)
    prev = _fake_prev_svitlo(personal, svitlo=False, soc=78, minutes_ago=180)
    await master.event_bus.emit(SvitloOnEvent(item=item, prev_event=prev))


async def emit_power_alert(master, personal, *, soc: int = 20, emoji: str = "‼️") -> None:
    item = _fake_deye_item(personal, soc=soc, battery_power=1500, grid_voltage=0.0)
    await master.event_bus.emit(PowerAlertEvent(item=item, emoji=emoji))


async def emit_new_schedule(master, personal) -> None:
    if not personal.yasno_group:
        print("Personal has no yasno_group — nothing to post.")
        return
    yasno = await mongodb.get_last_yasno(personal.yasno_group)
    if yasno is None:
        print(f"No yasno doc for group {personal.yasno_group}")
        return
    await master.event_bus.emit(NewScheduleEvent(schedule=yasno))


async def emit_update_schedule(master, personal) -> None:
    if not personal.yasno_group:
        print("Personal has no yasno_group — nothing to edit.")
        return
    yasno = await mongodb.get_last_yasno(personal.yasno_group)
    if yasno is None:
        print(f"No yasno doc for group {personal.yasno_group}")
        return
    await master.event_bus.emit(UpdateScheduleEvent(schedule=yasno))


# ---------------------------------------------------------------------------
# fakers
# ---------------------------------------------------------------------------

def _fake_deye_item(personal, *, soc: int, battery_power: int, grid_voltage: float) -> DeyeItem:
    return DeyeItem(
        device_sn=personal.device_sn,
        battery_capacity_kwh=personal.battery_capacity_kwh,
        soc=soc,
        battery_power=battery_power,
        grid_voltage=grid_voltage,
        measured_at=int(time.time()),
        average_battery_power=battery_power,
        deye_data=[],
    )


def _fake_prev_svitlo(personal, *, svitlo: bool, soc: int, minutes_ago: int) -> SvitloItem:
    return SvitloItem(
        device_sn=personal.device_sn,
        svitlo=svitlo,
        soc=soc,
        timestamp=int(tz_now().timestamp()) - minutes_ago * 60,
        date_str=tz_now().strftime("%Y-%m-%d"),
    )


if __name__ == "__main__":
    asyncio.run(main())
