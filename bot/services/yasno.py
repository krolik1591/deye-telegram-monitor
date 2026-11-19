import logging
from asyncio import sleep
from datetime import datetime

from clients.yasno_client import YasnoClient
from db import mongodb
from services.event_bus import EventBus
from services.msg_service import create_message_service
from types_ import types as t
from types_.mixin_types import NewScheduleEvent, ScheduleYasno, UpdateScheduleEvent


class Yasno:
    POLL_INTERVAL = 120

    def __init__(self, event_bus: EventBus):
        self.yasno = YasnoClient()
        self.event_bus = event_bus
        self.msg = create_message_service()

    async def start(self):
        logging.info("Starting yasno watcher...")
        while True:
            try:
                groups = await self._collect_groups()
                for group in groups:
                    try:
                        await self._tick_group(group)
                    except Exception as e:
                        text = f"Yasno watcher error (group {group}): {e}"
                        logging.error(text)
                        await self.msg.to_devs(text)
            except Exception as e:
                text = f"Yasno watcher error: {e}"
                logging.error(text)
                await self.msg.to_devs(text)

            await sleep(self.POLL_INTERVAL)

    async def _collect_groups(self) -> list[str]:
        personals = await mongodb.get_all_deye_personals()
        return sorted({p.yasno_group for p in personals if p.yasno_group})

    async def prime_group(self, group: str) -> None:
        """Force-fetch a group now (used right after a user sets yasno_group,
        so they don't have to wait until the next 120 s poll for the DB doc
        to exist)."""
        try:
            await self._tick_group(group)
        except Exception as e:
            logging.warning(f"Yasno prime_group({group}) failed: {e}")

    async def _tick_group(self, group: str) -> None:
        raw_yasno = await self.yasno.get_group(group)
        yasno_date = datetime.fromisoformat(raw_yasno["today"]["date"])
        formatted_date = yasno_date.strftime("%Y-%m-%d")

        db_yasno = await mongodb.get_yasno_by_date(formatted_date, group)

        if not db_yasno:
            return await self._new_schedule(raw_yasno, formatted_date, group)

        return await self._update_schedule(db_yasno, raw_yasno, formatted_date, group)

    async def _new_schedule(self, raw_yasno: t.ScheduleRaw, formatted_date: str, group: str):
        yasno = await mongodb.push_yasno_update(formatted_date, group, raw_yasno)
        await self.event_bus.emit(NewScheduleEvent(schedule=yasno))

    async def _update_schedule(
        self,
        db_yasno: ScheduleYasno,
        raw_yasno: t.ScheduleRaw,
        formatted_date: str,
        group: str,
    ):
        if not self._is_equal(db_yasno.updates[-1], raw_yasno):
            db_yasno = await mongodb.push_yasno_update(formatted_date, group, raw_yasno)

        await self.event_bus.emit(UpdateScheduleEvent(schedule=db_yasno))

    @staticmethod
    def _is_equal(db_yasno: t.ScheduleRaw, raw: t.ScheduleRaw) -> bool:
        is_today_equal = raw["today"] == db_yasno["today"]
        is_tomorrow_equal = raw["tomorrow"] == db_yasno["tomorrow"]
        return is_today_equal and is_tomorrow_equal
