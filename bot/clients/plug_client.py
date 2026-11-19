import logging
import asyncio

from tapo import ApiClient, PlugEnergyMonitoringHandler

from settings.dotenv_config import dotenv_config
from types_.mixin_types import Plug


class PlugClient:
    def __init__(self):
        self.client = ApiClient(dotenv_config.tapo_username, dotenv_config.tapo_password)
        self._devices: dict[str, PlugEnergyMonitoringHandler] = {}

    async def get_device(self, ip: str) -> PlugEnergyMonitoringHandler:
        if ip in self._devices:
            return self._devices[ip]

        logging.info(f"[TAPO] Creating new device session for {ip}")
        try:
            device = await asyncio.wait_for(
                self.client.p110(ip),
                timeout=3
            )
            self._devices[ip] = device
            return device

        except asyncio.TimeoutError:
            logging.error(f"[TAPO] Timeout creating device session for {ip}")
            raise
        except Exception:
            raise

    async def get_device_info(self, ip: str) -> Plug:
        try:
            device = await self.get_device(ip)
            device_info = await device.get_device_info()
            return Plug(
                ip=device_info.ip,
                nickname=device_info.nickname,
                device_on=device_info.device_on,
                is_online=True,
            )
        except Exception as e:
            self.drop_device(ip)
            raise e

    async def device_on(self, ip: str):
        device = await self.get_device(ip)
        try:
            await device.on()
        except Exception as e:
            self.drop_device(ip)
            raise e

    async def device_off(self, ip: str):
        device = await self.get_device(ip)
        try:
            await device.off()
        except Exception as e:
            self.drop_device(ip)
            raise e

    def drop_device(self, ip: str):
        self._devices.pop(ip, None)

    def clear(self):
        self._devices.clear()
