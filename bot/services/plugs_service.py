import asyncio
import logging
import time
from typing import List

from clients.plug_client import PlugClient
from db import mongodb
from services.msg_service import create_message_service
from types_.mixin_types import Plug

# Only backend supported today. When more land, split plugs_service.py by backend.
TAPO_LOCAL = "tapo_local"


class DeviceStateWarning(Exception):
    """Warning for non-critical device state issues"""
    pass


class PlugsService:
    STATE_TTL = 180

    def __init__(self):
        self.plug_client = PlugClient()
        self.msg = create_message_service()

        self._last_state_refresh: float = 0

    async def register_device(self, device_ip):
        plug = await self.plug_client.get_device_info(device_ip)
        await mongodb.force_update_plug(plug)

    async def get_and_update_plugs(self) -> List[Plug]:
        cached_plugs_info = await mongodb.get_plugs()
        current_plugs_info = []
        for plug in cached_plugs_info:
            try:
                plug = await self.plug_client.get_device_info(plug.ip)
            except Exception as e:
                logging.error(f"Cant fetch device {plug.nickname}: {e}")
                plug.is_online = False

            await mongodb.sync_plug_device_info(plug)
            current_plugs_info.append(plug)

        return current_plugs_info

    async def enable_plug(self, device_ip: str):
        plug = await mongodb.get_plug_by_ip(device_ip)
        logging.info(f"Enabling device {plug}")
        if plug.device_on:
            raise DeviceStateWarning("Device already on")

        try:
            await self.plug_client.device_on(device_ip)
        except Exception as e:
            text = f"Cant enable device {plug.nickname}: {e}"
            await self.msg.to_devs(text)
            raise Exception(text)

        await mongodb.update_device_on_state(plug.ip, True)
        await self.msg.to_devs(f"Device {plug.nickname} enabled")

    async def disable_plug(self, device_ip: str):
        plug = await mongodb.get_plug_by_ip(device_ip)
        logging.info(f"Disabling device {plug}")
        if not plug.device_on:
            raise DeviceStateWarning("Device already off")

        try:
            await self.plug_client.device_off(device_ip)
        except Exception as e:
            text = f"Cant disable device {plug.nickname}: {e}"
            await self.msg.to_devs(text)
            raise Exception(text)

        await mongodb.update_device_on_state(plug.ip, False)
        await self.msg.to_devs(f"Device {plug.nickname} disabled")


    async def start(self):
        logging.info("Plugs watcher starting")
        while True:
            try:
                await self._start()
            except Exception as e:
                logging.error(f"Plugs watcher error: {e}")

            await asyncio.sleep(30)

    async def _start(self):
        owner = await mongodb.get_deye_personal_by_plug_service(TAPO_LOCAL)
        if owner is None:
            logging.info("Plugs watcher: no personal with plug_service=tapo_local, skipping tick")
            return

        svitlo_stat = await mongodb.get_last_event(owner.device_sn)

        plugs = await mongodb.get_watcher_enabled_plugs()
        plugs = await self._refresh_all_plugs_state_if_needed(plugs)

        for plug in plugs:
            if not plug.is_online:
                try:
                    plug = await self.plug_client.get_device_info(plug.ip)
                except Exception as e:
                    logging.error(f"Plug watcher: Cant fetch device {plug.nickname}: {e}")
                    continue

            try:
                if svitlo_stat.svitlo:
                    await self.enable_plug(plug.ip)
                else:
                    await self.disable_plug(plug.ip)

            except DeviceStateWarning as e:
                logging.info(e)
            except Exception as e:
                logging.error(f"Plug watcher error: {e}")

    async def _refresh_all_plugs_state_if_needed(self, plugs: list[Plug]) -> list[Plug]:
        now = time.time()

        if now - self._last_state_refresh < self.STATE_TTL:
            return plugs

        logging.info("Force refreshing plugs state...")
        updated_plugs: list[Plug] = []
        for plug in plugs:
            try:
                real_plug = await self.plug_client.get_device_info(plug.ip)

                if real_plug.device_on != plug.device_on:
                    logging.info(
                        f"State mismatch {plug.nickname}: "
                        f"db={plug.device_on} real={real_plug.device_on}"
                    )
                    await mongodb.sync_plug_device_info(real_plug)
                    plug.device_on = real_plug.device_on

                updated_plugs.append(plug)

            except Exception as e:
                logging.error(
                    f"State refresh failed {plug.nickname}: {e}"
                )
                plug.is_online = False
                updated_plugs.append(plug)
                await mongodb.update_is_online_state(plug.ip, False)

        self._last_state_refresh = now
        return updated_plugs
