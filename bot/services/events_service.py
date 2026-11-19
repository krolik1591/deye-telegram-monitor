import logging
from typing import TYPE_CHECKING

from db import mongodb
from services.event_bus import EventBus
from services.texts.yasno_texts import get_schedule_text
from types_.mixin_types import (
    NewScheduleEvent,
    PowerAlertEvent,
    SvitloOffEvent,
    SvitloOnEvent,
    UpdateScheduleEvent,
)

if TYPE_CHECKING:
    from services.master_service import MasterService


class EventsService:
    def __init__(self, master_service: 'MasterService', bus: EventBus):
        self.templates = master_service.templates
        self.msg = master_service.msg

        self._subs = [
            bus.subscribe(SvitloOnEvent, self.on_svitlo_on),
            bus.subscribe(SvitloOffEvent, self.on_svitlo_off),
            bus.subscribe(PowerAlertEvent, self.on_power_alert),
            bus.subscribe(NewScheduleEvent, self.on_new_schedule),
            bus.subscribe(UpdateScheduleEvent, self.on_update_schedule),
        ]

    # ------ schedule ------

    async def on_new_schedule(self, event: NewScheduleEvent):
        group = event.schedule.group
        logging.info(f"New schedule event (group={group})")
        text = get_schedule_text(event.schedule)

        for personal in await mongodb.get_deye_personals_by_group(group):
            if personal.channel_id is None:
                continue
            await self.msg.send_new_schedule(personal.channel_id, text)

    async def on_update_schedule(self, event: UpdateScheduleEvent):
        group = event.schedule.group
        logging.info(f"Update schedule event (group={group})")
        text = get_schedule_text(event.schedule)

        for personal in await mongodb.get_deye_personals_by_group(group):
            if personal.channel_id is None:
                continue
            await self.msg.update_schedule(personal.channel_id, text)

    # ------ svitlo ------

    async def on_svitlo_off(self, event: SvitloOffEvent):
        logging.info("Light Off!")
        deye_item = event.item
        prev_event = event.prev_event
        device_sn = deye_item.device_sn

        current_event = await mongodb.create_light_off(deye_item.soc, device_sn)
        deye_personal = await mongodb.get_deye_personal_by_device_sn(device_sn)
        current_yasno = await self._last_yasno_for(deye_personal)

        self.templates.init_text_service(deye_item, current_yasno)
        duration_sec = current_event.timestamp - prev_event.timestamp

        text_hata = self.templates.hata_svitlo_off(duration_sec)
        await self.msg.send_msgs(deye_personal.user_ids, text_hata)

        if deye_personal.channel_id is not None:
            text_channel = self.templates.channel_svitlo_off(duration_sec)
            await self.msg.to_channel(deye_personal.channel_id, text_channel)

    async def on_svitlo_on(self, event: SvitloOnEvent):
        logging.info("Light On!")
        deye_item = event.item
        prev_event = event.prev_event
        device_sn = deye_item.device_sn

        current_event = await mongodb.create_light_on(deye_item.soc, device_sn)
        deye_personal = await mongodb.get_deye_personal_by_device_sn(device_sn)
        current_yasno = await self._last_yasno_for(deye_personal)

        self.templates.init_text_service(deye_item, current_yasno)

        soc_used = deye_item.soc - prev_event.soc
        duration_sec = current_event.timestamp - prev_event.timestamp

        text_hata = self.templates.hata_svitlo_on(duration_sec, soc_used)
        await self.msg.send_msgs(deye_personal.user_ids, text_hata)

        if deye_personal.channel_id is not None:
            text_channel = self.templates.channel_svitlo_on(duration_sec)
            await self.msg.to_channel(deye_personal.channel_id, text_channel)

    # ------ power alert ------

    async def on_power_alert(self, event: PowerAlertEvent):
        deye_item = event.item
        logging.info(f"Power Level Alert! SOC: {deye_item.soc}")

        deye_personal = await mongodb.get_deye_personal_by_device_sn(deye_item.device_sn)
        current_yasno = await self._last_yasno_for(deye_personal)

        self.templates.init_text_service(deye_item, current_yasno)

        text = self.templates.hata_power_alert_template(deye_item.soc, event.emoji)
        await self.msg.send_msgs(deye_personal.user_ids, text)

    # ------ helpers ------

    @staticmethod
    async def _last_yasno_for(personal):
        if personal is None or not personal.yasno_group:
            return None
        return await mongodb.get_last_yasno(personal.yasno_group)
