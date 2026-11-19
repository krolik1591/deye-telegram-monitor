"""
Quick probe: fetch any Deye metric(s) for a given user and print the latest
value(s). Edit USER_ID and METRICS and run this file.
"""

import asyncio
from datetime import datetime

import aiohttp

from clients.deye_client import DeyeClient
from db import mongodb
from metrics import AllMetric
from utils._time import tz_now


USER_ID = 357108179

# Put any AllMetric.X here. Add/remove freely.
METRICS = [
    AllMetric.SOC,
    AllMetric.BatteryPower,
    AllMetric.GridVoltageL1L2,
    # AllMetric.GridFrequency,
    # AllMetric.GridCurrentL1L2,
    # AllMetric.ACVoltageRUA,
    # AllMetric.LoadVoltageL1L2,
    # AllMetric.BatteryVoltage
]


class ProbeDeyeClient(DeyeClient):
    """DeyeClient that lets the caller choose measurePoints per request."""

    def __init__(self, personal, session, metrics):
        super().__init__(personal, session)
        self._metrics = metrics

    def _build_history_payload(self):
        today = tz_now().strftime("%Y-%m-%d")
        return {
            "deviceSn": self.deye_personal.device_sn,
            "startAt": today,
            "endAt": today,
            "granularity": 1,
            "measurePoints": self._metrics,
        }


def _extract_latest(data, metric):
    data_list = data.get("dataList") or []
    if not data_list:
        return None, None, None

    last = data_list[-1]
    item = next((i for i in last["itemList"] if i["key"] == metric), None)
    if not item:
        return None, None, int(last["time"])

    return item.get("value"), item.get("unit"), int(last["time"])


async def main():
    personal = await mongodb.get_deye_personal_by_user_id(USER_ID)
    if personal is None:
        print(f"No DeyePersonal for user_id={USER_ID}")
        return

    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        client = ProbeDeyeClient(personal, session, METRICS)

        try:
            data = await client.get_device_info()
        except Exception as e:
            # typically DeyeAuthError on first run — retry once with fresh token
            print(f"First call failed ({type(e).__name__}: {e}); retrying…")
            data = await client.get_device_info()

    print(f"device_sn={personal.device_sn}  email={personal.email}")
    for metric in METRICS:
        value, unit, ts = _extract_latest(data, metric)
        when = datetime.fromtimestamp(ts).strftime("%H:%M:%S") if ts else "—"
        print(f"  [{when}] {metric:<30} = {value} {unit or ''}".rstrip())


if __name__ == "__main__":
    asyncio.run(main())
