import logging

from clients.deye_client import DeyeClientManager
from db import mongodb
from services.device_runtime import DeyeManager
from services.event_bus import EventBus
from services.events_service import EventsService
from services.msg_service import create_message_service
from services.plugs_service import PlugsService
from services.texts.templates_service import TemplatesService
from services.yasno import Yasno


class MasterService:
    def __init__(self):
        self.msg = create_message_service()

        self.event_bus = EventBus()

        self.new_yasno = Yasno(self.event_bus)

        self.deye_client_manager = DeyeClientManager()

        self.deye_manager = DeyeManager(
            client_factory=self.deye_client_manager,
            event_bus=self.event_bus,
        )

        self.templates = TemplatesService(self)

        self.events = EventsService(self, self.event_bus)
        self.plugs = PlugsService()

    async def run(self):
        deye_personals = await mongodb.get_all_deye_personals()
        for personal in deye_personals:
            logging.info(f"Ensure device with personal: {personal.email}")
            await self.deye_manager.ensure_device(personal)


def create_master_service():
    return MasterService()
