import asyncio
import logging
import time
from typing import Protocol

from clients.deye_client import DeyeClient, DeyeAuthError
from db import mongodb
from metrics import AllMetric
from services.event_bus import EventBus
from types_.mixin_types import DeyePersonal, DeyeItem, SvitloOnEvent, SvitloOffEvent, PowerAlertEvent, Alerts
from types_.types import DeyeData

REQUEST_INTERVAL = 30
LATEST_ITEMS_THRESHOLD = 60 * 60


class DeyeDeviceRuntime:
    def __init__(
            self,
            personal: DeyePersonal,
            client: DeyeClient,
            event_bus: EventBus,
    ):
        self.personal = personal
        self.client = client
        self.event_bus = event_bus

        self._cached_deye_data: list[DeyeData] | None = None
        self._latest_update: int | None = None

        self.alerts: list[Alerts] = personal.alerts

    async def run(self):
        logging.info(f"Starting runtime for device {self.personal.device_sn}")

        while True:
            try:
                item = await self.get_item()
                logging.info(f"For personal: {self.personal.email}. BatteryPower: {item.battery_power}")
                await self._watch_svitlo(item)
                await self._watch_power(item)

            except Exception as e:
                logging.exception(f"[{self.personal.device_sn}] watcher error: {e}")

            await asyncio.sleep(REQUEST_INTERVAL)

    async def get_item(self) -> DeyeItem:
        now = time.time()

        if (
                self._cached_deye_data
                and self._latest_update
                and now - self._latest_update < REQUEST_INTERVAL
        ):
            return self._build_item()

        await self._fetch_deye_data()
        return self._build_item()

    async def _fetch_deye_data(self):
        now = int(time.time())

        try:
            try:
                data = await self.client.get_device_info()
            except DeyeAuthError:
                data = await self.client.get_device_info()

            data_list = data.get("dataList", [])

            if not data_list:
                raise Exception("No device history")

            self._cached_deye_data = data_list
            self._latest_update = now

        except Exception as e:
            if self._cached_deye_data:
                logging.error(f"[{self.personal.device_sn}] Error fetching data, using cache")
                return self._cached_deye_data

            raise e

    def _build_item(self) -> DeyeItem:
        return DeyeItem(
            device_sn=self.personal.device_sn,
            battery_capacity_kwh=self.personal.battery_capacity_kwh,

            soc=self._get_metric(AllMetric.SOC),
            battery_power=self._get_metric(AllMetric.BatteryPower),
            grid_voltage=self._get_metric(AllMetric.GridVoltageL1L2),
            measured_at=self._get_latest_item_ts(),
            average_battery_power=self._get_average_battery_power(),
            deye_data=self._cached_deye_data,
        )

    def _get_latest_item_ts(self) -> int:
        return int(self._cached_deye_data[-1]["time"])

    def _get_metric(self, metric) -> int:
        last_data = self._cached_deye_data[-1]
        m = next(
            (item for item in last_data["itemList"] if item["key"] == metric),
            None,
        )
        return int(float(m["value"])) if m else 0

    def _get_average_battery_power(self) -> int:
        items = self._get_latest_items(LATEST_ITEMS_THRESHOLD)

        total = 0
        count = 0

        for item in items:
            m = next(
                (i for i in item["itemList"] if i["key"] == AllMetric.BatteryPower),
                None,
            )
            if not m:
                continue

            power = int(m["value"])
            if power > 0:
                total += power
                count += 1

        return int(total / count) if count else 0

    def _get_latest_items(self, ts):
        min_time = time.time() - ts
        return sorted(
            [x for x in self._cached_deye_data if int(x["time"]) > min_time],
            key=lambda x: int(x["time"]),
        )

    async def _watch_svitlo(self, item: DeyeItem):
        device_sn = self.personal.device_sn
        is_charging = item.battery_power < 0

        prev_event = await mongodb.get_last_event(device_sn)
        if not prev_event:
            if is_charging:
                await mongodb.create_light_on(item.soc, device_sn)
            else:
                await mongodb.create_light_off(item.soc, device_sn)

            prev_event = await mongodb.get_last_event(device_sn)



        if not prev_event.svitlo and is_charging:
            await self.event_bus.emit(
                SvitloOnEvent(item=item, prev_event=prev_event)
            )

        if prev_event.svitlo and not is_charging:
            await self.event_bus.emit(
                SvitloOffEvent(item=item, prev_event=prev_event)
            )

    async def _watch_power(self, item: DeyeItem):
        soc = item.soc
        changed = False

        for alert in self.alerts:
            if soc < alert["soc"] and not alert["triggered"]:
                alert["triggered"] = True
                changed = True

                await self.event_bus.emit(
                    PowerAlertEvent(item=item, emoji=alert["emoji"])
                )

            elif soc >= alert["soc"] and alert["triggered"]:
                alert["triggered"] = False
                changed = True

        if changed:
            logging.info("Updating device alerts")
            await mongodb.update_device_alerts(
                device_sn=self.personal.device_sn,
                alerts=self.alerts,
            )


class DeyeClientFactory(Protocol):
    def get_client(self, personal: DeyePersonal) -> DeyeClient:
        ...


class DeyeManager:
    def __init__(
            self,
            *,
            client_factory: DeyeClientFactory,
            event_bus: EventBus,
    ):
        self._client_factory = client_factory
        self._event_bus = event_bus
        self._runtimes: dict[int, DeyeDeviceRuntime] = {}

    async def ensure_device(self, personal: DeyePersonal):
        if personal.device_sn in self._runtimes:
            return

        client = self._client_factory.get_client(personal)

        runtime = DeyeDeviceRuntime(
            personal=personal,
            client=client,
            event_bus=self._event_bus,
        )

        self._runtimes[personal.device_sn] = runtime
        asyncio.create_task(runtime.run())

    async def get_item(self, device_sn: int) -> DeyeItem:
        runtime = self._runtimes.get(device_sn)

        if not runtime:
            raise KeyError(f"Deye runtime not found for device_sn={device_sn}")

        return await runtime.get_item()
